"""Séries históricas de apoio à rentabilidade: índices mensais, PTAX diária e preços fora da B3."""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import insert_upsert
from ..models import Ativo, CotacaoMoeda, IndiceMensal, Operacao
from ..providers import indices as fontes
from ..providers.base import AtivoRef
from ..providers.yahoo import ProvedorYahoo
from . import cotahist

log = logging.getLogger(__name__)

FONTE_PTAX = "BCB PTAX"


@dataclass
class ResultadoHistorico:
    gravados: dict[str, int] = field(default_factory=dict)
    falhas: list[str] = field(default_factory=list)

    def resumo(self) -> str:
        texto = ", ".join(f"{k}: {v}" for k, v in self.gravados.items()) or "nada gravado"
        return texto + (f"; falhas: {'; '.join(self.falhas)}" if self.falhas else "")


def _primeira_data(sessao: Session) -> date:
    primeira = sessao.scalar(select(func.min(Operacao.data)))
    return primeira or date.today().replace(month=1, day=1)


def atualizar_indices(sessao: Session, desde: date | None = None) -> ResultadoHistorico:
    """Grava em `indice_mensal` a variação mensal (fração) das séries SGS e o nível de fim de mês da B3."""
    # Um mês antes: a variação de IBOV/IFIX no 1º mês precisa do nível do mês anterior.
    inicio = ((desde or _primeira_data(sessao)).replace(day=1) - timedelta(days=1)).replace(day=1)
    hoje = date.today()
    resultado = ResultadoHistorico()
    valores: dict[date, dict[str, Decimal]] = {}

    with httpx.Client() as cliente:
        for coluna, serie in fontes.SERIES_MENSAIS.items():
            try:
                for dia, pct in fontes.serie_sgs(serie, inicio, hoje, cliente).items():
                    valores.setdefault(dia.replace(day=1), {})[coluna] = pct / 100
            except fontes.ErroIndice as erro:
                log.warning("%s", erro)
                resultado.falhas.append(coluna)
        for coluna, codigo in fontes.INDICES_B3.items():
            diarios: dict[date, Decimal] = {}
            try:
                for ano in range(inicio.year, hoje.year + 1):
                    diarios.update(fontes.indice_b3(codigo, ano, cliente))
            except fontes.ErroIndice as erro:
                log.warning("%s", erro)
                resultado.falhas.append(coluna)
            for competencia, nivel in fontes.fechamentos_mensais(diarios).items():
                if competencia >= inicio:
                    valores.setdefault(competencia, {})[coluna] = nivel

    for competencia, campos in valores.items():
        linha = sessao.get(IndiceMensal, competencia) or IndiceMensal(competencia=competencia)
        for coluna, valor in campos.items():
            setattr(linha, coluna, valor)
        sessao.merge(linha)
    sessao.commit()
    resultado.gravados["meses"] = len(valores)
    return resultado


def carregar_ptax_historica(sessao: Session, desde: date | None = None) -> ResultadoHistorico:
    """PTAX de venda diária (SGS) em `cotacao_moeda`, para converter posições em moeda estrangeira no passado."""
    inicio = desde or _primeira_data(sessao)
    resultado = ResultadoHistorico()
    with httpx.Client() as cliente:
        for moeda, serie in fontes.SERIES_PTAX_VENDA.items():
            try:
                diarios = fontes.serie_sgs(serie, inicio, date.today(), cliente)
            except fontes.ErroIndice as erro:
                log.warning("%s", erro)
                resultado.falhas.append(moeda)
                continue
            linhas = [{"moeda": moeda, "data": d, "valor": v, "fonte": FONTE_PTAX} for d, v in diarios.items()]
            for i in range(0, len(linhas), 500):
                lote = insert_upsert(sessao, CotacaoMoeda).values(linhas[i : i + 500])
                sessao.execute(
                    lote.on_conflict_do_update(
                        index_elements=["moeda", "data"],
                        set_={"valor": lote.excluded.valor, "fonte": lote.excluded.fonte, "atualizado_em": func.now()},
                    )
                )
            sessao.commit()
            resultado.gravados[moeda] = len(linhas)
    return resultado


def carregar_historico_exterior(sessao: Session, desde: date | None = None) -> ResultadoHistorico:
    """Fechamentos diários do Yahoo para ativos negociados fora da B3 que já tiveram operação."""
    inicio = desde or _primeira_data(sessao)
    ativos = list(
        sessao.scalars(
            select(Ativo).where(
                Ativo.mercado.is_not(None),
                Ativo.mercado != "BVMF",
                Ativo.id.in_(select(Operacao.ativo_id).distinct()),
            )
        )
    )
    resultado = ResultadoHistorico()
    if not ativos:
        return resultado
    historico = ProvedorYahoo().historico([AtivoRef(a.ticker, a.mercado, a.moeda) for a in ativos], inicio)
    ids = {a.ticker: a.id for a in ativos}
    fechamentos = [
        cotahist.Fechamento(ticker, dia, preco, Decimal(0))
        for ticker, serie in historico.items()
        for dia, preco in serie.items()
    ]
    resultado.gravados["cotações"] = cotahist.gravar(
        sessao, fechamentos, ids, fonte=ProvedorYahoo.nome, preservar_fonte=cotahist.FONTE
    )
    resultado.falhas.extend(sorted(set(ids) - set(historico)))
    return resultado


def carregar_tudo(sessao: Session) -> ResultadoHistorico:
    """Histórico complementar completo: índices, PTAX e preços do exterior."""
    return _combinar(sessao, (atualizar_indices, carregar_ptax_historica, carregar_historico_exterior), None)


def atualizar_recentes(sessao: Session) -> ResultadoHistorico:
    """Rotina diária: só as últimas semanas (meses ainda abertos de índices, PTAX e exterior)."""
    return _combinar(sessao, (atualizar_indices, carregar_ptax_historica, carregar_historico_exterior), 45)


def _combinar(sessao: Session, etapas, dias: int | None) -> ResultadoHistorico:
    desde = date.today() - timedelta(days=dias) if dias else None
    total = ResultadoHistorico()
    for etapa in etapas:
        r = etapa(sessao, desde)
        total.gravados.update(r.gravados)
        total.falhas.extend(r.falhas)
    return total
