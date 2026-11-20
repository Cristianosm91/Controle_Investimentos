"""Histórico local de alterações nos lançamentos financeiros."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import HistoricoLancamento, MovCaixa, Operacao, Provento

_CAMPOS = {
    Operacao: (
        "investidor_id", "ativo_id", "corretora_id", "data", "evento", "quantidade", "preco", "taxas", "irrf",
        "moeda", "cambio", "daytrade", "transferencia_pareada_id", "cripto_valor_original", "cripto_cambio_usd",
        "cripto_cambio_usd_data_moeda", "cripto_cambio_usd_data_usd", "cripto_cambio_usd_fonte", "cripto_valor_usd",
        "taxas_moeda", "taxas_cambio_brl", "taxas_cambio_usd", "taxas_cambio_usd_data_moeda",
        "taxas_cambio_usd_data_usd", "taxas_cambio_usd_fonte", "taxas_valor_usd",
    ),
    Provento: (
        "investidor_id", "ativo_id", "corretora_id", "data_pagamento", "data_com", "evento", "valor", "irrf",
        "taxas", "moeda", "cambio",
    ),
    MovCaixa: ("investidor_id", "corretora_id", "data", "evento", "valor", "moeda"),
}


def _serializar(valor):
    if isinstance(valor, Decimal):
        return format(valor, "f")
    if isinstance(valor, date | datetime):
        return valor.isoformat()
    return valor


def snapshot(objeto: Operacao | Provento | MovCaixa) -> dict[str, object]:
    return {campo: _serializar(getattr(objeto, campo)) for campo in _CAMPOS[type(objeto)]}


def registrar(
    sessao: Session,
    objeto: Operacao | Provento | MovCaixa,
    acao: str,
    anterior: dict[str, object] | None = None,
) -> None:
    if objeto.id is None:
        raise ValueError("O lançamento precisa estar salvo antes de registrar a auditoria")
    estado = snapshot(objeto) if acao != "excluido" else None
    sessao.add(
        HistoricoLancamento(
            entidade=type(objeto).__name__.lower(),
            registro_id=objeto.id,
            acao=acao,
            investidor_id=objeto.investidor_id,
            ativo_id=getattr(objeto, "ativo_id", None),
            ocorrido_em=datetime.now(UTC),
            anterior_json=json.dumps(anterior, ensure_ascii=False, sort_keys=True) if anterior is not None else None,
            novo_json=json.dumps(estado, ensure_ascii=False, sort_keys=True) if estado is not None else None,
        )
    )


def listar(sessao: Session, investidores: list[int] | None, limite: int) -> list[HistoricoLancamento]:
    from sqlalchemy import select

    consulta = select(HistoricoLancamento)
    if investidores:
        consulta = consulta.where(HistoricoLancamento.investidor_id.in_(investidores))
    return list(
        sessao.scalars(
            consulta.order_by(HistoricoLancamento.ocorrido_em.desc(), HistoricoLancamento.id.desc()).limit(limite)
        )
    )
