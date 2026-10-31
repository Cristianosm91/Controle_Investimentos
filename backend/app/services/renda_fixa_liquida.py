"""Renda fixa (ativos personalizados): valor líquido de IR regressivo e IOF, por aplicação, e projeção no vencimento.

Cada compra é uma aplicação com prazo próprio; resgates consomem as aplicações mais antigas (PEPS), como fazem
bancos e corretoras. O IOF incide sobre o rendimento nos primeiros 29 dias e o IR sobre o rendimento menos o IOF.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Ativo, Operacao
from . import renda_fixa
from .carteira import cambios_atuais, carregar_posicoes
from .posicao import ZERO

# Tabela regressiva do IOF (Decreto 6.306/2007, anexo): % do rendimento pelo número de dias corridos (1 a 29).
_IOF = (96, 93, 90, 86, 83, 80, 76, 73, 70, 66, 63, 60, 56, 53, 50, 46, 43, 40, 36, 33, 30, 26, 23, 20, 16, 13, 10, 6, 3)

_ENTRADAS = ("C", "BONIFICACAO")


def aliquota_ir(dias: int) -> Decimal:
    """IR regressivo da renda fixa (Lei 11.033/2004, art. 1º)."""
    if dias <= 180:
        return Decimal("0.225")
    if dias <= 360:
        return Decimal("0.20")
    if dias <= 720:
        return Decimal("0.175")
    return Decimal("0.15")


def aliquota_iof(dias: int) -> Decimal:
    if dias >= 30:
        return ZERO
    return Decimal(_IOF[max(dias, 1) - 1]) / 100


@dataclass
class Aplicacao:
    data: date
    quantidade: Decimal
    custo: Decimal  # BRL


@dataclass
class Impostos:
    bruto: Decimal
    iof: Decimal
    ir: Decimal

    @property
    def liquido(self) -> Decimal:
        return self.bruto - self.iof - self.ir


def aplicacoes_abertas(movimentos: Sequence[tuple[date, str, Decimal, Decimal, Decimal, Decimal]]) -> list[Aplicacao]:
    """`movimentos`: (data, evento, quantidade, preço, taxas, câmbio) em ordem cronológica."""
    abertas: list[Aplicacao] = []
    for dia, evento, qtd, preco, taxas, cambio in movimentos:
        if evento in _ENTRADAS or (evento == "TRANSFERENCIA" and qtd > 0):
            abertas.append(Aplicacao(dia, qtd, (qtd * preco + taxas) * cambio))
        elif evento in ("V", "TRANSFERENCIA") and qtd < 0:
            resto = -qtd
            while resto > 0 and abertas:
                primeira = abertas[0]
                usado = min(resto, primeira.quantidade)
                primeira.custo -= primeira.custo * usado / primeira.quantidade
                primeira.quantidade -= usado
                resto -= usado
                if primeira.quantidade <= Decimal("1e-9"):
                    abertas.pop(0)
    return abertas


def calcular_impostos(aplicacoes: Sequence[Aplicacao], valor_cota_brl: Decimal, dia: date, isento: bool) -> Impostos:
    bruto = iof = ir = ZERO
    for a in aplicacoes:
        valor = a.quantidade * valor_cota_brl
        rendimento = valor - a.custo
        dias = (dia - a.data).days
        iof_a = rendimento * aliquota_iof(dias) if rendimento > 0 else ZERO
        ir_a = (rendimento - iof_a) * aliquota_ir(dias) if rendimento > 0 and not isento else ZERO
        bruto, iof, ir = bruto + valor, iof + iof_a, ir + ir_a
    return Impostos(bruto, iof, ir)


def _ajustar(aplicacoes: list[Aplicacao], quantidade: Decimal, custo: Decimal) -> list[Aplicacao]:
    """Eventos raros (desdobramento, amortização) mudam a posição sem gerar aplicação: reparte o total oficial."""
    q = sum((a.quantidade for a in aplicacoes), ZERO)
    c = sum((a.custo for a in aplicacoes), ZERO)
    if not aplicacoes or q <= 0:
        return aplicacoes
    return [
        Aplicacao(a.data, a.quantidade * quantidade / q, a.custo * custo / c if c else custo * a.quantidade / q)
        for a in aplicacoes
    ]


@dataclass
class ItemRendaFixa:
    investidor_id: int
    ativo: Ativo
    descricao: str
    quantidade: Decimal
    custo: Decimal
    atual: Impostos
    vencimento: Impostos | None
    hoje: date

    @property
    def dias_para_vencer(self) -> int | None:
        return (self.ativo.data_vencimento - self.hoje).days if self.ativo.data_vencimento else None

    @property
    def aliquota_ir(self) -> Decimal | None:
        base = self.atual.bruto - self.custo - self.atual.iof
        return self.atual.ir / base if base > 0 and self.atual.ir else None


def descrever(ativo: Ativo) -> str:
    if not ativo.indexador:
        return "Saldo manual"
    taxa = f"{float(ativo.taxa_aa or 0) * 100:.2f}".replace(".", ",") + "% a.a." if ativo.taxa_aa else ""
    if ativo.indexador == "PRE":
        return f"Prefixado {taxa}".strip()
    pct = ativo.indexador_pct if ativo.indexador_pct is not None else Decimal(1)
    texto = ativo.indexador if pct == 1 else f"{float(pct) * 100:.0f}% do {ativo.indexador}"
    return f"{texto} + {taxa}" if taxa else texto


def listar(sessao: Session, investidor_ids: Sequence[int] | None, hoje: date | None = None) -> list[ItemRendaFixa]:
    hoje = hoje or date.today()
    ativos = {a.id: a for a in sessao.scalars(select(Ativo).where(~Ativo.cotacao_automatica, Ativo.classe != "CRIPTO"))}
    if not ativos:
        return []
    posicoes = {k: p for k, p in carregar_posicoes(sessao, investidor_ids, ativo_ids=set(ativos)).items() if p.aberta}
    if not posicoes:
        return []

    consulta = (
        select(Operacao.investidor_id, Operacao.ativo_id, Operacao.data, Operacao.evento, Operacao.quantidade,
               Operacao.preco, Operacao.taxas, Operacao.cambio)
        .where(Operacao.ativo_id.in_({a for _, a in posicoes}), ~Operacao.daytrade)
        .order_by(Operacao.data, Operacao.id)
    )
    if investidor_ids:
        consulta = consulta.where(Operacao.investidor_id.in_(investidor_ids))
    movimentos: dict[tuple[int, int], list] = defaultdict(list)
    for inv, ativo_id, *resto in sessao.execute(consulta):
        movimentos[(inv, ativo_id)].append(tuple(resto))

    cambios = cambios_atuais(sessao)
    cotas: dict[int, tuple[Decimal, Decimal | None]] = {}
    itens = []
    for (inv, ativo_id), posicao in sorted(posicoes.items(), key=lambda kv: (ativos[kv[0][1]].ticker, kv[0][0])):
        ativo = ativos[ativo_id]
        cambio = cambios.get(ativo.moeda)
        if cambio is None:
            continue
        if ativo_id not in cotas:
            venc = None
            if renda_fixa.calculado(ativo) and ativo.data_vencimento and ativo.data_vencimento > hoje:
                venc = renda_fixa.valor_cota(sessao, ativo, ativo.data_vencimento)
            cotas[ativo_id] = (renda_fixa.valor_cota(sessao, ativo, hoje), venc)
        cota_hoje, cota_venc = cotas[ativo_id]
        aplicacoes = _ajustar(aplicacoes_abertas(movimentos[(inv, ativo_id)]), posicao.quantidade, posicao.custo)
        if not aplicacoes:
            aplicacoes = [Aplicacao(posicao.data_inicio or hoje, posicao.quantidade, posicao.custo)]
        atual = calcular_impostos(aplicacoes, cota_hoje * cambio, hoje, ativo.isento_ir)
        vencimento = (
            calcular_impostos(aplicacoes, cota_venc * cambio, ativo.data_vencimento, ativo.isento_ir)
            if cota_venc is not None else None
        )
        itens.append(
            ItemRendaFixa(inv, ativo, descrever(ativo), posicao.quantidade, posicao.custo, atual, vencimento, hoje)
        )
    return itens
