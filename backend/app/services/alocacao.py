"""Alocação ideal x atual e simulador de aporte/rebalanceamento.

Peso-alvo de um ativo no portfólio = peso da estratégia x peso do book x peso do ativo no book.
Dentro do book, ativos com peso definido na carteira usam esse peso; o restante do book é dividido
igualmente entre os demais ativos com posição. Um ativo distribuído entre books (exceção) participa de
cada um com a fração configurada.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Ativo, Estrategia, MetaMetodologia
from . import caixa as servico_caixa
from . import configuracao
from . import parametros as servico_parametros
from .carteira import LinhaCarteira, cambios_atuais, montar_carteira, ultimas_cotacoes
from .filtros_ativos import classificar_mercado

ZERO = Decimal(0)
UM = Decimal(1)
CENTAVO = Decimal("0.01")
MODOS = ("comprar", "rebalancear")


@dataclass
class Candidato:
    ativo_id: int
    ticker: str
    nome: str | None
    classe: str
    moeda: str
    valor_atual: Decimal
    books: list[tuple[int, Decimal]]  # (book_id, fração do ativo)
    cotacao: Decimal | None = None
    preco_brl: Decimal | None = None  # cotação x câmbio
    carteira: str | None = None
    peso_no_book: Decimal | None = None
    preco_teto: Decimal | None = None


@dataclass
class BookAlvo:
    id: int
    nome: str
    estrategia: str
    peso_alvo: Decimal  # fração do portfólio


@dataclass
class ItemAlocacao:
    candidato: Candidato
    book: str
    peso_alvo: Decimal = ZERO
    peso_atual: Decimal = ZERO
    valor_alvo: Decimal = ZERO
    ajuste: Decimal = ZERO
    quantidade: Decimal | None = None
    acima_teto: bool = False


@dataclass
class GrupoAlocacao:
    nome: str
    estrategia: str | None
    peso_alvo: Decimal
    peso_atual: Decimal
    valor_atual: Decimal
    valor_alvo: Decimal
    ajuste: Decimal


@dataclass
class CategoriaMetodologia:
    nome: str
    valor_atual: Decimal
    peso_atual: Decimal


@dataclass
class MetodologiaAlocacao:
    nome: str
    categorias: list[CategoriaMetodologia]
    total_atual: Decimal
    peso_total: Decimal


@dataclass
class ResultadoAlocacao:
    total_atual: Decimal
    aporte: Decimal
    sobra: Decimal
    estrategias: list[GrupoAlocacao]
    books: list[GrupoAlocacao]
    ativos: list[ItemAlocacao]
    sem_book: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    metodologias: list[MetodologiaAlocacao] = field(default_factory=list)


_CATEGORIAS_ARCA = ("Ações BR", "FIIs", "Caixa", "Exterior")
_CATEGORIAS_KRAKEN = ("Caixa", "FIIs", "Ações BR", "Cripto", "Exterior", "Negócios")
CATEGORIAS_METODOLOGIAS = {"ARCA": _CATEGORIAS_ARCA, "KRAKEN": _CATEGORIAS_KRAKEN}
_NAO_CLASSIFICADO = "Não classificado"


def metas_do_investidor(sessao: Session, investidor_id: int) -> dict[tuple[str, str], Decimal]:
    metas = sessao.scalars(select(MetaMetodologia).where(MetaMetodologia.investidor_id == investidor_id))
    return {(meta.metodologia, meta.categoria): meta.peso_alvo for meta in metas}


def _categoria_metodologia(ativo: Ativo, metodologia: str) -> str:
    classe = ativo.classe.strip().upper()
    mercado = classificar_mercado(ativo)
    cripto = classe == "CRIPTO" or ativo.coingecko_id is not None

    if cripto:
        return "Cripto" if metodologia == "KRAKEN" else "Exterior"
    if classe == "ETF" and ativo.ticker == "GPUS11":
        return "Exterior"
    if classe in {"CAIXA", "R.FIXA"}:
        return "Caixa"
    if classe == "FII":
        return "FIIs"
    if classe in {"BDR", "REIT", "ETF_US"}:
        return "Exterior"
    if classe in {"AÇÃO", "STOCK"}:
        if mercado == "BRASIL":
            return "Ações BR"
        if mercado == "EUA":
            return "Exterior"

    if metodologia == "KRAKEN" and classe in {"NEGÓCIO", "NEGÓCIOS", "NEGOCIO", "NEGOCIOS"}:
        return "Negócios"
    if metodologia == "ARCA":
        return _NAO_CLASSIFICADO

    return _NAO_CLASSIFICADO


def calcular_metodologias(posicoes: Sequence[tuple[Ativo, Decimal]], caixa_brl: Decimal = ZERO) -> list[MetodologiaAlocacao]:
    configuracoes = (
        ("ARCA", _CATEGORIAS_ARCA),
        ("KRAKEN", _CATEGORIAS_KRAKEN),
    )
    resultados = []
    for nome, categorias in configuracoes:
        valores = {categoria: ZERO for categoria in (*categorias, _NAO_CLASSIFICADO)}
        valores["Caixa"] += caixa_brl
        for ativo, valor in posicoes:
            valores[_categoria_metodologia(ativo, nome)] += valor

        total = sum(valores.values(), ZERO)
        linhas = [
            CategoriaMetodologia(
                categoria,
                valor,
                valor / total if total else ZERO,
            )
            for categoria, valor in valores.items()
            if categoria != _NAO_CLASSIFICADO or valor != ZERO
        ]
        resultados.append(MetodologiaAlocacao(nome, linhas, total, Decimal(1) if total else ZERO))
    return resultados


def _quantidade(valor: Decimal, c: Candidato) -> Decimal | None:
    if not c.preco_brl:
        return None
    casas = Decimal(1) if c.moeda == "BRL" else Decimal("0.0001")
    return (valor / c.preco_brl).quantize(casas, rounding=ROUND_DOWN)


def _pesos_no_book(membros: list[Candidato]) -> dict[int, Decimal]:
    explicitos = {c.ativo_id: c.peso_no_book for c in membros if c.peso_no_book is not None}
    soma = sum(explicitos.values(), ZERO)
    escala = UM / soma if soma > UM else UM
    pesos = {a: p * escala for a, p in explicitos.items()}
    livres = [c for c in membros if c.ativo_id not in explicitos and c.valor_atual > 0]
    if livres:
        resto = max(ZERO, UM - soma * escala) / len(livres)
        pesos.update({c.ativo_id: resto for c in livres})
    return pesos


def calcular_alocacao(
    candidatos: Sequence[Candidato],
    books: Sequence[BookAlvo],
    aporte: Decimal = ZERO,
    modo: str = "comprar",
    respeitar_teto: bool = True,
) -> ResultadoAlocacao:
    if modo not in MODOS:
        raise ValueError(f"Modo deve ser um de {MODOS}")
    por_book = {b.id: b for b in books}
    alocaveis = [c for c in candidatos if any(b in por_book for b, _ in c.books)]
    sem_book = sorted({c.classe for c in candidatos if c not in alocaveis and c.valor_atual > 0})

    total_atual = sum((c.valor_atual for c in alocaveis), ZERO)
    base = total_atual + aporte

    peso_alvo: dict[int, Decimal] = {}
    vazios = []
    for b in books:
        membros = [c for c in alocaveis if any(bid == b.id for bid, _ in c.books)]
        pesos = _pesos_no_book(membros)
        if b.peso_alvo > 0 and not pesos:
            vazios.append(b.nome)
        for ativo_id, peso in pesos.items():
            peso_alvo[ativo_id] = peso_alvo.get(ativo_id, ZERO) + b.peso_alvo * peso

    itens = []
    for c in alocaveis:
        principal = max((bp for bp in c.books if bp[0] in por_book), key=lambda bp: bp[1])[0]
        item = ItemAlocacao(c, por_book[principal].nome, peso_alvo.get(c.ativo_id, ZERO))
        item.peso_atual = c.valor_atual / total_atual if total_atual else ZERO
        item.valor_alvo = base * item.peso_alvo
        item.acima_teto = bool(c.preco_teto and c.cotacao is not None and c.cotacao > c.preco_teto)
        itens.append(item)

    def pode_comprar(i: ItemAlocacao) -> bool:
        return i.candidato.preco_brl is not None and not (respeitar_teto and i.acima_teto)

    sobra = aporte
    if modo == "comprar":
        deficits = {id(i): max(ZERO, i.valor_alvo - i.candidato.valor_atual) if pode_comprar(i) else ZERO for i in itens}
        soma = sum(deficits.values(), ZERO)
        fator = min(UM, aporte / soma) if soma else ZERO
        for i in itens:
            i.ajuste = (deficits[id(i)] * fator).quantize(CENTAVO, rounding=ROUND_DOWN)
        sobra = aporte - sum((i.ajuste for i in itens), ZERO)
    else:
        for i in itens:
            diferenca = i.valor_alvo - i.candidato.valor_atual
            i.ajuste = (diferenca if diferenca < 0 or pode_comprar(i) else ZERO).quantize(CENTAVO)
        sobra = ZERO
    for i in itens:
        i.quantidade = _quantidade(i.ajuste, i.candidato) if i.ajuste else ZERO

    grupos_book = []
    for b in books:
        valor = sum(
            (c.valor_atual * pct for c in alocaveis for bid, pct in c.books if bid == b.id), ZERO
        )
        alvo = base * b.peso_alvo
        grupos_book.append(
            GrupoAlocacao(
                b.nome, b.estrategia, b.peso_alvo, valor / total_atual if total_atual else ZERO, valor, alvo, alvo - valor
            )
        )
    grupos_estr: dict[str, GrupoAlocacao] = {}
    for g in grupos_book:
        e = grupos_estr.setdefault(g.estrategia, GrupoAlocacao(g.estrategia, None, ZERO, ZERO, ZERO, ZERO, ZERO))
        for campo in ("peso_alvo", "peso_atual", "valor_atual", "valor_alvo", "ajuste"):
            setattr(e, campo, getattr(e, campo) + getattr(g, campo))

    avisos = []
    soma_alvo = sum((b.peso_alvo for b in books), ZERO)
    if abs(soma_alvo - UM) > Decimal("0.0001"):
        avisos.append(f"Pesos-alvo somam {soma_alvo:.2%} do portfólio (deveriam somar 100%).")
    if vazios:
        avisos.append(f"Books com peso-alvo e sem ativos: {', '.join(vazios)} (o valor fica sem destino no simulador).")
    if sem_book:
        avisos.append(f"Classes sem book (fora da alocação): {', '.join(sem_book)}.")

    itens.sort(key=lambda i: (-i.ajuste, i.candidato.ticker))
    return ResultadoAlocacao(total_atual, aporte, sobra, list(grupos_estr.values()), grupos_book, itens, sem_book, avisos)


def books_alvo(sessao: Session, classificacao: configuracao.Classificacao) -> list[BookAlvo]:
    ordem = {e.id: e.ordem for e in sessao.scalars(select(Estrategia))}
    lista = sorted(classificacao.books.values(), key=lambda b: (ordem.get(b.estrategia_id, 0), b.ordem, b.nome))
    return [BookAlvo(b.id, b.nome, b.estrategia.nome, b.estrategia.peso * b.peso) for b in lista]


def metodologias_da_carteira(
    sessao: Session,
    investidor_ids: Sequence[int] | None,
    linhas: Sequence[LinhaCarteira],
    classes_excluidas: Sequence[str] = (),
) -> list[MetodologiaAlocacao]:
    caixa_brl = ZERO
    if not classes_excluidas and servico_parametros.carregar(sessao).caixa_no_portfolio:
        caixa_brl = servico_caixa.calcular(sessao, investidor_ids).total_brl
    valores_posicoes = [
        (linha.ativo, linha.valor_mercado if linha.valor_mercado is not None else linha.posicao.custo)
        for linha in linhas
        if linha.ativo.classe not in classes_excluidas
    ]
    return calcular_metodologias(valores_posicoes, caixa_brl)


def calcular(
    sessao: Session,
    investidor_ids: Sequence[int] | None,
    aporte: Decimal = ZERO,
    modo: str = "comprar",
    respeitar_teto: bool = True,
) -> ResultadoAlocacao:
    classificacao = configuracao.carregar(sessao)
    cambios = cambios_atuais(sessao)

    def candidato(ativo: Ativo, valor: Decimal, cotacao: Decimal | None) -> Candidato:
        vinculo = classificacao.carteira(ativo.id)
        cambio = cambios.get(ativo.moeda)
        return Candidato(
            ativo.id, ativo.ticker, ativo.nome, ativo.classe, ativo.moeda, valor,
            [(b.id, pct) for b, pct in classificacao.books_do_ativo(ativo)],
            cotacao, cotacao * cambio if cotacao is not None and cambio is not None else None,
            vinculo.carteira.nome if vinculo else None,
            vinculo.peso if vinculo else None,
            vinculo.preco_teto if vinculo and vinculo.entra_preco_teto else None,
        )

    linhas = montar_carteira(sessao, investidor_ids, consolidado=True)
    candidatos = {
        l.ativo.id: candidato(l.ativo, l.valor_mercado if l.valor_mercado is not None else l.posicao.custo,
                              l.cotacao.preco if l.cotacao else None)
        for l in linhas
    }
    # Ativos de carteira com peso-alvo ainda sem posição entram como candidatos à compra.
    novos = {a for a, v in classificacao.carteiras.items() if v.peso and a not in candidatos}
    if novos:
        cotacoes = ultimas_cotacoes(sessao, novos)
        for ativo in sessao.scalars(select(Ativo).where(Ativo.id.in_(novos))):
            cot = cotacoes.get(ativo.id)
            candidatos[ativo.id] = candidato(ativo, ZERO, cot.preco if cot else None)

    resultado = calcular_alocacao(list(candidatos.values()), books_alvo(sessao, classificacao), aporte, modo, respeitar_teto)
    resultado.metodologias = metodologias_da_carteira(sessao, investidor_ids, linhas)
    return resultado
