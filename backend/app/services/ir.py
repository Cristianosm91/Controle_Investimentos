"""Apuração do IR de renda variável: DARF mensal (código 6015) e exterior (GCAP até 2023, anual desde 2024).

As funções de cálculo são puras; `carregar_*` e `apurar` fazem a leitura do banco. O IR é sempre por CPF.
Resultado é estimativa: confira no e-CAC/GCAP antes de recolher.
"""

import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dominio import DARF_MINIMO, GRUPO_PREJUIZO
from ..models import Ativo, DarfPago, Operacao, PrejuizoInicial, Provento, RegraFiscal
from . import parametros as param
from .posicao import ZERO, Carteira, Movimento

CENTAVO = Decimal("0.01")
CATEGORIAS_MENSAIS = ("ACAO", "BDR", "ETF", "OPCAO", "DAYTRADE", "FII")
GRUPOS_MENSAIS = ("COMUM", "DAYTRADE", "FII")
_SAIDAS = ("V", "VENDA_SUBSCRICAO")


def centavos(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, ROUND_HALF_UP)


def mes(dia: date) -> date:
    return dia.replace(day=1)


def proximo_mes(dia: date) -> date:
    return date(dia.year + dia.month // 12, dia.month % 12 + 1, 1)


# ---------- Regras com vigência ----------

@dataclass(frozen=True)
class Regra:
    categoria: str
    inicio: date
    fim: date | None
    aliquota: Decimal
    limite_isencao: Decimal | None = None
    apuracao: str = "MENSAL"


def _r(categoria: str, inicio: str, fim: str | None, aliquota: str, limite: str | None = None, apuracao: str = "MENSAL"):
    return Regra(
        categoria, date.fromisoformat(inicio), date.fromisoformat(fim) if fim else None, Decimal(aliquota),
        Decimal(limite) if limite else None, apuracao,
    )


# Mesmos valores carregados pela migração; usados quando a tabela `regra_fiscal` está vazia.
REGRAS_PADRAO = [
    _r("ACAO", "2005-01-01", None, "0.15", "20000"),
    _r("BDR", "2005-01-01", None, "0.15"),
    _r("ETF", "2005-01-01", None, "0.15"),
    _r("OPCAO", "2005-01-01", None, "0.15"),
    _r("DAYTRADE", "2005-01-01", None, "0.20"),
    _r("FII", "2005-01-01", None, "0.20"),
    _r("EXTERIOR", "2005-01-01", "2023-12-31", "0.15", "35000"),
    _r("EXTERIOR", "2024-01-01", None, "0.15", apuracao="ANUAL"),
]


def regra_vigente(regras: Iterable[Regra], categoria: str, dia: date) -> Regra | None:
    """Regra da categoria vigente no dia; em sobreposição vale a de início mais recente."""
    candidatas = [r for r in regras if r.categoria == categoria and r.inicio <= dia and (r.fim is None or dia <= r.fim)]
    return max(candidatas, key=lambda r: r.inicio, default=None)


# ---------- Classificação ----------

def _normalizar(classe: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", classe).encode("ascii", "ignore").decode()
    return sem_acento.strip().upper()


_CLASSES_BOLSA = {"ACAO": "ACAO", "UNIT": "ACAO", "BDR": "BDR", "ETF": "ETF", "INDICE": "ETF", "OPCAO": "OPCAO"}


def categoria_ir(classe: str, moeda: str, daytrade: bool, bdr_como_acao: bool = False) -> str | None:
    """Categoria de IR do ativo; None = fora da apuração de renda variável (renda fixa, caixa, cripto...)."""
    c = _normalizar(classe)
    if moeda != "BRL" or c.startswith(("STOCK", "REIT", "ETF_")):
        return "EXTERIOR"
    if c in ("FII", "FIAGRO"):
        return "FII"
    categoria = _CLASSES_BOLSA.get(c)
    if categoria == "BDR" and bdr_como_acao:
        categoria = "ACAO"
    if categoria and daytrade:
        return "DAYTRADE"
    return categoria


# ---------- Fatos mensais (vendas, lucro e IRRF por categoria) ----------

@dataclass(frozen=True)
class OperacaoIR:
    movimento: Movimento
    ticker: str
    classe: str
    moeda: str
    irrf: Decimal = ZERO


@dataclass
class Fato:
    vendas: Decimal = ZERO
    lucro: Decimal = ZERO
    irrf: Decimal = ZERO


Fatos = dict[tuple[date, str], Fato]


def fatos_por_mes(operacoes: Iterable[OperacaoIR], bdr_como_acao: bool = False) -> tuple[Fatos, set[str]]:
    """Agrupa vendas, lucro realizado e IRRF por (mês, categoria). Devolve também os tickers vendidos fora da apuração."""
    carteira = Carteira()
    fatos: Fatos = defaultdict(Fato)
    ignorados: set[str] = set()
    for op in sorted(operacoes, key=lambda o: (o.movimento.data, o.movimento.ordem)):
        m = op.movimento
        lucro = carteira.aplicar(m)
        venda = m.evento in _SAIDAS
        if not venda and not op.irrf:
            continue
        categoria = categoria_ir(op.classe, op.moeda, m.daytrade, bdr_como_acao)
        if categoria is None:
            if venda:
                ignorados.add(op.ticker)
            continue
        f = fatos[(mes(m.data), categoria)]
        f.irrf += op.irrf * m.cambio
        if venda:
            f.vendas += -m.quantidade * m.preco * m.cambio
            f.lucro += lucro
    return dict(fatos), ignorados


# ---------- Apuração mensal (DARF 6015) ----------

@dataclass
class ResultadoCategoria:
    categoria: str
    vendas: Decimal
    lucro: Decimal
    isento: bool
    base: Decimal  # lucro tributável após compensar prejuízo
    aliquota: Decimal | None
    imposto: Decimal


@dataclass
class MesIR:
    competencia: date
    categorias: list[ResultadoCategoria]
    prejuizo: dict[str, Decimal]  # saldo a compensar ao fim do mês, por grupo
    imposto: Decimal
    irrf: Decimal
    irrf_compensado: Decimal
    irrf_saldo: Decimal  # a compensar nos meses seguintes do mesmo ano
    darf_mes: Decimal  # imposto − IRRF compensado
    darf_anterior: Decimal  # valores abaixo do mínimo trazidos de meses anteriores
    darf: Decimal  # a recolher; zero quando o total não atinge o mínimo
    darf_transportado: Decimal  # vai para o mês seguinte por não atingir o mínimo
    pago: Decimal

    @property
    def saldo(self) -> Decimal:
        return self.darf - self.pago


def _compensar(tributavel: dict[str, Decimal], prejuizo: Decimal, categorias: list[str]) -> tuple[dict[str, Decimal], Decimal]:
    """Abate perdas do mês e o prejuízo acumulado dos lucros do grupo; devolve a base por categoria e o novo saldo."""
    perdas = prejuizo + sum((-tributavel[c] for c in categorias if tributavel[c] < 0), ZERO)
    base = {}
    for c in categorias:
        ganho = max(tributavel[c], ZERO)
        usado = min(ganho, perdas)
        perdas -= usado
        base[c] = ganho - usado
    return base, perdas


def apurar_mensal(
    fatos: Mapping[tuple[date, str], Fato],
    regras: Iterable[Regra],
    inicio: date,
    fim: date,
    prejuizo_inicial: Mapping[str, Decimal] | None = None,
    pagos: Mapping[date, Decimal] | None = None,
    daytrade_no_limite: bool = False,
) -> list[MesIR]:
    regras = list(regras)
    prejuizo = {g: Decimal((prejuizo_inicial or {}).get(g, ZERO)) for g in GRUPOS_MENSAIS}
    pagos = pagos or {}
    irrf_saldo = transportado = ZERO
    meses: list[MesIR] = []
    comp = mes(inicio)
    while comp <= fim:
        if comp.month == 1:
            irrf_saldo = ZERO  # saldo de IRRF não compensado no ano vai para a declaração anual
        doc = {c: fatos.get((comp, c), Fato()) for c in CATEGORIAS_MENSAIS}
        vendas_acoes = doc["ACAO"].vendas + (doc["DAYTRADE"].vendas if daytrade_no_limite else ZERO)

        tributavel, isento, regra_cat = {}, {}, {}
        for c in CATEGORIAS_MENSAIS:
            regra = regra_vigente(regras, c, comp)
            regra_cat[c] = regra if regra and regra.apuracao == "MENSAL" else None
            vendas = vendas_acoes if c == "ACAO" else doc[c].vendas
            limite = regra_cat[c].limite_isencao if regra_cat[c] else None
            isento[c] = limite is not None and ZERO < vendas <= limite
            # Lucro de mês isento não é tributado, mas o prejuízo continua compensável.
            tributavel[c] = ZERO if isento[c] and doc[c].lucro > 0 else doc[c].lucro

        base: dict[str, Decimal] = {}
        for g in GRUPOS_MENSAIS:
            cats = [c for c in CATEGORIAS_MENSAIS if GRUPO_PREJUIZO[c] == g]
            base_grupo, prejuizo[g] = _compensar(tributavel, prejuizo[g], cats)
            base.update(base_grupo)

        resultados = []
        for c in CATEGORIAS_MENSAIS:
            aliquota = regra_cat[c].aliquota if regra_cat[c] else None
            imposto = centavos(base[c] * aliquota) if aliquota is not None else ZERO
            resultados.append(ResultadoCategoria(c, doc[c].vendas, doc[c].lucro, isento[c], base[c], aliquota, imposto))

        imposto = sum((r.imposto for r in resultados), ZERO)
        irrf = sum((doc[c].irrf for c in CATEGORIAS_MENSAIS), ZERO)
        disponivel = irrf_saldo + irrf
        compensado = min(imposto, disponivel)
        irrf_saldo = disponivel - compensado
        darf_mes = imposto - compensado
        total = centavos(darf_mes + transportado)
        anterior = transportado
        darf = total if total >= DARF_MINIMO else ZERO
        transportado = ZERO if darf else total

        meses.append(MesIR(
            comp, resultados, dict(prejuizo), imposto, irrf, compensado, irrf_saldo, darf_mes, anterior, darf,
            transportado, pagos.get(comp, ZERO),
        ))
        comp = proximo_mes(comp)
    return meses


# ---------- Exterior ----------

@dataclass
class AnoExterior:
    ano: int
    vendas: Decimal = ZERO
    lucro: Decimal = ZERO
    dividendos: Decimal = ZERO  # rendimentos brutos em BRL (entram na base anual desde 2024)
    imposto_pago_exterior: Decimal = ZERO
    base: Decimal = ZERO
    imposto: Decimal = ZERO
    prejuizo: Decimal = ZERO  # saldo a compensar ao fim do ano (apuração anual)
    regimes: list[str] = field(default_factory=list)


def apurar_exterior(
    fatos: Mapping[tuple[date, str], Fato],
    regras: Iterable[Regra],
    anos: Iterable[int],
    proventos: Mapping[int, tuple[Decimal, Decimal]] | None = None,
    prejuizo_inicial: Decimal = ZERO,
) -> list[AnoExterior]:
    """Até 2023: ganho de capital mensal (isenção por vendas no mês, sem compensação).
    Desde 2024 (Lei 14.754/2023): lucros e dividendos somados no ano, com compensação de prejuízo
    e dedução do imposto pago no exterior (limitada ao imposto brasileiro sobre os dividendos).
    """
    regras = list(regras)
    proventos = proventos or {}
    prejuizo = prejuizo_inicial
    resultado = []
    for ano in sorted(set(anos)):
        a = AnoExterior(ano)
        anual = ZERO
        regra_anual: Regra | None = None
        for m in range(1, 13):
            comp = date(ano, m, 1)
            f = fatos.get((comp, "EXTERIOR"), Fato())
            a.vendas += f.vendas
            a.lucro += f.lucro
            regra = regra_vigente(regras, "EXTERIOR", comp)
            if regra is None:
                continue
            if regra.apuracao not in a.regimes:
                a.regimes.append(regra.apuracao)
            if regra.apuracao == "ANUAL":
                anual += f.lucro
                regra_anual = regra
            elif f.lucro > 0 and (regra.limite_isencao is None or f.vendas > regra.limite_isencao):
                a.base += f.lucro
                a.imposto += centavos(f.lucro * regra.aliquota)

        if regra_anual is not None:
            a.dividendos, a.imposto_pago_exterior = proventos.get(ano, (ZERO, ZERO))
            liquido = anual - prejuizo
            ganho = max(liquido, ZERO)
            prejuizo = max(-liquido, ZERO)
            imposto_dividendos = centavos(a.dividendos * regra_anual.aliquota)
            credito = min(a.imposto_pago_exterior, imposto_dividendos)
            a.base += ganho + a.dividendos
            a.imposto += centavos(ganho * regra_anual.aliquota) + imposto_dividendos - credito
        a.prejuizo = prejuizo
        resultado.append(a)
    return resultado


# ---------- Leitura do banco ----------

def carregar_regras(sessao: Session) -> list[Regra]:
    linhas = sessao.scalars(select(RegraFiscal)).all()
    if not linhas:
        return list(REGRAS_PADRAO)
    return [
        Regra(r.categoria, r.vigencia_inicio, r.vigencia_fim, r.aliquota, r.limite_isencao, r.apuracao) for r in linhas
    ]


def carregar_operacoes(sessao: Session, investidor_id: int) -> list[OperacaoIR]:
    consulta = (
        select(Operacao, Ativo.ticker, Ativo.classe, Ativo.moeda)
        .join(Ativo, Ativo.id == Operacao.ativo_id)
        .where(Operacao.investidor_id == investidor_id)
    )
    return [
        OperacaoIR(
            Movimento(o.investidor_id, o.ativo_id, o.data, o.evento, o.quantidade, o.preco, o.taxas, o.daytrade, o.id, o.cambio),
            ticker, classe, moeda, o.irrf,
        )
        for o, ticker, classe, moeda in sessao.execute(consulta)
    ]


def _proventos_exterior(sessao: Session, investidor_id: int) -> dict[int, tuple[Decimal, Decimal]]:
    """(rendimento bruto, imposto retido no exterior) em BRL por ano."""
    consulta = (
        select(Provento.data_pagamento, Provento.valor, Provento.irrf, Provento.cambio, Ativo.classe, Ativo.moeda)
        .join(Ativo, Ativo.id == Provento.ativo_id)
        .where(Provento.investidor_id == investidor_id, Provento.evento != "AMORTIZACAO")
    )
    por_ano: dict[int, tuple[Decimal, Decimal]] = {}
    for dia, valor, irrf, cambio, classe, moeda in sessao.execute(consulta):
        if categoria_ir(classe, moeda, False) != "EXTERIOR":
            continue
        bruto, retido = por_ano.get(dia.year, (ZERO, ZERO))
        por_ano[dia.year] = (bruto + valor * cambio, retido + irrf * cambio)
    return por_ano


def carregar_prejuizos(sessao: Session, investidor_id: int) -> dict[str, Decimal]:
    consulta = select(PrejuizoInicial).where(PrejuizoInicial.investidor_id == investidor_id)
    return {p.grupo: p.valor for p in sessao.scalars(consulta)}


def carregar_pagos(sessao: Session, investidor_id: int) -> dict[date, Decimal]:
    pagos: dict[date, Decimal] = defaultdict(lambda: ZERO)
    for d in sessao.scalars(select(DarfPago).where(DarfPago.investidor_id == investidor_id)):
        pagos[mes(d.competencia)] += d.valor
    return dict(pagos)


@dataclass
class ApuracaoIR:
    meses: list[MesIR]
    exterior: list[AnoExterior]
    nao_apurados: list[str]


def apurar(sessao: Session, investidor_id: int, hoje: date | None = None) -> ApuracaoIR:
    p = param.carregar(sessao)
    regras = carregar_regras(sessao)
    fatos, ignorados = fatos_por_mes(carregar_operacoes(sessao, investidor_id), p.ir_bdr_como_acao)
    prejuizos = carregar_prejuizos(sessao, investidor_id)
    proventos_ext = _proventos_exterior(sessao, investidor_id)
    fim = mes(hoje or date.today())

    meses_bolsa = [comp for comp, cat in fatos if cat != "EXTERIOR"]
    if p.ir_ano_inicio:
        inicio = date(p.ir_ano_inicio, 1, 1)
    else:
        inicio = date(min(meses_bolsa).year, 1, 1) if meses_bolsa else fim
    meses = apurar_mensal(
        fatos, regras, inicio, max(fim, *meses_bolsa) if meses_bolsa else fim, prejuizos,
        carregar_pagos(sessao, investidor_id), p.ir_daytrade_no_limite,
    )

    anos_ext = {comp.year for comp, cat in fatos if cat == "EXTERIOR"} | set(proventos_ext)
    if p.ir_ano_inicio:
        anos_ext = {a for a in anos_ext if a >= p.ir_ano_inicio}
    anos_ext = set(range(min(anos_ext), fim.year + 1)) if anos_ext else set()
    exterior = apurar_exterior(fatos, regras, anos_ext, proventos_ext, prejuizos.get("EXTERIOR", ZERO))
    return ApuracaoIR(meses, exterior, sorted(ignorados))
