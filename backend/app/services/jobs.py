"""Atualizações em segundo plano (APScheduler) com status consultável pela API.

Cada tarefa tem uma trava própria: execução agendada e manual nunca rodam ao mesmo tempo.
"""

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from ..config import settings
from ..db import SessionLocal
from . import cotahist, cripto, fundamentos, historico
from .cotacoes import atualizar_cotacoes

log = logging.getLogger(__name__)

FUSO = ZoneInfo("America/Sao_Paulo")


class TarefaOcupada(Exception):
    pass


@dataclass
class Tarefa:
    nome: str
    descricao: str
    funcao: Callable[[Session], Any]
    resumir: Callable[[Any], str]
    trava: threading.Lock = field(default_factory=threading.Lock, repr=False)
    em_execucao: bool = False
    inicio: datetime | None = None
    fim: datetime | None = None
    sucesso: bool | None = None
    mensagem: str | None = None
    duracao_s: float | None = None


def _resumo_cotacoes(r) -> str:
    texto = f"{len(r.atualizados)} atualizados"
    return texto + (f"; sem cotação: {', '.join(r.sem_cotacao)}" if r.sem_cotacao else "")


def _resumo_cotahist(r: cotahist.ResultadoCarga) -> str:
    if not r.arquivos and not r.indisponiveis:
        return "Nada a carregar"
    texto = f"{r.cotacoes} cotações de {len(r.arquivos)} arquivo(s)"
    return texto + (f"; ainda não publicados: {', '.join(r.indisponiveis)}" if r.indisponiveis else "")


def _resumo_fundamentos(r: fundamentos.ResultadoFundamentos) -> str:
    return r.resumo()


TAREFAS: dict[str, Tarefa] = {
    t.nome: t
    for t in (
        Tarefa("cotacoes", "Cotações (Yahoo) e câmbio (PTAX/BCB)", atualizar_cotacoes, _resumo_cotacoes),
        Tarefa("cotahist_diario", "Fechamento oficial B3 (COTAHIST diário)", cotahist.carregar_pendentes, _resumo_cotahist),
        Tarefa("cotahist_historico", "Histórico B3 (COTAHIST anual)", cotahist.carregar_historico, _resumo_cotahist),
        Tarefa(
            "indices_diario", "Índices (CDI, IPCA, SELIC, IGP-M, IBOV, IFIX), PTAX e exterior — recentes",
            historico.atualizar_recentes, lambda r: r.resumo(),
        ),
        Tarefa(
            "historico_complementar", "Histórico de índices, PTAX e ativos do exterior (completo)",
            historico.carregar_tudo, lambda r: r.resumo(),
        ),
        Tarefa("fundamentos", "Fundamentos de ações e FIIs (Fundamentus)", fundamentos.atualizar, _resumo_fundamentos),
        Tarefa("cripto", "Cripto (CoinGecko → Kraken) e câmbio PTAX", cripto.atualizar, lambda r: r.resumo()),
    )
}


def executar(nome: str) -> Any:
    """Roda a tarefa agora, na thread atual. Levanta TarefaOcupada se já estiver em execução."""
    tarefa = TAREFAS[nome]
    if not tarefa.trava.acquire(blocking=False):
        raise TarefaOcupada(f"'{tarefa.descricao}' já está em execução")
    tarefa.em_execucao, tarefa.inicio = True, datetime.now(FUSO)
    inicio = time.perf_counter()
    log.info("Tarefa %s iniciada", nome)
    try:
        with SessionLocal() as sessao:
            resultado = tarefa.funcao(sessao)
        tarefa.sucesso, tarefa.mensagem = True, tarefa.resumir(resultado)
        log.info("Tarefa %s concluída: %s", nome, tarefa.mensagem)
        return resultado
    except Exception as erro:
        tarefa.sucesso, tarefa.mensagem = False, f"{type(erro).__name__}: {erro}"
        log.exception("Tarefa %s falhou", nome)
        raise
    finally:
        tarefa.em_execucao, tarefa.fim = False, datetime.now(FUSO)
        tarefa.duracao_s = round(time.perf_counter() - inicio, 1)
        tarefa.trava.release()


def _executar_agendado(nome: str) -> None:
    try:
        executar(nome)
    except TarefaOcupada:
        log.info("Tarefa %s ignorada: já em execução", nome)
    except Exception:
        pass  # já registrado em executar()


_agendador: BackgroundScheduler | None = None


def iniciar() -> None:
    global _agendador
    if _agendador is not None:
        return
    _agendador = BackgroundScheduler(timezone=FUSO, job_defaults={"coalesce": True, "max_instances": 1})
    _agendador.add_job(
        _executar_agendado, CronTrigger(day_of_week="mon-fri", hour="10-18", minute=f"*/{settings.cotacoes_intervalo_min}"),
        args=["cotacoes"], id="cotacoes",
    )
    # Noite do pregão e manhã seguinte (caso o arquivo atrase ou o computador esteja desligado).
    _agendador.add_job(
        _executar_agendado, CronTrigger(hour=f"8,{settings.cotahist_hora}", minute=5),
        args=["cotahist_diario"], id="cotahist_diario",
    )
    _agendador.add_job(
        _executar_agendado, CronTrigger(hour="9,20", minute=15), args=["indices_diario"], id="indices_diario",
    )
    _agendador.add_job(
        _executar_agendado, CronTrigger(day_of_week="mon", hour=8, minute=0),
        args=["fundamentos"], id="fundamentos",
    )
    _agendador.add_job(
        _executar_agendado, CronTrigger(minute=f"*/{settings.cotacoes_intervalo_min}"),
        args=["cripto"], id="cripto",
    )
    _agendador.start()
    # Recupera dias perdidos enquanto o app estava fechado (só se o histórico já foi carregado).
    with SessionLocal() as sessao:
        if cotahist.ultima_data_b3(sessao):
            disparar("cotahist_diario")
    log.info("Agendador iniciado")


def parar() -> None:
    global _agendador
    if _agendador is not None:
        _agendador.shutdown(wait=False)
        _agendador = None


def disparar(nome: str) -> None:
    """Agenda a tarefa para rodar já em segundo plano (para tarefas longas)."""
    tarefa = TAREFAS[nome]
    if tarefa.em_execucao:
        raise TarefaOcupada(f"'{tarefa.descricao}' já está em execução")
    if _agendador is None:
        threading.Thread(target=_executar_agendado, args=[nome], daemon=True, name=f"tarefa-{nome}").start()
        return
    _agendador.add_job(_executar_agendado, args=[nome], id=f"{nome}-manual", replace_existing=True)


def proxima_execucao(nome: str) -> datetime | None:
    job = _agendador.get_job(nome) if _agendador else None
    return job.next_run_time if job else None
