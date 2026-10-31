"""APIs públicas: CoinGecko principal; Kraken apenas para preços com identidade conhecida."""

import json
import logging
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache

import httpx
from pydantic import AwareDatetime, BaseModel, Field, TypeAdapter, ValidationError

log = logging.getLogger(__name__)
_CG = "https://api.coingecko.com/api/v3"
_KRAKEN = "https://api.kraken.com/0/public"
# Não inferir a identidade pelo ticker: símbolos podem representar tokens distintos.
_PARES = {
    "bitcoin": "XBTUSD", "ethereum": "ETHUSD", "solana": "SOLUSD",
    "ripple": "XRPUSD", "cardano": "ADAUSD", "dogecoin": "XDGUSD",
    "litecoin": "LTCUSD", "polkadot": "DOTUSD", "chainlink": "LINKUSD",
}


class ErroCripto(Exception):
    pass


class MoedaCatalogo(BaseModel):
    id: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9-]*$")
    symbol: str = Field(min_length=1)
    name: str = Field(min_length=1)


class Mercado(BaseModel):
    id: str
    symbol: str
    name: str
    current_price: Decimal = Field(gt=0, lt=Decimal("1e12"), allow_inf_nan=False)
    market_cap: Decimal | None = Field(default=None, ge=0, lt=Decimal("1e22"), allow_inf_nan=False)
    price_change_percentage_24h_in_currency: Decimal | None = Field(default=None, allow_inf_nan=False)
    price_change_percentage_7d_in_currency: Decimal | None = Field(default=None, allow_inf_nan=False)
    price_change_percentage_30d_in_currency: Decimal | None = Field(default=None, allow_inf_nan=False)
    last_updated: AwareDatetime
    fonte: str = "CoinGecko"


def _get(url: str, params: dict[str, str]) -> object:
    for tentativa in range(3):
        try:
            resposta = httpx.get(url, params=params, timeout=15)
            resposta.raise_for_status()
            return json.loads(resposta.text, parse_float=Decimal)
        except httpx.HTTPStatusError as erro:
            if tentativa < 2 and (erro.response.status_code == 429 or erro.response.status_code >= 500):
                time.sleep(2 ** tentativa)
                continue
            log.exception("Falha na API cripto %s", url)
            raise ErroCripto(f"Fonte cripto indisponível (HTTP {erro.response.status_code})") from erro
        except httpx.TransportError as erro:
            if tentativa < 2:
                time.sleep(2 ** tentativa)
                continue
            log.exception("Falha de conexão na API cripto %s", url)
            raise ErroCripto("Não foi possível conectar à fonte cripto") from erro
        except ValueError as erro:
            log.exception("Resposta inválida na API cripto %s", url)
            raise ErroCripto("Resposta inválida da fonte cripto") from erro
    raise AssertionError("Tentativas de consulta esgotadas")


@lru_cache(maxsize=64)
def _buscar(termo: str, janela: int) -> tuple[MoedaCatalogo, ...]:
    dados = _get(f"{_CG}/search", {"query": termo})
    try:
        if not isinstance(dados, dict):
            raise ValueError("Catálogo inválido")
        return tuple(TypeAdapter(list[MoedaCatalogo]).validate_python(dados["coins"])[:25])
    except (KeyError, ValueError, ValidationError) as erro:
        log.exception("Catálogo CoinGecko inválido")
        raise ErroCripto("Catálogo CoinGecko inválido") from erro


def buscar(termo: str) -> tuple[MoedaCatalogo, ...]:
    return _buscar(termo.strip().lower(), int(time.time() // 300))


def mercados(ids: Sequence[str]) -> tuple[dict[str, Mercado], list[str]]:
    encontrados: dict[str, Mercado] = {}
    avisos: list[str] = []
    ids = sorted(set(ids))
    for inicio in range(0, len(ids), 250):
        lote = ids[inicio:inicio + 250]
        try:
            dados = _get(f"{_CG}/coins/markets", {
                "vs_currency": "usd", "ids": ",".join(lote), "per_page": "250",
                "price_change_percentage": "24h,7d,30d", "precision": "full",
            })
            if not isinstance(dados, list):
                raise ValueError("Mercado inválido")
            for linha in dados:
                try:
                    mercado = Mercado.model_validate(linha)
                except ValidationError:
                    log.exception("Snapshot CoinGecko inválido")
                    avisos.append("CoinGecko devolveu um snapshot inválido; tentando fallback de preço")
                    continue
                if mercado.id in lote:
                    encontrados[mercado.id] = mercado
        except (ErroCripto, ValueError) as erro:
            log.warning("Mercado CoinGecko indisponível: %s", erro)
            avisos.append(str(erro))
    for id_ in ids:
        if id_ in encontrados:
            continue
        par = _PARES.get(id_)
        if par is None:
            avisos.append(f"{id_}: sem preço CoinGecko e sem vínculo Kraken verificado")
            continue
        try:
            dados = _get(f"{_KRAKEN}/Ticker", {"pair": par})
            if not isinstance(dados, dict) or dados["error"]:
                raise ValueError("Ticker Kraken inválido")
            resultado = dados["result"]
            if not isinstance(resultado, dict) or len(resultado) != 1:
                raise ValueError("Par Kraken indisponível")
            linha = next(iter(resultado.values()))
            encontrados[id_] = Mercado(
                id=id_, symbol=par.removesuffix("USD"), name=id_,
                current_price=Decimal(linha["c"][0]), last_updated=datetime.now(UTC), fonte="Kraken",
            )
            avisos.append(f"{id_}: fallback Kraken; market cap e variações indisponíveis")
        except (ErroCripto, KeyError, ValueError, TypeError, ValidationError) as erro:
            log.warning("Preço Kraken %s indisponível: %s", id_, erro)
            avisos.append(f"{id_}: preço Kraken indisponível")
    return encontrados, avisos


@lru_cache(maxsize=64)
def _historico(id_: str, dias: int, janela: int) -> tuple[tuple[datetime, Decimal], ...]:
    dados = _get(f"{_CG}/coins/{id_}/market_chart", {"vs_currency": "usd", "days": str(dias), "precision": "full"})
    try:
        if not isinstance(dados, dict):
            raise ValueError("Histórico inválido")
        pontos = TypeAdapter(list[tuple[int, Decimal]]).validate_python(dados["prices"])
        if not pontos or any(not preco.is_finite() or preco <= 0 for _, preco in pontos):
            raise ValueError("Histórico vazio ou inválido")
        return tuple((datetime.fromtimestamp(ts / 1000, UTC), preco) for ts, preco in sorted(pontos))
    except (KeyError, ValueError, ValidationError, OverflowError) as erro:
        log.exception("Histórico CoinGecko inválido")
        raise ErroCripto("Histórico CoinGecko indisponível ou inválido") from erro


def historico(id_: str, dias: int) -> tuple[tuple[datetime, Decimal], ...]:
    return _historico(id_, dias, int(time.time() // 900))
