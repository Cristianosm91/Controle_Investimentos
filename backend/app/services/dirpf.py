"""Relatório de apoio à DIRPF: bens e direitos, rendimentos isentos, tributação exclusiva e renda variável.

Códigos de ficha só onde confirmados pela RFB (Perguntas e Respostas IRPF); demais itens trazem a descrição
para o usuário escolher o grupo/código no programa da Receita.
"""

import csv
import io
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dominio import EVENTOS_PROVENTO, GRUPOS_PREJUIZO
from ..models import Ativo, Provento
from .carteira import carregar_posicoes
from .ir import ZERO, AnoExterior, MesIR, apurar, categoria_ir

TIPO_BEM = {
    "ACAO": "Ações",
    "BDR": "BDR",
    "ETF": "Fundo de índice (ETF)",
    "OPCAO": "Opções",
    "FII": "Cotas de FII / Fiagro",
    "EXTERIOR": "Ativo no exterior",
}

ISENTO_DIVIDENDOS = "09 – Lucros e dividendos recebidos"
ISENTO_FII = "Rendimentos de FII / Fiagro"
ISENTO_ACOES_20K = "Ganhos líquidos em ações com vendas até R$ 20 mil no mês"
EXCLUSIVO_JCP = "Juros sobre capital próprio (valor líquido)"
EXCLUSIVO_BTC = "Aluguel de ações — BTC (remuneração líquida do IRRF)"
OUTROS = "Outros proventos (classificar manualmente)"


@dataclass
class BemDireito:
    ativo_id: int
    ticker: str
    nome: str | None
    cnpj: str | None
    tipo: str
    quantidade: Decimal
    custo_anterior: Decimal
    custo_atual: Decimal
    discriminacao: str


@dataclass
class Rendimento:
    ficha: str  # ISENTO | EXCLUSIVO | OUTROS
    tipo: str
    ativo_id: int | None
    ticker: str | None
    cnpj: str | None
    valor: Decimal
    irrf: Decimal = ZERO


@dataclass
class RelatorioDirpf:
    ano: int
    bens: list[BemDireito]
    rendimentos: list[Rendimento]
    meses: list[MesIR]
    prejuizo_final: dict[str, Decimal]
    irrf_saldo_final: Decimal
    exterior: AnoExterior | None
    avisos: list[str] = field(default_factory=list)


def _qtd(valor: Decimal) -> str:
    return f"{valor.normalize():f}".replace(".", ",")


def _brl(valor: Decimal) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _formatar_cnpj(cnpj: str | None) -> str:
    if not cnpj:
        return ""
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def _bens(sessao: Session, investidor_id: int, ano: int) -> list[BemDireito]:
    anterior = carregar_posicoes(sessao, [investidor_id], date(ano - 1, 12, 31))
    atual = carregar_posicoes(sessao, [investidor_id], date(ano, 12, 31))
    ids = {a for (_, a), p in anterior.items() if p.aberta} | {a for (_, a), p in atual.items() if p.aberta}
    ativos = {a.id: a for a in sessao.scalars(select(Ativo).where(Ativo.id.in_(ids)))} if ids else {}
    bens = []
    for ativo_id in ids:
        a = ativos[ativo_id]
        p_ant, p_atu = anterior.get((investidor_id, ativo_id)), atual.get((investidor_id, ativo_id))
        custo_ant = p_ant.custo if p_ant and p_ant.aberta else ZERO
        if p_atu and p_atu.aberta:
            qtd, custo = p_atu.quantidade, p_atu.custo
            texto = f"{_qtd(qtd)} {a.ticker}" + (f" - {a.nome.rstrip('.')}" if a.nome else "")
            if a.cnpj:
                texto += f" - CNPJ {_formatar_cnpj(a.cnpj)}"
            texto += f". Custo médio R$ {_brl(p_atu.preco_medio)}."
        else:
            qtd, custo = ZERO, ZERO
            texto = f"{a.ticker}: posição encerrada em {ano}."
        categoria = categoria_ir(a.classe, a.moeda, False)
        bens.append(BemDireito(
            a.id, a.ticker, a.nome, a.cnpj, TIPO_BEM.get(categoria or "", f"Outros ({a.classe})"), qtd, custo_ant, custo, texto,
        ))
    bens.sort(key=lambda b: (b.tipo, b.ticker))
    return bens


def _rendimentos(sessao: Session, investidor_id: int, ano: int, meses: list[MesIR]) -> list[Rendimento]:
    consulta = (
        select(Provento, Ativo)
        .join(Ativo, Ativo.id == Provento.ativo_id)
        .where(
            Provento.investidor_id == investidor_id,
            Provento.data_pagamento >= date(ano, 1, 1),
            Provento.data_pagamento <= date(ano, 12, 31),
        )
    )
    total: dict[tuple[str, str, int], list[Decimal]] = defaultdict(lambda: [ZERO, ZERO])
    ativos: dict[int, Ativo] = {}
    for p, a in sessao.execute(consulta):
        categoria = categoria_ir(a.classe, a.moeda, False)
        if categoria == "EXTERIOR" or p.evento == "AMORTIZACAO":
            continue  # exterior vai na apuração anual; amortização devolve capital (reduz custo)
        if p.evento in ("JSCP", "ALUGUEL"):
            chave = ("EXCLUSIVO", EXCLUSIVO_JCP if p.evento == "JSCP" else EXCLUSIVO_BTC)
            valor = (p.valor - p.irrf) * p.cambio
        elif categoria == "FII" and p.evento in ("RENDIMENTO", "DIVIDENDO"):
            chave, valor = ("ISENTO", ISENTO_FII), p.valor * p.cambio
        elif p.evento in ("DIVIDENDO", "RENDIMENTO"):
            chave, valor = ("ISENTO", ISENTO_DIVIDENDOS), p.valor * p.cambio
        else:
            chave = ("OUTROS", f"{OUTROS}: {EVENTOS_PROVENTO.get(p.evento, p.evento)}")
            valor = p.valor * p.cambio
        ativos[a.id] = a
        soma = total[(*chave, a.id)]
        soma[0] += valor
        soma[1] += p.irrf * p.cambio

    rendimentos = [
        Rendimento(ficha, tipo, a, ativos[a].ticker, ativos[a].cnpj, v, irrf)
        for (ficha, tipo, a), (v, irrf) in total.items()
    ]
    isento_acoes = sum(
        (c.lucro for m in meses for c in m.categorias if c.categoria == "ACAO" and c.isento and c.lucro > 0), ZERO
    )
    if isento_acoes:
        rendimentos.append(Rendimento("ISENTO", ISENTO_ACOES_20K, None, None, None, isento_acoes))
    ordem = {"ISENTO": 0, "EXCLUSIVO": 1, "OUTROS": 2}
    rendimentos.sort(key=lambda r: (ordem[r.ficha], r.tipo, r.ticker or ""))
    return rendimentos


def gerar(sessao: Session, investidor_id: int, ano: int) -> RelatorioDirpf:
    apuracao = apurar(sessao, investidor_id)
    meses = [m for m in apuracao.meses if m.competencia.year == ano]
    ultimo = meses[-1] if meses else None
    relatorio = RelatorioDirpf(
        ano=ano,
        bens=_bens(sessao, investidor_id, ano),
        rendimentos=_rendimentos(sessao, investidor_id, ano, meses),
        meses=meses,
        prejuizo_final=dict(ultimo.prejuizo) if ultimo else {},
        irrf_saldo_final=ultimo.irrf_saldo if ultimo else ZERO,
        exterior=next((e for e in apuracao.exterior if e.ano == ano), None),
    )
    sem_cnpj = sorted({b.ticker for b in relatorio.bens if not b.cnpj and b.quantidade and b.tipo != TIPO_BEM["EXTERIOR"]})
    if sem_cnpj:
        relatorio.avisos.append(f"Ativos sem CNPJ cadastrado: {', '.join(sem_cnpj)}")
    if apuracao.nao_apurados:
        relatorio.avisos.append(f"Vendas fora da apuração de renda variável: {', '.join(apuracao.nao_apurados)}")
    return relatorio


def para_csv(r: RelatorioDirpf) -> str:
    """CSV com `;` e vírgula decimal (abre direto no Excel em pt-BR)."""
    saida = io.StringIO()
    w = csv.writer(saida, delimiter=";", lineterminator="\n")
    w.writerow([f"DIRPF {r.ano + 1} - ano-calendário {r.ano} (estimativa; confira no programa da Receita)"])
    w.writerow([])
    w.writerow(["BENS E DIREITOS"])
    w.writerow([
        "Tipo", "Ticker", "CNPJ", "Quantidade", f"Situação em 31/12/{r.ano - 1}", f"Situação em 31/12/{r.ano}", "Discriminação",
    ])
    for b in r.bens:
        w.writerow([
            b.tipo, b.ticker, _formatar_cnpj(b.cnpj), _qtd(b.quantidade), _brl(b.custo_anterior), _brl(b.custo_atual),
            b.discriminacao,
        ])
    w.writerow([])
    w.writerow(["RENDIMENTOS"])
    w.writerow(["Ficha", "Tipo", "Ticker", "CNPJ da fonte", "Valor", "IR retido"])
    fichas = {"ISENTO": "Isentos e não tributáveis", "EXCLUSIVO": "Tributação exclusiva", "OUTROS": "A classificar"}
    for rend in r.rendimentos:
        w.writerow([
            fichas[rend.ficha], rend.tipo, rend.ticker or "", _formatar_cnpj(rend.cnpj), _brl(rend.valor), _brl(rend.irrf),
        ])
    w.writerow([])
    w.writerow(["RENDA VARIÁVEL (DARF 6015)"])
    w.writerow(["Mês", "Lucro operações comuns", "Lucro day trade", "Lucro FII", "Imposto", "IRRF", "DARF", "Pago"])
    for m in r.meses:
        lucro = defaultdict(lambda: ZERO)
        for c in m.categorias:
            if not c.isento:
                lucro[{"DAYTRADE": "DT", "FII": "FII"}.get(c.categoria, "COMUM")] += c.lucro
        w.writerow([f"{m.competencia:%m/%Y}", _brl(lucro["COMUM"]), _brl(lucro["DT"]), _brl(lucro["FII"]),
                    _brl(m.imposto), _brl(m.irrf), _brl(m.darf), _brl(m.pago)])
    w.writerow([])
    w.writerow([f"Prejuízo a compensar em 31/12/{r.ano}"])
    for grupo, valor in r.prejuizo_final.items():
        w.writerow([GRUPOS_PREJUIZO.get(grupo, grupo), _brl(valor)])
    w.writerow(["IRRF não compensado no ano", _brl(r.irrf_saldo_final)])
    if r.exterior:
        e = r.exterior
        w.writerow([])
        w.writerow(["EXTERIOR"])
        w.writerow(["Vendas", "Lucro", "Dividendos", "Imposto pago no exterior", "Imposto estimado", "Prejuízo a compensar"])
        w.writerow([
            _brl(e.vendas), _brl(e.lucro), _brl(e.dividendos), _brl(e.imposto_pago_exterior), _brl(e.imposto), _brl(e.prejuizo),
        ])
    for aviso in r.avisos:
        w.writerow([f"Aviso: {aviso}"])
    return saida.getvalue()
