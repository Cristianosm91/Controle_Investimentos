"""Atualização periódica dos snapshots de indicadores publicados para ativos B3."""

import logging
from collections.abc import Collection
from dataclasses import dataclass, field
from datetime import date

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Ativo, Fundamento
from ..providers import fundamentus

log = logging.getLogger(__name__)

_CAMPOS = (
    "preco_lucro",
    "preco_valor_patrimonial",
    "dividend_yield",
    "psr",
    "roe",
    "roic",
    "margem_bruta",
    "margem_ebit",
    "margem_liquida",
    "liquidez_corrente",
    "liquidez_media_2m",
    "patrimonio_liquido",
    "valor_mercado",
    "divida_liquida_patrimonio",
    "crescimento_receita_5a",
    "segmento_fii",
    "fii_dividendos_meses_12m",
    "fii_dividend_yield_2a",
    "fii_dividendos_meses_2a",
    "fii_ffo_yield",
    "fii_liquidez",
    "fii_area_m2",
    "fii_preco_m2",
    "fii_numero_imoveis",
    "fii_numero_unidades",
)


@dataclass
class ResultadoFundamentos:
    atualizados: int = 0
    sem_dados: list[str] = field(default_factory=list)
    falhas: list[str] = field(default_factory=list)

    def resumo(self) -> str:
        partes = [f"{self.atualizados} ativos atualizados"]
        if self.sem_dados:
            partes.append(f"sem dados: {', '.join(sorted(self.sem_dados))}")
        if self.falhas:
            partes.append(f"falhas: {'; '.join(self.falhas)}")
        return "; ".join(partes)


def _campos_linha(linha: dict[str, object]) -> dict[str, object]:
    return {campo: linha.get(campo) for campo in _CAMPOS}


def _gravar(
    sessao: Session,
    ativos: dict[str, Ativo],
    valores: dict[str, dict[str, object]],
    data_ref: date,
) -> int:
    if not valores:
        return 0
    ids = {ativos[ticker].id for ticker in valores}
    existentes = {
        fundamento.ativo_id: fundamento
        for fundamento in sessao.scalars(
            select(Fundamento).where(
                Fundamento.ativo_id.in_(ids),
                Fundamento.data_ref == data_ref,
                Fundamento.fonte == fundamentus.FONTE,
            )
        )
    }
    for ticker, indicadores in valores.items():
        ativo = ativos[ticker]
        fundamento = existentes.get(ativo.id)
        if fundamento is None:
            fundamento = Fundamento(ativo_id=ativo.id, data_ref=data_ref, fonte=fundamentus.FONTE)
            sessao.add(fundamento)
        for campo, valor in _campos_linha(indicadores).items():
            setattr(fundamento, campo, valor)
    return len(valores)


def atualizar(
    sessao: Session,
    cliente: httpx.Client | None = None,
    hoje: date | None = None,
    ativo_ids: Collection[int] | None = None,
) -> ResultadoFundamentos:
    """Atualiza snapshots uma vez por dia, consultando somente as tabelas públicas necessárias."""
    consulta = select(Ativo).where(Ativo.cotacao_automatica.is_(True), Ativo.mercado == "BVMF")
    if ativo_ids is not None:
        consulta = consulta.where(Ativo.id.in_(ativo_ids))
    ativos = {ativo.ticker: ativo for ativo in sessao.scalars(consulta)}
    resultado = ResultadoFundamentos()
    if not ativos:
        return resultado

    alvos_fii = {ticker: ativo for ticker, ativo in ativos.items() if ativo.classe.upper() in {"FII", "FIAGRO"}}
    alvos_acoes = {ticker: ativo for ticker, ativo in ativos.items() if ticker not in alvos_fii}
    proprietario_cliente = cliente is None
    cliente = cliente or fundamentus.cliente_http()
    try:
        resultados: list[tuple[dict[str, Ativo], dict[str, dict[str, object]]]] = []
        if alvos_acoes:
            try:
                dados = fundamentus.buscar_acoes(cliente)
                resultados.append(({k: v for k, v in alvos_acoes.items() if k in dados}, {
                    ticker: dados[ticker] for ticker in alvos_acoes if ticker in dados
                }))
            except fundamentus.ErroFundamentus as erro:
                resultado.falhas.append(f"Ações: {erro}")
                log.warning("Falha na coleta de fundamentos de ações: %s", erro)
        if alvos_fii:
            try:
                dados_fii = fundamentus.buscar_fiis(cliente)
                resultados.append(({k: v for k, v in alvos_fii.items() if k in dados_fii}, {
                    ticker: dados_fii[ticker] for ticker in alvos_fii if ticker in dados_fii
                }))
            except fundamentus.ErroFundamentus as erro:
                resultado.falhas.append(f"FIIs: {erro}")
                log.warning("Falha na coleta de fundamentos de FIIs: %s", erro)

        data_ref = hoje or date.today()
        for ativos_tipo, dados_tipo in resultados:
            resultado.atualizados += _gravar(sessao, ativos_tipo, dados_tipo, data_ref)

        encontrados = {ticker for _, dados in resultados for ticker in dados}
        resultado.sem_dados = sorted(set(ativos) - encontrados)
        if resultados:
            sessao.commit()
        return resultado
    except Exception:
        sessao.rollback()
        raise
    finally:
        if proprietario_cliente:
            cliente.close()
