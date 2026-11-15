"""Atualizações em segundo plano (APScheduler) com status consultável pela API.

Cada tarefa tem uma trava própria: execução agendada e manual nunca rodam ao mesmo tempo.
"""

import logging
import re
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..config import settings
from ..db import SessionLocal
from ..models import Operacao
from . import backup, cotahist, cripto, fundamentos, historico
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
    # Falhas de fonte do resultado (job concluído, mas com dados faltando por erro do provedor).
    falhas_de: Callable[[Any], list[str]] = field(default=lambda _r: [], repr=False)
    trava: threading.Lock = field(default_factory=threading.Lock, repr=False)
    em_execucao: bool = False
    inicio: datetime | None = None
    fim: datetime | None = None
    sucesso: bool | None = None
    mensagem: str | None = None
    duracao_s: float | None = None
    # "ok" | "parcial" (concluída com falhas de fonte) | "falha" (exceção); None = ainda não executada.
    status: str | None = None


_URL = re.compile(r"https?://\S+", re.IGNORECASE)
_PASTA_USUARIO = re.compile(r"(?i)\b([a-z]:[\\/]+users[\\/]+)[^\\/\s'\"]+")
_DETALHE_SQL = re.compile(r"\s*\[(?:SQL|parameters):.*", re.DOTALL)


def mensagem_segura(texto: str) -> str:
    """Remove URLs, SQL/parâmetros e pastas de usuário do texto exibido na UI (o detalhe fica no log)."""
    texto = _DETALHE_SQL.sub("", texto)
    texto = _URL.sub("<fonte externa>", texto)
    return _PASTA_USUARIO.sub(r"\1***", texto).strip()


def mensagem_de_erro(erro: BaseException) -> str:
    if isinstance(erro, SQLAlchemyError):
        return "Falha ao acessar o banco de dados; detalhes no log"
    if isinstance(erro, (httpx.HTTPError, requests.RequestException, ConnectionError, TimeoutError)):
        return "Falha de comunicação com a fonte externa; detalhes no log"
    return mensagem_segura(f"{type(erro).__name__}: {erro}")


def _falhas_cotacoes(r) -> list[str]:
    return list(dict.fromkeys(r.falhas_fonte))


def _resumo_cotacoes(r) -> str:
    texto = f"{len(r.atualizados)} atualizados"
    texto += f"; sem cotação: {', '.join(r.sem_cotacao)}" if r.sem_cotacao else ""
    return texto + (f"; falha na fonte: {', '.join(_falhas_cotacoes(r))}" if r.falhas_fonte else "")


def _resumo_cotahist(r: cotahist.ResultadoCarga) -> str:
    if not r.arquivos and not r.indisponiveis:
        return "Nada a carregar"
    texto = f"{r.cotacoes} cotações de {len(r.arquivos)} arquivo(s)"
    return texto + (f"; ainda não publicados: {', '.join(r.indisponiveis)}" if r.indisponiveis else "")


def _resumo_fundamentos(r: fundamentos.ResultadoFundamentos) -> str:
    return r.resumo()


def usa_sqlite() -> bool:
    return settings.database_url is None


def _backup_automatico(_sessao: Session) -> Path | None:
    return backup.gerar_automatico(settings.db_path) if usa_sqlite() else None


def _resumo_backup(r: Path | None) -> str:
    return f"Salvo {r.name}" if r else "Banco em servidor: use o backup do próprio serviço"


TAREFAS: dict[str, Tarefa] = {
    t.nome: t
    for t in (
        Tarefa(
            "cotacoes", "Cotações (Yahoo) e câmbio (PTAX/BCB)", atualizar_cotacoes, _resumo_cotacoes, _falhas_cotacoes,
        ),
        Tarefa("cotahist_diario", "Fechamento oficial B3 (COTAHIST diário)", cotahist.carregar_pendentes, _resumo_cotahist),
        Tarefa("cotahist_historico", "Histórico B3 (COTAHIST anual)", cotahist.carregar_historico, _resumo_cotahist),
        Tarefa(
            "indices_diario", "Índices (CDI, IPCA, SELIC, IGP-M, IBOV, IFIX), PTAX, exterior e criptos — recentes",
            historico.atualizar_recentes, lambda r: r.resumo(), lambda r: r.falhas,
        ),
        Tarefa(
            "historico_complementar", "Histórico de índices, PTAX, ativos do exterior e criptos (completo)",
            historico.carregar_tudo, lambda r: r.resumo(), lambda r: r.falhas,
        ),
        Tarefa(
            "fundamentos", "Fundamentos B3 (Fundamentus) e ativos dos EUA (Yahoo Finance)",
            fundamentos.atualizar, _resumo_fundamentos, lambda r: r.falhas,
        ),
        Tarefa(
            "cripto", "Cripto (CoinGecko → Kraken) e câmbio PTAX", cripto.atualizar, lambda r: r.resumo(),
            lambda r: r.falhas,
        ),
        Tarefa("backup", "Backup automático do banco (mantém os 10 últimos)", _backup_automatico, _resumo_backup),
    )
}


@contextmanager
def exclusivo() -> Iterator[None]:
    """Trava todas as tarefas (para restaurar o banco); falha se alguma estiver em execução."""
    obtidas: list[Tarefa] = []
    try:
        for tarefa in TAREFAS.values():
            if not tarefa.trava.acquire(blocking=False):
                raise TarefaOcupada(f"Aguarde '{tarefa.descricao}' terminar")
            obtidas.append(tarefa)
        yield
    finally:
        for tarefa in obtidas:
            tarefa.trava.release()


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
        falhas = tarefa.falhas_de(resultado)
        tarefa.sucesso, tarefa.mensagem = True, mensagem_segura(tarefa.resumir(resultado))
        tarefa.status = "parcial" if falhas else "ok"
        if falhas:
            log.warning("Tarefa %s concluída com falhas de fonte: %s", nome, "; ".join(falhas))
        else:
            log.info("Tarefa %s concluída: %s", nome, tarefa.mensagem)
        return resultado
    except Exception as erro:
        tarefa.sucesso, tarefa.status, tarefa.mensagem = False, "falha", mensagem_de_erro(erro)
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
    _agendador.add_job(_executar_agendado, CronTrigger(hour=12, minute=30), args=["backup"], id="backup")
    _agendador.start()
    with SessionLocal() as sessao:
        if cotahist.ultima_data_b3(sessao):
            # Recupera dias perdidos enquanto o app estava fechado.
            disparar("cotahist_diario")
        elif sessao.scalar(select(Operacao.id).limit(1)) is not None:
            # Sem histórico de preços a rentabilidade usa o custo como valor de mercado nos meses passados.
            disparar_carga_historica()
    if usa_sqlite() and settings.db_path.is_file():
        backup.limpar_parciais(settings.db_path)
        if not backup.automatico_recente(settings.db_path):
            disparar("backup")
    log.info("Agendador iniciado")


def parar() -> None:
    global _agendador
    em_curso = [t.nome for t in TAREFAS.values() if t.em_execucao]
    if em_curso:
        # Cada lote já gravado foi commitado; o restante é refeito na próxima execução.
        log.warning("Encerrando com tarefas em execução (serão interrompidas): %s", ", ".join(em_curso))
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


CARGA_HISTORICA = ("cotahist_historico", "historico_complementar")
# Impede duas sequências simultâneas (ex.: duplo clique antes de a 1ª tarefa marcar `em_execucao`).
_trava_carga_historica = threading.Lock()


def disparar_carga_historica() -> None:
    """Histórico B3 e complementar (PTAX, exterior, índices) em sequência, numa thread própria.

    Em sequência para não concorrerem pela gravação de `cotacao` no SQLite.
    """
    for nome in CARGA_HISTORICA:
        if TAREFAS[nome].em_execucao:
            raise TarefaOcupada(f"'{TAREFAS[nome].descricao}' já está em execução")
    if not _trava_carga_historica.acquire(blocking=False):
        raise TarefaOcupada("A carga histórica já está em execução")

    def rodar() -> None:
        try:
            for nome in CARGA_HISTORICA:
                _executar_agendado(nome)
        finally:
            _trava_carga_historica.release()

    try:
        threading.Thread(target=rodar, daemon=True, name="tarefa-carga-historica").start()
    except BaseException:
        _trava_carga_historica.release()
        raise


def proxima_execucao(nome: str) -> datetime | None:
    job = _agendador.get_job(nome) if _agendador else None
    return job.next_run_time if job else None
