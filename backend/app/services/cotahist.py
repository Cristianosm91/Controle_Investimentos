"""Fechamento oficial da B3 a partir dos arquivos COTAHIST (layout posicional, preços com 2 casas).

Arquivos: anual `COTAHIST_A{aaaa}.ZIP` (atualizado diariamente no ano corrente) e diário
`COTAHIST_D{ddmmaaaa}.ZIP`. O fechamento da B3 prevalece sobre cotações de outras fontes do mesmo dia.
"""

import io
import logging
import tempfile
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from ..models import Ativo, Cotacao, Operacao

log = logging.getLogger(__name__)

FONTE = "B3 COTAHIST"
_URL = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/{nome}.ZIP"
_MERCADO_VISTA = "010"


@dataclass(frozen=True)
class Fechamento:
    ticker: str
    data: date
    preco: Decimal
    volume: Decimal


def interpretar_linha(linha: str) -> Fechamento | None:
    """Registro tipo 01 do mercado à vista; demais linhas (header, trailer, opções...) -> None."""
    if len(linha) < 217 or linha[0:2] != "01" or linha[24:27] != _MERCADO_VISTA:
        return None
    fator = int(linha[210:217]) or 1
    return Fechamento(
        ticker=linha[12:24].strip(),
        data=datetime.strptime(linha[2:10], "%Y%m%d").date(),
        preco=Decimal(int(linha[108:121])) / 100 / fator,
        volume=Decimal(int(linha[170:188])) / 100,
    )


def codigos_b3(ticker: str) -> set[str]:
    """Códigos de negociação aceitos para o ticker; FIIs `XXXX11` negociavam como `XXXX11B` até 2017."""
    codigos = {ticker}
    if len(ticker) == 6 and ticker.endswith("11") and ticker[:4].isalpha():
        codigos.add(f"{ticker}B")
    return codigos


def ler_arquivo(caminho_zip: Path, tickers: set[str]) -> dict[tuple[str, date], Fechamento]:
    """Fechamentos dos tickers pedidos (aceitando códigos antigos); no mesmo dia vale o código atual
    e, depois, o registro de maior volume."""
    por_codigo = {c: t for t in tickers for c in codigos_b3(t)}
    resultado: dict[tuple[str, date], Fechamento] = {}
    with zipfile.ZipFile(caminho_zip) as arquivo:
        for nome in arquivo.namelist():
            with arquivo.open(nome) as bruto:
                for linha in io.TextIOWrapper(bruto, encoding="latin-1"):
                    ticker = por_codigo.get(linha[12:24].strip())
                    if ticker is None:
                        continue
                    f = interpretar_linha(linha)
                    if f is None:
                        continue
                    codigo_atual = f.ticker == ticker
                    f = Fechamento(ticker, f.data, f.preco, f.volume if codigo_atual else -f.volume)
                    atual = resultado.get((ticker, f.data))
                    if atual is None or f.volume > atual.volume:
                        resultado[(ticker, f.data)] = f
    return resultado


def baixar(nome: str, destino: Path) -> bool:
    """Baixa o ZIP; False se a B3 ainda não publicou (404 ou resposta que não é ZIP)."""
    url = _URL.format(nome=nome)
    with httpx.stream("GET", url, timeout=120, follow_redirects=True) as resposta:
        if resposta.status_code == 404:
            return False
        resposta.raise_for_status()
        with destino.open("wb") as saida:
            for bloco in resposta.iter_bytes(1 << 16):
                saida.write(bloco)
    return zipfile.is_zipfile(destino)


@dataclass
class ResultadoCarga:
    arquivos: list[str] = field(default_factory=list)
    indisponiveis: list[str] = field(default_factory=list)
    cotacoes: int = 0


def _ativos_b3(sessao: Session) -> dict[str, int]:
    """Ativos da B3 que já tiveram operação (inclui posições encerradas, úteis para histórico)."""
    consulta = (
        select(Ativo.ticker, Ativo.id)
        .where(Ativo.mercado == "BVMF", Ativo.id.in_(select(Operacao.ativo_id).distinct()))
    )
    return {t: i for t, i in sessao.execute(consulta)}


def _preco_anterior(sessao: Session, ativo_id: int, antes_de: date) -> Decimal | None:
    return sessao.scalar(
        select(Cotacao.preco)
        .where(Cotacao.ativo_id == ativo_id, Cotacao.data < antes_de)
        .order_by(Cotacao.data.desc())
        .limit(1)
    )


def gravar(
    sessao: Session,
    fechamentos: Iterable[Fechamento],
    ids: dict[str, int],
    fonte: str = FONTE,
    preservar_fonte: str | None = None,
) -> int:
    """Upsert em `cotacao`, calculando a variação contra o fechamento anterior do mesmo ativo.

    Linhas já gravadas com `preservar_fonte` não são sobrescritas.
    """
    por_ativo: dict[int, list[Fechamento]] = {}
    for f in fechamentos:
        por_ativo.setdefault(ids[f.ticker], []).append(f)

    linhas = []
    for ativo_id, lista in por_ativo.items():
        lista.sort(key=lambda f: f.data)
        anterior = _preco_anterior(sessao, ativo_id, lista[0].data)
        for f in lista:
            variacao = f.preco / anterior - 1 if anterior else None
            linhas.append({
                "ativo_id": ativo_id, "data": f.data, "preco": f.preco, "variacao_pct": variacao, "fonte": fonte,
            })
            anterior = f.preco

    for i in range(0, len(linhas), 500):
        lote = insert(Cotacao).values(linhas[i : i + 500])
        sessao.execute(
            lote.on_conflict_do_update(
                index_elements=["ativo_id", "data"],
                set_={
                    "preco": lote.excluded.preco,
                    "variacao_pct": lote.excluded.variacao_pct,
                    "fonte": lote.excluded.fonte,
                    "atualizado_em": func.now(),
                },
                where=(Cotacao.fonte != preservar_fonte) if preservar_fonte else None,
            )
        )
        sessao.commit()  # lotes curtos: não bloqueia gravações da API durante cargas longas
    return len(linhas)


def _carregar(sessao: Session, nomes: Iterable[str]) -> ResultadoCarga:
    resultado = ResultadoCarga()
    ids = _ativos_b3(sessao)
    if not ids:
        return resultado
    with tempfile.TemporaryDirectory(prefix="cotahist_") as pasta:
        for nome in nomes:
            destino = Path(pasta) / f"{nome}.zip"
            if not baixar(nome, destino):
                resultado.indisponiveis.append(nome)
                continue
            fechamentos = ler_arquivo(destino, set(ids))
            resultado.cotacoes += gravar(sessao, fechamentos.values(), ids)
            resultado.arquivos.append(nome)
            log.info("%s: %d cotações gravadas", nome, len(fechamentos))
            destino.unlink()
    return resultado


def _dias_uteis(inicio: date, fim: date) -> Iterator[date]:
    dia = inicio
    while dia <= fim:
        if dia.weekday() < 5:
            yield dia
        dia += timedelta(days=1)


def carregar_historico(sessao: Session, desde_ano: int | None = None, ate_ano: int | None = None) -> ResultadoCarga:
    """Carga anual, por padrão desde o ano da primeira operação até o ano corrente."""
    if desde_ano is None:
        primeira = sessao.scalar(select(func.min(Operacao.data)))
        desde_ano = primeira.year if primeira else date.today().year
    ate_ano = ate_ano or date.today().year
    return _carregar(sessao, (f"COTAHIST_A{ano}" for ano in range(desde_ano, ate_ano + 1)))


def ultima_data_b3(sessao: Session) -> date | None:
    return sessao.scalar(select(func.max(Cotacao.data)).where(Cotacao.fonte == FONTE))


def carregar_pendentes(sessao: Session, hoje: date | None = None, max_dias: int = 10) -> ResultadoCarga:
    """Arquivos diários desde o último fechamento B3 gravado (no máximo `max_dias` úteis)."""
    hoje = hoje or date.today()
    ultima = ultima_data_b3(sessao)
    inicio = ultima + timedelta(days=1) if ultima else hoje - timedelta(days=14)
    dias = list(_dias_uteis(inicio, hoje))[-max_dias:]
    return _carregar(sessao, (f"COTAHIST_D{d:%d%m%Y}" for d in dias))
