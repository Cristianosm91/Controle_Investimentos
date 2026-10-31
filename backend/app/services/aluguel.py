"""Aluguel de ações (BTC) como doador: remuneração, taxa de intermediação e IRRF viram um provento ALUGUEL.

O extrato da corretora traz três lançamentos por liquidação: o crédito da remuneração (só a raiz do ticker, ex.:
MGLU), a taxa de intermediação (ticker completo, ex.: MGLU3) e o IRRF. São agrupados por data e raiz.
"""

import csv
import hashlib
import io
import re
import unicodedata
import zipfile
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from itertools import islice

from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Ativo, Investidor, Provento
from ..seguranca import LINHAS_MAXIMAS, tamanho_descompactado_excedido
from . import lotes

EVENTO = "ALUGUEL"
ORIGEM = "corretora"
TAMANHO_MAXIMO = 5 * 1024 * 1024
_TOLERANCIA = Decimal("0.02")

PREFIXOS = (
    ("CREDITO REF. TAXA DE REMUNERACAO BTC", "valor"),
    ("DEBITO CBLC IRRF S/ RENDIMENTO DE BTC", "irrf"),
    ("TAXA DE INTERMEDIACAO DOADOR", "taxas"),
)


class ExtratoInvalido(Exception):
    pass


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().upper().strip()


def classificar(historico: str) -> tuple[str, str | None] | None:
    """(campo, ticker citado no histórico) ou None se a linha não for do BTC."""
    h = re.sub(r"\s+", " ", _sem_acento(historico))
    for prefixo, campo in PREFIXOS:
        if h.startswith(prefixo):
            resto = h[len(prefixo):].split()
            ticker = resto[0] if resto and re.fullmatch(r"[A-Z]{4}\d{0,2}", resto[0]) else None
            return campo, ticker
    return None


@dataclass
class GrupoBTC:
    data: date
    raiz: str
    ticker: str | None = None
    valor: Decimal = Decimal(0)
    irrf: Decimal = Decimal(0)
    taxas: Decimal = Decimal(0)
    linhas: list[int] = field(default_factory=list)


def agrupar(linhas: Iterable[tuple[int, date, str, str | None, Decimal]]) -> list[GrupoBTC]:
    """Linhas (número, data, histórico, ticker opcional, valor) → grupos por data e raiz; ignora o que não é BTC."""
    grupos: dict[tuple[date, str], GrupoBTC] = {}
    for numero, dia, historico, ticker, valor in linhas:
        classe = classificar(historico)
        if classe is None:
            continue
        campo, citado = classe
        ticker = (ticker or citado or "").strip().upper()
        if len(ticker) < 4:
            continue
        grupo = grupos.setdefault((dia, ticker[:4]), GrupoBTC(dia, ticker[:4]))
        setattr(grupo, campo, getattr(grupo, campo) + abs(valor))
        grupo.linhas.append(numero)
        if len(ticker) > 4:
            grupo.ticker = ticker
    return [grupos[chave] for chave in sorted(grupos)]


def ativo_por_raiz(ativos: Iterable[Ativo], raiz: str, ticker: str | None) -> tuple[Ativo | None, list[str]]:
    """Ativo do grupo e os candidatos considerados (o extrato da remuneração traz só a raiz)."""
    por_ticker = {a.ticker: a for a in ativos}
    if ticker and ticker in por_ticker:
        return por_ticker[ticker], [ticker]
    candidatos = sorted(
        (a for t, a in por_ticker.items() if t.startswith(raiz) and t[len(raiz):].isdigit() and a.moeda == "BRL"),
        key=lambda a: (_sem_acento(a.classe) != "ACAO", a.ticker),
    )
    return (candidatos[0] if candidatos else None), [a.ticker for a in candidatos]


# ---------- Resumo (página P12) ----------

def resumo(sessao: Session, investidores: list[int] | None, ano: int | None) -> dict:
    filtros = [Provento.evento == EVENTO]
    if investidores:
        filtros.append(Provento.investidor_id.in_(investidores))
    anos = sorted({d.year for d in sessao.scalars(select(Provento.data_pagamento).where(*filtros))}, reverse=True)
    base = select(Provento, Ativo.ticker).join(Ativo, Ativo.id == Provento.ativo_id).where(*filtros)
    if ano:
        base = base.where(Provento.data_pagamento.between(date(ano, 1, 1), date(ano, 12, 31)))

    zero = Decimal(0)
    totais = {"bruto": zero, "taxas": zero, "irrf": zero, "liquido": zero, "lancamentos": 0}
    por_ativo: dict[str, dict] = {}
    por_mes: dict[str, dict] = defaultdict(lambda: {"bruto": zero, "taxas": zero, "irrf": zero, "liquido": zero})
    for provento, ticker in sessao.execute(base):
        cambio = provento.cambio or Decimal(1)
        bruto, taxas, irrf = provento.valor * cambio, provento.taxas * cambio, provento.irrf * cambio
        liquido = bruto - taxas - irrf
        item = por_ativo.setdefault(ticker, {
            "ticker": ticker, "bruto": zero, "taxas": zero, "irrf": zero, "liquido": zero, "lancamentos": 0,
            "ultimo": provento.data_pagamento,
        })
        mes = por_mes[provento.data_pagamento.strftime("%Y-%m")]
        for alvo in (totais, item, mes):
            alvo["bruto"] += bruto
            alvo["taxas"] += taxas
            alvo["irrf"] += irrf
            alvo["liquido"] += liquido
        totais["lancamentos"] += 1
        item["lancamentos"] += 1
        item["ultimo"] = max(item["ultimo"], provento.data_pagamento)
    return {
        "anos": anos,
        "totais": {k: v for k, v in totais.items() if k != "lancamentos"},
        "lancamentos": totais["lancamentos"],
        "por_ativo": sorted(por_ativo.values(), key=lambda i: i["liquido"], reverse=True),
        "por_mes": [{"mes": m, **v} for m, v in sorted(por_mes.items())],
    }


# ---------- Importação do extrato da corretora ----------

def _decimal(valor) -> Decimal | None:
    if valor is None:
        return None
    if isinstance(valor, int | float | Decimal):
        return Decimal(str(valor))
    texto = str(valor).replace("R$", "").replace("\u00a0", "").replace(" ", "").strip()
    if texto in ("", "-"):
        return None
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation:
        return None


def _data(valor) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(str(valor or "").strip()[:10], formato).date()
        except ValueError:
            continue
    return None


def _ler_tabela(conteudo: bytes) -> list[tuple]:
    if len(conteudo) > TAMANHO_MAXIMO:
        raise ExtratoInvalido("Arquivo maior que 5 MB")
    if zipfile.is_zipfile(io.BytesIO(conteudo)):
        try:
            excedido = tamanho_descompactado_excedido(conteudo)
        except zipfile.BadZipFile as erro:
            raise ExtratoInvalido("Planilha .xlsx corrompida") from erro
        if excedido:
            raise ExtratoInvalido("Planilha grande demais quando descompactada")
        try:
            livro = load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
        except Exception as erro:
            raise ExtratoInvalido(f"Não foi possível abrir a planilha: {erro}") from erro
        try:
            planilha = livro.worksheets[0]
            planilha.reset_dimensions()  # arquivos com dimensão "A1" seriam lidos só até a primeira linha
            linhas = [tuple(linha) for linha in islice(planilha.iter_rows(values_only=True), LINHAS_MAXIMAS + 1)]
        finally:
            livro.close()
        if len(linhas) > LINHAS_MAXIMAS:
            raise ExtratoInvalido(f"Planilha com mais de {LINHAS_MAXIMAS} linhas: divida o período do extrato")
        return linhas
    for codificacao in ("utf-8-sig", "cp1252"):
        try:
            texto = conteudo.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ExtratoInvalido("Arquivo de texto com codificação desconhecida")
    try:
        dialeto = csv.Sniffer().sniff(texto[:4096], delimiters=";,\t")
    except csv.Error:
        dialeto = _PontoEVirgula
    return [tuple(linha) for linha in csv.reader(io.StringIO(texto), dialeto)]


class _PontoEVirgula(csv.excel):
    delimiter = ";"


def _achar(nomes: list[str], *opcoes: str) -> int | None:
    return next((i for o in opcoes for i, n in enumerate(nomes) if n.startswith(o)), None)


def _colunas(linhas: list[tuple]) -> tuple[int, dict[str, int]]:
    """Localiza o cabeçalho: data (liquidação/movimentação/data), histórico (lançamento/histórico/descrição) e valor."""
    for indice, linha in enumerate(linhas[:30]):
        nomes = [_sem_acento(str(c or "")) for c in linha]
        mapa = {
            "data": _achar(nomes, "LIQUIDACAO", "DATA", "MOVIMENTACAO"),
            "historico": _achar(nomes, "LANCAMENTO", "HISTORICO", "DESCRICAO"),
            "valor": _achar(nomes, "VALOR"),
            "ticker": _achar(nomes, "TICKER", "ATIVO", "CODIGO"),
        }
        if None not in (mapa["data"], mapa["historico"], mapa["valor"]):
            return indice, {k: v for k, v in mapa.items() if v is not None}
    raise ExtratoInvalido(
        "Cabeçalho não encontrado: o extrato precisa das colunas de data (Liquidação/Data), Lançamento/Histórico e Valor."
    )


def _celula(linha: tuple, col: dict[str, int], campo: str):
    return linha[col[campo]] if campo in col and col[campo] < len(linha) else None


def ler_extrato(conteudo: bytes) -> list[GrupoBTC]:
    linhas = _ler_tabela(conteudo)
    cabecalho, col = _colunas(linhas)
    brutas = []
    for numero, linha in enumerate(linhas[cabecalho + 1:], start=cabecalho + 2):
        dia, historico = _data(_celula(linha, col, "data")), _celula(linha, col, "historico")
        valor = _decimal(_celula(linha, col, "valor"))
        if dia and historico and valor is not None:
            ticker = str(_celula(linha, col, "ticker") or "").strip() or None
            brutas.append((numero, dia, str(historico), ticker, valor))
    grupos = agrupar(brutas)
    if not grupos:
        raise ExtratoInvalido("Nenhum lançamento de aluguel (BTC) encontrado no extrato.")
    return grupos


@dataclass
class ItemPrevia:
    data: date
    ticker: str | None
    raiz: str
    valor: Decimal
    taxas: Decimal
    irrf: Decimal
    linhas: list[int]
    status: str  # novo | duplicado | verificar | sem_ativo
    motivo: str | None = None
    hash: str = ""


def _hash(investidor_id: int, g: GrupoBTC) -> str:
    base = f"{ORIGEM}|{EVENTO}|{investidor_id}|{g.data}|{g.raiz}|{g.valor.normalize()}|{g.irrf.normalize()}|{g.taxas.normalize()}"
    return hashlib.sha256(base.encode()).hexdigest()


def analisar(sessao: Session, investidor_id: int, conteudo: bytes) -> list[ItemPrevia]:
    grupos = ler_extrato(conteudo)
    ativos = list(sessao.scalars(select(Ativo)))
    hashes = set(sessao.scalars(select(Provento.hash_origem).where(Provento.origem == ORIGEM)))
    existentes: dict[tuple[date, str], list[Provento]] = defaultdict(list)
    for provento, ticker in sessao.execute(
        select(Provento, Ativo.ticker).join(Ativo, Ativo.id == Provento.ativo_id).where(
            Provento.investidor_id == investidor_id, Provento.evento == EVENTO,
            Provento.data_pagamento.between(min(g.data for g in grupos), max(g.data for g in grupos)),
        )
    ):
        existentes[(provento.data_pagamento, ticker[:4])].append(provento)

    itens = []
    for g in grupos:
        ativo, candidatos = ativo_por_raiz(ativos, g.raiz, g.ticker)
        item = ItemPrevia(g.data, ativo.ticker if ativo else g.ticker, g.raiz, g.valor, g.taxas, g.irrf, g.linhas,
                          "novo", hash=_hash(investidor_id, g))
        if len(candidatos) > 1:
            item.motivo = f"Vários tickers com a raiz {g.raiz} ({', '.join(candidatos)}): usado {ativo.ticker}"
        mesmos = existentes.get((g.data, g.raiz), [])
        if item.hash in hashes:
            item.status, item.motivo = "duplicado", "Já importado anteriormente"
        elif mesmos:
            soma = sum((p.valor for p in mesmos), Decimal(0))
            if abs(soma - g.valor) <= _TOLERANCIA:
                item.status, item.motivo = "duplicado", "Já existe aluguel deste ativo nesta data"
            else:
                item.status, item.motivo = "verificar", "Já existe aluguel deste ativo nesta data com outro valor"
        elif ativo is None:
            item.status, item.motivo = "sem_ativo", f"Nenhum ativo cadastrado com a raiz {g.raiz}"
        elif g.valor <= 0:
            item.status, item.motivo = "verificar", "Sem crédito de remuneração (só taxa/IRRF) nesta data"
        itens.append(item)
    return itens


def importar(
    sessao: Session, investidor_id: int, conteudo: bytes, incluir: set[str], arquivo: str | None = None
) -> tuple[int, int | None]:
    """Grava os itens "novo" e os "verificar" cujo hash está em `incluir`; devolve (quantidade gravada, lote)."""
    if sessao.get(Investidor, investidor_id) is None:
        raise ExtratoInvalido("Investidor não encontrado")
    ativos = {a.ticker: a for a in sessao.scalars(select(Ativo))}
    gravados = 0
    lote = None
    for item in analisar(sessao, investidor_id, conteudo):
        if item.status != "novo" and not (item.status == "verificar" and item.hash in incluir):
            continue
        if lote is None:
            lote = lotes.novo(sessao, "ALUGUEL", investidor_id, arquivo)
        sessao.add(Provento(
            investidor_id=investidor_id, ativo=ativos[item.ticker], data_pagamento=item.data, evento=EVENTO,
            valor=item.valor, irrf=item.irrf, taxas=item.taxas, moeda="BRL", cambio=Decimal(1),
            observacao="Importado do extrato da corretora (BTC)", origem=ORIGEM, hash_origem=item.hash,
            lote_id=lote.id,
        ))
        gravados += 1
    if lote is not None:
        lotes.contar(sessao, lote)
    sessao.commit()
    return gravados, lote.id if lote else None
