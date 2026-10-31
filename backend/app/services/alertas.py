"""Alertas calculados na hora a partir dos dados locais (nada é enviado para fora)."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Ativo, AtivoRadar, Investidor, Operacao
from . import agenda_proventos, alocacao, ir, parametros, qualidade, renda_fixa_liquida
from .carteira import ultimas_cotacoes

log = logging.getLogger(__name__)


@dataclass
class Alerta:
    codigo: str
    severidade: str  # alta | media | info
    titulo: str
    detalhe: str
    link: str | None = None


def _moeda(valor) -> str:
    return f"R$ {float(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _num(valor) -> str:
    return f"{float(valor):.2f}".replace(".", ",")


def _preco_alvo(sessao: Session) -> list[Alerta]:
    alvos = {
        a.ativo_id: (a.preco_alvo, ativo)
        for a, ativo in sessao.execute(
            select(AtivoRadar, Ativo).join(Ativo, Ativo.id == AtivoRadar.ativo_id).where(AtivoRadar.preco_alvo.is_not(None))
        )
    }
    cotacoes = ultimas_cotacoes(sessao, set(alvos))
    return [
        Alerta(
            f"preco_alvo:{ativo.ticker}", "media", f"{ativo.ticker} atingiu o preço-alvo",
            f"Cotação {_num(cotacoes[i].preco)} ≤ alvo {_num(alvo)} ({ativo.moeda}) em {cotacoes[i].data:%d/%m/%Y}.",
            "/radar",
        )
        for i, (alvo, ativo) in alvos.items()
        if i in cotacoes and cotacoes[i].preco <= alvo
    ]


def _pct(fracao) -> str:
    return f"{float(fracao) * 100:.1f}%".replace(".", ",")


def _alocacao(sessao: Session, investidor_ids: Sequence[int] | None, desvio_pp: int) -> list[Alerta]:
    r = alocacao.calcular(sessao, investidor_ids)
    limite = desvio_pp / 100
    fora = sorted(
        (b for b in r.books if b.peso_alvo > 0 and abs(b.peso_atual - b.peso_alvo) >= limite),
        key=lambda b: -abs(b.peso_atual - b.peso_alvo),
    )
    if not fora:
        return []
    titulo = f"Book {fora[0].nome} fora do alvo" if len(fora) == 1 else f"{len(fora)} books fora do alvo"
    detalhe = "; ".join(f"{b.nome}: {_pct(b.peso_atual)} × alvo {_pct(b.peso_alvo)}" for b in fora)
    return [Alerta("alocacao", "media", titulo, f"{detalhe} (desvio de {desvio_pp} p.p. ou mais).", "/alocacao")]


def _vencimentos(sessao: Session, investidor_ids: Sequence[int] | None, dias: int, hoje: date) -> list[Alerta]:
    alertas = []
    vistos: set[int] = set()
    for item in renda_fixa_liquida.listar(sessao, investidor_ids, hoje):
        restante = item.dias_para_vencer
        if restante is None or restante > dias or item.ativo.id in vistos:
            continue
        vistos.add(item.ativo.id)
        venc = f"{item.ativo.data_vencimento:%d/%m/%Y}"
        if restante < 0:
            alertas.append(Alerta(
                f"vencido:{item.ativo.ticker}", "alta", f"{item.ativo.ticker} venceu em {venc}",
                "Ainda há posição aberta: lance o resgate como venda para atualizar a carteira.", "/renda-fixa",
            ))
        else:
            alertas.append(Alerta(
                f"vencimento:{item.ativo.ticker}", "alta" if restante <= 7 else "media",
                f"{item.ativo.ticker} vence em {restante} dia(s)",
                f"Vencimento em {venc}; valor líquido estimado hoje {_moeda(item.atual.liquido)}.", "/renda-fixa",
            ))
    return alertas


def _darf(sessao: Session, investidor_ids: Sequence[int] | None, hoje: date) -> list[Alerta]:
    competencia = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)
    consulta = select(Investidor).where(Investidor.ativo)
    if investidor_ids:
        consulta = consulta.where(Investidor.id.in_(investidor_ids))
    alertas = []
    for inv in sessao.scalars(consulta):
        if not sessao.scalar(select(Operacao.id).where(Operacao.investidor_id == inv.id).limit(1)):
            continue
        mes = next((m for m in ir.apurar(sessao, inv.id, hoje).meses if m.competencia == competencia), None)
        if mes and mes.saldo > 0:
            alertas.append(Alerta(
                f"darf:{inv.id}", "alta", f"DARF de {inv.nome}: {_moeda(mes.saldo)}",
                f"Apuração de {competencia:%m/%Y} (código 6015); vence no último dia útil de {hoje:%m/%Y}. "
                "Registre o pagamento na tela de IR.",
                "/ir",
            ))
    return alertas


def _proventos(sessao: Session, investidor_ids: Sequence[int] | None, hoje: date) -> list[Alerta]:
    proximos = [i for i in agenda_proventos.calcular(sessao, investidor_ids, hoje).a_receber
                if i.data_pagamento <= hoje + timedelta(days=7)]
    if not proximos:
        return []
    total = sum(i.liquido for i in proximos)
    tickers = ", ".join(sorted({i.ticker for i in proximos}))
    return [Alerta(
        "proventos", "info", f"{len(proximos)} provento(s) nos próximos 7 dias", f"{_moeda(total)} · {tickers}",
        "/proventos",
    )]


def listar(sessao: Session, investidor_ids: Sequence[int] | None = None, hoje: date | None = None) -> list[Alerta]:
    hoje = hoje or date.today()
    params = parametros.carregar(sessao)
    fontes = [
        lambda: _darf(sessao, investidor_ids, hoje),
        lambda: _vencimentos(sessao, investidor_ids, params.alerta_vencimento_dias, hoje)
        if params.alerta_vencimento_dias else [],
        lambda: _preco_alvo(sessao),
        lambda: _alocacao(sessao, investidor_ids, params.alerta_desvio_pp) if params.alerta_desvio_pp else [],
        lambda: _proventos(sessao, investidor_ids, hoje),
        lambda: [
            Alerta("qualidade", "alta", f"{len(erros)} problema(s) nos dados",
                   "; ".join(v.titulo for v in erros) + ". Veja Configurações → Qualidade dos dados.",
                   "/configuracoes?secao=qualidade")
            for erros in [[v for v in qualidade.verificar(sessao, investidor_ids, hoje) if v.severidade == "erro"]]
            if erros
        ],
    ]
    alertas: list[Alerta] = []
    for fonte in fontes:
        try:
            alertas.extend(fonte())
        except Exception:  # um cálculo com dados incompletos não pode esconder os demais alertas
            log.exception("Falha ao calcular alertas")
    ordem = {"alta": 0, "media": 1, "info": 2}
    return sorted(alertas, key=lambda a: ordem[a.severidade])
