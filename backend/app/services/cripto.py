"""Posições e monitor informativo de cripto; não calcula imposto nem altera P10."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Ativo, Cotacao, CotacaoMoeda, CriptoMercado, Investidor, Operacao
from ..providers import cripto as provedor
from ..providers.bcb import ProvedorBcb
from .carteira import cambios_atuais, montar_carteira
from .ir_calculo import mes
from .posicao import ZERO, Carteira, Movimento

LIMITE_INFORMATIVO = Decimal("35000")


@dataclass
class AtualizacaoCripto:
    atualizados: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    def resumo(self) -> str:
        return f"{len(self.atualizados)} cripto(s) atualizada(s)" + (
            "; " + "; ".join(self.avisos) if self.avisos else ""
        )


def atualizar(sessao: Session) -> AtualizacaoCripto:
    ativos = list(sessao.scalars(select(Ativo).where(Ativo.classe == "CRIPTO", Ativo.cotacao_automatica)))
    resultado = AtualizacaoCripto()
    if not ativos:
        return resultado
    ids = [a.coingecko_id for a in ativos if a.coingecko_id]
    mercados, resultado.avisos = provedor.mercados(ids)
    moedas = sorted({"USD"} | {a.moeda for a in ativos if a.moeda != "BRL"})
    for moeda, cot in ProvedorBcb().cambios(moedas).items():
        linha = sessao.scalar(select(CotacaoMoeda).where(CotacaoMoeda.moeda == moeda, CotacaoMoeda.data == cot.data))
        if linha is None:
            linha = CotacaoMoeda(moeda=moeda, data=cot.data)
            sessao.add(linha)
        linha.valor, linha.fonte = cot.preco, cot.fonte
    sessao.flush()
    cambios = cambios_atuais(sessao)
    for ativo in ativos:
        mercado = mercados.get(ativo.coingecko_id)
        if mercado is None:
            resultado.avisos.append(f"{ativo.ticker}: sem snapshot novo; dados antigos não são apresentados como atuais")
            continue
        if mercado.current_price.quantize(Decimal("0.00000001")) <= 0:
            resultado.avisos.append(f"{ativo.ticker}: preço abaixo da precisão de 8 casas do banco; snapshot não gravado")
            continue
        instante = mercado.last_updated.astimezone(UTC).replace(tzinfo=None)
        linha = sessao.get(CriptoMercado, ativo.id)
        if linha and linha.atualizado_em > instante:
            resultado.avisos.append(f"{ativo.ticker}: snapshot recebido é anterior ao cache local")
            continue
        if linha is None:
            linha = CriptoMercado(ativo_id=ativo.id)
            sessao.add(linha)
        linha.preco_usd, linha.market_cap_usd = mercado.current_price, mercado.market_cap
        linha.variacao_24h = _fracao(mercado.price_change_percentage_24h_in_currency)
        linha.variacao_7d = _fracao(mercado.price_change_percentage_7d_in_currency)
        linha.variacao_30d = _fracao(mercado.price_change_percentage_30d_in_currency)
        linha.fonte, linha.atualizado_em = mercado.fonte, instante
        resultado.atualizados.append(ativo.ticker)
        if ativo.moeda == "USD":
            preco = linha.preco_usd
        elif "USD" in cambios and ativo.moeda in cambios:
            preco = linha.preco_usd * cambios["USD"] / cambios[ativo.moeda]
        else:
            resultado.avisos.append(f"{ativo.ticker}: câmbio indisponível; cotação da carteira não atualizada")
            continue
        dia = mercado.last_updated.astimezone(UTC).date()
        cotacao = sessao.scalar(select(Cotacao).where(Cotacao.ativo_id == ativo.id, Cotacao.data == dia))
        if cotacao is None:
            cotacao = Cotacao(ativo_id=ativo.id, data=dia)
            sessao.add(cotacao)
        cotacao.preco, cotacao.fonte = preco, mercado.fonte
        # Variação em USD não representa a variação em BRL/EUR após conversão cambial.
        cotacao.variacao_pct = linha.variacao_24h if ativo.moeda == "USD" else None
    sessao.commit()
    return resultado


def _fracao(valor: Decimal | None) -> Decimal | None:
    return valor / 100 if valor is not None else None


def painel(sessao: Session, investidores: Sequence[int] | None) -> dict:
    ativos = list(sessao.scalars(select(Ativo).where(Ativo.classe == "CRIPTO").order_by(Ativo.ticker)))
    ids = {a.id for a in ativos}
    linhas = montar_carteira(sessao, investidores, consolidado=True, ativo_ids=ids)
    por_ativo = {l.ativo.id: l for l in linhas}
    snapshots = {s.ativo_id: s for s in sessao.scalars(select(CriptoMercado).where(CriptoMercado.ativo_id.in_(ids)))}
    cambio = sessao.scalar(
        select(CotacaoMoeda).where(CotacaoMoeda.moeda == "USD").order_by(CotacaoMoeda.data.desc()).limit(1)
    )
    itens = []
    avisos = []
    for ativo in ativos:
        snapshot = snapshots.get(ativo.id)
        linha = por_ativo.get(ativo.id)
        if ativo.coingecko_id is None:
            avisos.append(f"{ativo.ticker}: vincule o ID CoinGecko para obter cotações sem ambiguidade")
        if snapshot is None:
            avisos.append(f"{ativo.ticker}: sem snapshot de mercado; use Atualizar cripto")
        elif datetime.now(UTC).replace(tzinfo=None) - snapshot.atualizado_em > timedelta(hours=2):
            avisos.append(f"{ativo.ticker}: snapshot com mais de 2 horas; consulte a data da fonte")
        itens.append({
            "ativo_id": ativo.id, "ticker": ativo.ticker, "nome": ativo.nome, "coingecko_id": ativo.coingecko_id,
            "preco_usd": snapshot.preco_usd if snapshot else None,
            "preco_brl": snapshot.preco_usd * cambio.valor if snapshot and cambio else None,
            "market_cap_usd": snapshot.market_cap_usd if snapshot else None,
            "variacao_24h": snapshot.variacao_24h if snapshot else None,
            "variacao_7d": snapshot.variacao_7d if snapshot else None,
            "variacao_30d": snapshot.variacao_30d if snapshot else None,
            "fonte": snapshot.fonte if snapshot else None,
            "atualizado_em": snapshot.atualizado_em.replace(tzinfo=UTC) if snapshot else None,
            "quantidade": linha.posicao.quantidade if linha else ZERO,
            "preco_medio_brl": linha.posicao.preco_medio if linha else ZERO,
            "investido_brl": linha.posicao.custo if linha else ZERO,
            "mercado_brl": linha.valor_mercado if linha else ZERO,
            "lucro_aberto_brl": linha.lucro_aberto if linha else ZERO,
        })
    return {
        "itens": itens, "cambio_usd_brl": cambio.valor if cambio else None,
        "cambio_data": cambio.data if cambio else None, "avisos": avisos,
    }


def monitor(sessao: Session, investidores: Sequence[int] | None, ano: int) -> dict:
    consulta = (
        select(Operacao, Ativo.ticker).join(Ativo, Ativo.id == Operacao.ativo_id)
        .where(Ativo.classe == "CRIPTO", Operacao.data < date(ano + 1, 1, 1))
        .order_by(Operacao.data, Operacao.id)
    )
    if investidores:
        consulta = consulta.where(Operacao.investidor_id.in_(investidores))
    carteira = Carteira()
    dados: dict[tuple[int, date], dict] = {}
    incompletos: set[tuple[int, int]] = set()
    avisos = []
    for op, ticker in sessao.execute(consulta):
        movimento = Movimento(
            op.investidor_id, op.ativo_id, op.data, op.evento, op.quantidade, op.preco,
            op.taxas, False, op.id, op.cambio,
        )
        if op.evento == "V":
            posicao = carteira.posicoes.get((op.investidor_id, op.ativo_id))
            if posicao is None or posicao.quantidade < -op.quantidade:
                incompletos.add((op.investidor_id, op.ativo_id))
                avisos.append(f"{ticker} em {op.data:%d/%m/%Y}: venda sem posição suficiente; revise os lançamentos")
        lucro = carteira.aplicar(movimento)
        if op.data.year != ano or op.evento != "V":
            continue
        chave = (op.investidor_id, mes(op.data))
        linha = dados.setdefault(chave, {
            "investidor_id": op.investidor_id, "competencia": chave[1], "vendas_brl": ZERO,
            "ganhos_brl": ZERO, "perdas_brl": ZERO, "limite_brl": LIMITE_INFORMATIVO, "completo": True,
        })
        linha["vendas_brl"] += -op.quantidade * op.preco * op.cambio
        linha["ganhos_brl"] += max(lucro, ZERO)
        linha["perdas_brl"] += max(-lucro, ZERO)
        linha["completo"] = linha["completo"] and (op.investidor_id, op.ativo_id) not in incompletos
    nomes = {i.id: i.nome for i in sessao.scalars(select(Investidor))}
    meses = []
    for chave, linha in sorted(dados.items()):
        completo = linha.pop("completo")
        linha["investidor"] = nomes[chave[0]]
        linha["acima_limite"] = linha["vendas_brl"] > LIMITE_INFORMATIVO
        linha["saldo_limite_brl"] = max(LIMITE_INFORMATIVO - linha["vendas_brl"], ZERO)
        linha["resultado_brl"] = linha["ganhos_brl"] - linha["perdas_brl"] if completo else None
        if not completo:
            linha["ganhos_brl"] = linha["perdas_brl"] = None
        meses.append(linha)
    return {"meses": meses, "avisos": avisos}
