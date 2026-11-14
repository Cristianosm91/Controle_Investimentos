"""Correção explícita da moeda cadastrada, sem conversão dos valores informados."""

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Ativo, Operacao, Provento
from ..providers import bcb
from ..providers.base import CotacaoAtual
from . import backup, cotacoes, jobs

log = logging.getLogger(__name__)


@contextmanager
def corrigir(sessao: Session, ativo: Ativo, moeda: str, confirmado: bool) -> Iterator[None]:
    if moeda == ativo.moeda:
        yield
        return
    operacoes = list(sessao.scalars(select(Operacao).where(Operacao.ativo_id == ativo.id)))
    proventos = list(sessao.scalars(select(Provento).where(Provento.ativo_id == ativo.id)))
    if not operacoes and not proventos:
        ativo.moeda = moeda
        yield
        return
    if not confirmado:
        raise HTTPException(
            409, "Confirme a correção da moeda: todos os lançamentos do ativo serão relabelados, "
            "sem converter preços ou valores, com PTAX histórica e backup obrigatório.",
        )
    if not jobs.usa_sqlite() or not settings.db_path.is_file():
        raise HTTPException(409, "A correção dos lançamentos exige backup local. Nada foi alterado.")
    moeda_anterior = ativo.moeda
    datas = {o.data for o in operacoes} | {p.data_pagamento for p in proventos}
    try:
        boletins = {dia: bcb.ptax(moeda, dia) for dia in sorted(datas)}
    except bcb.ErroPtax as erro:
        log.warning("Correção de moeda do ativo %s cancelada: PTAX indisponível", ativo.id)
        raise HTTPException(422, "PTAX histórica indisponível. Nada foi alterado; tente novamente.") from erro
    cambios = {dia: p.venda for dia, p in boletins.items()}
    if any(not valor.is_finite() or valor <= 0 for valor in cambios.values()):
        raise HTTPException(422, "PTAX histórica inválida. Nada foi alterado.")
    try:
        with jobs.exclusivo():
            # Impede novos lancamentos entre a fotografia do backup e a correcao.
            sessao.connection().exec_driver_sql("BEGIN IMMEDIATE")
            sessao.refresh(ativo)
            operacoes = list(sessao.scalars(
                select(Operacao).where(Operacao.ativo_id == ativo.id).execution_options(populate_existing=True)
            ))
            proventos = list(sessao.scalars(
                select(Provento).where(Provento.ativo_id == ativo.id).execution_options(populate_existing=True)
            ))
            datas_atuais = {o.data for o in operacoes} | {p.data_pagamento for p in proventos}
            if ativo.moeda != moeda_anterior or not datas_atuais <= cambios.keys():
                sessao.rollback()
                raise HTTPException(409, "O cadastro ou os lançamentos mudaram durante a consulta da PTAX. Tente novamente.")
            try:
                arquivo = backup.gerar(settings.db_path, "manual", motivo="correcao-moeda-ativo")
            except (OSError, sqlite3.Error, backup.BackupInvalido) as erro:
                log.exception("Backup antes da correção de moeda falhou")
                raise HTTPException(409, "Falha no backup obrigatório. Nada foi alterado.") from erro
            anterior = ativo.moeda
            ativo.moeda = moeda
            for operacao in operacoes:
                operacao.moeda, operacao.cambio = moeda, cambios[operacao.data]
            for provento in proventos:
                provento.moeda, provento.cambio = moeda, cambios[provento.data_pagamento]
            try:
                if moeda != "BRL":
                    for p in boletins.values():
                        cotacoes.gravar_cambio(sessao, moeda, CotacaoAtual(moeda, p.venda, None, p.data, bcb.FONTE))
                yield
            except Exception:
                sessao.rollback()
                raise
            log.info(
                "Moeda do ativo %s corrigida de %s para %s: %s operações, %s proventos; backup %s",
                ativo.id, anterior, moeda, len(operacoes), len(proventos), arquivo.name,
            )
    except jobs.TarefaOcupada as erro:
        raise HTTPException(409, "Aguarde as atualizações terminarem antes de corrigir a moeda.") from erro
