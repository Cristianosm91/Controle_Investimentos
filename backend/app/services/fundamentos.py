"""Atualização periódica dos snapshots de indicadores publicados para ativos B3."""

import logging
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from datetime import date

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Ativo, Fundamento
from ..providers import fundamentus, yahoo_fundamentos

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

_TICKERS_HISTORICOS = {"BRDT3": "VBBR3", "VIIA3": "BHIA3"}


@dataclass
class ResultadoFundamentos:
    atualizados: int = 0
    sem_dados: list[str] = field(default_factory=list)
    mercados_nao_suportados: list[str] = field(default_factory=list)
    classes_incompativeis: list[str] = field(default_factory=list)
    tickers_historicos: list[str] = field(default_factory=list)
    falhas: list[str] = field(default_factory=list)

    def resumo(self) -> str:
        partes = [f"{self.atualizados} ativos atualizados"]
        if self.sem_dados:
            partes.append(f"sem dados na fonte: {', '.join(sorted(self.sem_dados))}")
        if self.mercados_nao_suportados:
            partes.append(f"mercados não suportados: {', '.join(sorted(self.mercados_nao_suportados))}")
        if self.classes_incompativeis:
            partes.append(f"classe incompatível: {'; '.join(sorted(self.classes_incompativeis))}")
        if self.tickers_historicos:
            partes.append(
                f"ticker histórico (corrija manualmente, se aplicável): {'; '.join(sorted(self.tickers_historicos))}"
            )
        if self.falhas:
            partes.append(f"falhas de consulta: {'; '.join(self.falhas)}")
        return "; ".join(partes)


def _campos_linha(linha: Mapping[str, object]) -> dict[str, object]:
    return {campo: linha.get(campo) for campo in _CAMPOS}


def _gravar(
    sessao: Session,
    ativos: dict[str, Ativo],
    valores: Mapping[str, Mapping[str, object]],
    data_ref: date,
    fonte: str,
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
                Fundamento.fonte == fonte,
            )
        )
    }
    for ticker, indicadores in valores.items():
        ativo = ativos[ticker]
        fundamento = existentes.get(ativo.id)
        if fundamento is None:
            fundamento = Fundamento(ativo_id=ativo.id, data_ref=data_ref, fonte=fonte)
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
    """Atualiza snapshots e identifica ativos fora da cobertura das tabelas do Fundamentus."""
    consulta = select(Ativo).where(Ativo.cotacao_automatica.is_(True))
    if ativo_ids is not None:
        consulta = consulta.where(Ativo.id.in_(ativo_ids))
    ativos = {ativo.ticker: ativo for ativo in sessao.scalars(consulta)}
    resultado = ResultadoFundamentos()
    if not ativos:
        return resultado

    ativos_bvmf = {ticker: ativo for ticker, ativo in ativos.items() if (ativo.mercado or "").upper() == "BVMF"}
    ativos_yahoo = {
        ticker: ativo for ticker, ativo in ativos.items()
        if (ativo.mercado or "").upper() in yahoo_fundamentos.MERCADOS
    }
    ativos_sem_fonte = {
        ticker: ativo for ticker, ativo in ativos.items()
        if ticker not in ativos_bvmf and ticker not in ativos_yahoo
    }
    resultado.mercados_nao_suportados = sorted(
        f"{ticker} (mercado: {(ativo.mercado or 'não informado').upper()})"
        for ticker, ativo in ativos_sem_fonte.items()
    )
    alvos_fii = {
        ticker: ativo for ticker, ativo in ativos_bvmf.items() if ativo.classe.upper() in {"FII", "FIAGRO"}
    }
    alvos_acoes = {ticker: ativo for ticker, ativo in ativos_bvmf.items() if ticker not in alvos_fii}
    if not ativos_bvmf and not ativos_yahoo:
        return resultado

    proprietario_cliente = bool(ativos_bvmf) and cliente is None
    if proprietario_cliente:
        cliente = fundamentus.cliente_http()
    try:
        dados_acoes: Mapping[str, Mapping[str, object]] | None = None
        dados_fii: Mapping[str, Mapping[str, object]] | None = None
        if alvos_acoes:
            try:
                dados_acoes = fundamentus.buscar_acoes(cliente)
            except fundamentus.ErroFundamentus as erro:
                resultado.falhas.append(f"Ações: {erro}; não verificados: {', '.join(sorted(alvos_acoes))}")
                log.warning("Falha na coleta de fundamentos de ações: %s", erro)
        if alvos_fii:
            try:
                dados_fii = fundamentus.buscar_fiis(cliente)
            except fundamentus.ErroFundamentus as erro:
                resultado.falhas.append(f"FIIs: {erro}; não verificados: {', '.join(sorted(alvos_fii))}")
                log.warning("Falha na coleta de fundamentos de FIIs: %s", erro)

        faltantes_acoes = {ticker for ticker in alvos_acoes if dados_acoes is None or ticker not in dados_acoes}
        faltantes_fii = {ticker for ticker in alvos_fii if dados_fii is None or ticker not in dados_fii}
        if faltantes_acoes and dados_fii is None:
            try:
                dados_fii = fundamentus.buscar_fiis(cliente)
            except fundamentus.ErroFundamentus as erro:
                resultado.falhas.append(f"FIIs (verificação de classe): {erro}")
                log.warning("Falha na verificação de classe de FIIs: %s", erro)
        if faltantes_fii and dados_acoes is None:
            try:
                dados_acoes = fundamentus.buscar_acoes(cliente)
            except fundamentus.ErroFundamentus as erro:
                resultado.falhas.append(f"Ações (verificação de classe): {erro}")
                log.warning("Falha na verificação de classe de ações: %s", erro)

        data_ref = hoje or date.today()
        valores_acoes = {
            ticker: dados_acoes[ticker] for ticker in alvos_acoes if dados_acoes is not None and ticker in dados_acoes
        }
        valores_fii = {
            ticker: dados_fii[ticker] for ticker in alvos_fii if dados_fii is not None and ticker in dados_fii
        }
        resultado.atualizados += _gravar(sessao, alvos_acoes, valores_acoes, data_ref, fundamentus.FONTE)
        resultado.atualizados += _gravar(sessao, alvos_fii, valores_fii, data_ref, fundamentus.FONTE)

        for ticker, ativo in ativos_bvmf.items():
            esperado = dados_fii if ticker in alvos_fii else dados_acoes
            alternativo = dados_acoes if ticker in alvos_fii else dados_fii
            if esperado is not None and ticker in esperado:
                continue
            if alternativo is not None and ticker in alternativo:
                classe_fonte = "ações" if alternativo is dados_acoes else "FIIs"
                resultado.classes_incompativeis.append(
                    f"{ticker} cadastrado como {ativo.classe}, encontrado na tabela de {classe_fonte}"
                )
            elif esperado is not None:
                ticker_atual = _TICKERS_HISTORICOS.get(ticker)
                if ticker_atual:
                    resultado.tickers_historicos.append(f"{ticker} (possível atual: {ticker_atual})")
                else:
                    resultado.sem_dados.append(ticker)

        valores_yahoo, falhas_yahoo = yahoo_fundamentos.buscar(sorted(ativos_yahoo))
        resultado.falhas.extend(f"Yahoo Finance ({ticker}): {erro}" for ticker, erro in sorted(falhas_yahoo.items()))
        resultado.atualizados += _gravar(
            sessao, ativos_yahoo, valores_yahoo, data_ref, yahoo_fundamentos.FONTE,
        )
        resultado.sem_dados.extend(sorted(set(ativos_yahoo) - valores_yahoo.keys() - falhas_yahoo.keys()))

        if valores_acoes or valores_fii or valores_yahoo:
            sessao.commit()
        return resultado
    except Exception:
        sessao.rollback()
        raise
    finally:
        if proprietario_cliente and cliente is not None:
            cliente.close()
