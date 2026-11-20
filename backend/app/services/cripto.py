"""Posições e monitor informativo de cripto; não calcula imposto nem altera P10."""

from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..dominio import MOEDAS_CRIPTO
from ..models import Ativo, Cotacao, CotacaoMoeda, CriptoMercado, Investidor, Operacao
from ..providers import bcb
from ..providers import cripto as provedor
from ..providers.base import CotacaoAtual
from ..providers.bcb import ProvedorBcb
from . import auditoria
from .carteira import cambios_atuais, montar_carteira
from .cotacoes import gravar_cambio
from .ir_calculo import mes
from .posicao import ZERO, Carteira, Movimento, calcular_posicoes, consolidar

LIMITE_INFORMATIVO = Decimal("35000")


@dataclass
class AtualizacaoCripto:
    atualizados: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    # Avisos que não indicam falha de fonte (não marcam a tarefa como "concluída com falhas").
    informativos: list[str] = field(default_factory=list)

    @property
    def falhas(self) -> list[str]:
        return [aviso for aviso in self.avisos if aviso not in self.informativos]

    def informar(self, texto: str) -> None:
        self.avisos.append(texto)
        self.informativos.append(texto)

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
    moedas = sorted(set(MOEDAS_CRIPTO) - {"BRL"} | {a.moeda for a in ativos if a.moeda != "BRL"})
    fonte_cambio = ProvedorBcb()
    for moeda, cot in fonte_cambio.cambios(moedas).items():
        gravar_cambio(sessao, moeda, cot)
    resultado.avisos.extend(f"{falha}: câmbio indisponível" for falha in fonte_cambio.falhas)
    sessao.flush()
    cambios = cambios_atuais(sessao)
    for ativo in ativos:
        mercado = mercados.get(ativo.coingecko_id)
        if mercado is None:
            resultado.avisos.append(f"{ativo.ticker}: sem snapshot novo; dados antigos não são apresentados como atuais")
            continue
        if mercado.current_price.quantize(Decimal("0.00000001")) <= 0:
            resultado.informar(f"{ativo.ticker}: preço abaixo da precisão de 8 casas do banco; snapshot não gravado")
            continue
        instante = mercado.last_updated.astimezone(UTC).replace(tzinfo=None)
        linha = sessao.get(CriptoMercado, ativo.id)
        if linha and linha.atualizado_em > instante:
            resultado.informar(f"{ativo.ticker}: snapshot recebido é anterior ao cache local")
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


def ptax_historica(dia: date, moedas: Sequence[str] = MOEDAS_CRIPTO) -> tuple[dict[str, bcb.Ptax], list[str]]:
    """Obtém PTAX de venda e data efetiva sem ampliar o domínio global de moedas."""
    resultado: dict[str, bcb.Ptax] = {"BRL": bcb.Ptax("BRL", dia, Decimal(1), Decimal(1))}
    avisos = []
    for moeda in sorted(set(moedas) - {"BRL"}):
        try:
            resultado[moeda] = bcb.ptax(moeda, dia, settings.ptax_dias_uteis_antes)
        except bcb.ErroPtax:
            avisos.append(f"{moeda}: PTAX indisponível para {dia:%d/%m/%Y}")
    return resultado, avisos


def cambios_operacao(
    sessao: Session,
    dia: date,
    moeda: str,
    moeda_taxas: str,
    cambio_usd_manual: Decimal | None = None,
    taxas_cambio_usd_manual: Decimal | None = None,
) -> dict:
    """Resolve taxa da operação e taxas históricas necessárias para todas as moedas de visualização."""
    cotacoes, avisos = ptax_historica(dia)
    cambio_usd_brl = cotacoes.get("USD")
    if cambio_usd_brl is None:
        raise bcb.ErroPtax(f"PTAX USD indisponível para {dia:%d/%m/%Y}")
    if moeda != "USD" and moeda not in cotacoes and cambio_usd_manual is None:
        raise bcb.ErroPtax(f"PTAX {moeda} indisponível; informe manualmente a taxa para USD")
    if moeda_taxas != "USD" and moeda_taxas not in cotacoes and taxas_cambio_usd_manual is None:
        raise bcb.ErroPtax(f"PTAX {moeda_taxas} indisponível; informe manualmente a taxa das taxas para USD")

    usd_brl = cambio_usd_brl.venda
    moeda_brl = cotacoes[moeda].venda if moeda in cotacoes else None
    automatico = (
        Decimal(1) if moeda == "USD"
        else Decimal(1) / usd_brl if moeda == "BRL"
        else moeda_brl / usd_brl if moeda_brl is not None
        else None
    )
    cambio_usd = cambio_usd_manual if cambio_usd_manual is not None else automatico
    if cambio_usd is None or not cambio_usd.is_finite() or cambio_usd <= 0:
        raise bcb.ErroPtax(f"Taxa da moeda {moeda} para USD inválida ou indisponível")
    if not usd_brl.is_finite() or usd_brl <= 0:
        raise bcb.ErroPtax(f"PTAX USD inválida para {dia:%d/%m/%Y}")

    moeda_taxas_brl = cotacoes[moeda_taxas].venda if moeda_taxas in cotacoes else None
    taxas_automatico = (
        Decimal(1) if moeda_taxas == "USD"
        else Decimal(1) / usd_brl if moeda_taxas == "BRL"
        else moeda_taxas_brl / usd_brl if moeda_taxas_brl is not None
        else None
    )
    taxas_cambio_usd = taxas_cambio_usd_manual if taxas_cambio_usd_manual is not None else taxas_automatico
    if taxas_cambio_usd is None or not taxas_cambio_usd.is_finite() or taxas_cambio_usd <= 0:
        raise bcb.ErroPtax(f"Taxa da moeda {moeda_taxas} para USD inválida ou indisponível")

    for moeda_cotada, ptax in cotacoes.items():
        if moeda_cotada != "BRL":
            gravar_cambio(
                sessao, moeda_cotada,
                CotacaoAtual(moeda_cotada, ptax.venda, None, ptax.data, bcb.FONTE),
            )
    sessao.flush()
    return {
        "cambio_brl": cambio_usd * usd_brl,
        "cambio_usd": cambio_usd,
        "data_moeda": cotacoes.get(moeda).data if moeda in cotacoes else dia,
        "data_usd": cambio_usd_brl.data,
        "fonte": "Manual" if cambio_usd_manual is not None else bcb.FONTE,
        "taxas_cambio_brl": taxas_cambio_usd * usd_brl,
        "taxas_cambio_usd": taxas_cambio_usd,
        "taxas_data_moeda": cotacoes.get(moeda_taxas).data if moeda_taxas in cotacoes else dia,
        "taxas_data_usd": cambio_usd_brl.data,
        "taxas_fonte": "Manual" if taxas_cambio_usd_manual is not None else bcb.FONTE,
        "cotacoes": cotacoes,
        "avisos": avisos,
    }


def salvar_operacao(sessao: Session, dados, operacao: Operacao | None = None) -> Operacao:
    anterior = auditoria.snapshot(operacao) if operacao is not None else None
    ativo = sessao.get(Ativo, dados.ativo_id)
    if ativo is None or ativo.classe != "CRIPTO":
        raise ValueError("A operação precisa estar vinculada a um ativo CRIPTO")
    if operacao is not None and operacao.transferencia_pareada is not None:
        campos = ("investidor_id", "ativo_id", "data", "evento", "quantidade", "preco", "moeda")
        if any(getattr(dados, campo) != getattr(operacao, campo) for campo in campos):
            raise ValueError("Desfaça o vínculo da transferência antes de alterar suas pernas")

    resolvidos = cambios_operacao(
        sessao, dados.data, dados.moeda, dados.taxas_moeda,
        dados.cambio_usd if dados.cambio_usd_manual else None,
        dados.taxas_cambio_usd if dados.taxas_cambio_usd_manual else None,
    )
    valor_original = dados.valor_original if dados.evento in ("C", "V") else None
    preco = valor_original / abs(dados.quantidade) if valor_original is not None else dados.preco
    if operacao is None:
        operacao = Operacao(origem="manual")
        sessao.add(operacao)

    operacao.investidor_id = dados.investidor_id
    operacao.ativo_id = dados.ativo_id
    operacao.corretora_id = dados.corretora_id
    operacao.data = dados.data
    operacao.evento = dados.evento
    operacao.quantidade = dados.quantidade
    operacao.preco = preco
    operacao.taxas = dados.taxas
    operacao.irrf = dados.irrf
    operacao.moeda = dados.moeda
    operacao.cambio = resolvidos["cambio_brl"]
    operacao.daytrade = dados.daytrade
    operacao.observacao = dados.observacao
    operacao.cripto_valor_original = valor_original
    operacao.cripto_cambio_usd = resolvidos["cambio_usd"]
    operacao.cripto_cambio_usd_data_moeda = resolvidos["data_moeda"]
    operacao.cripto_cambio_usd_data_usd = resolvidos["data_usd"]
    operacao.cripto_cambio_usd_fonte = resolvidos["fonte"]
    operacao.cripto_valor_usd = (
        valor_original * resolvidos["cambio_usd"] if valor_original is not None else None
    )
    operacao.taxas_moeda = dados.taxas_moeda
    operacao.taxas_cambio_brl = resolvidos["taxas_cambio_brl"]
    operacao.taxas_cambio_usd = resolvidos["taxas_cambio_usd"]
    operacao.taxas_cambio_usd_data_moeda = resolvidos["taxas_data_moeda"]
    operacao.taxas_cambio_usd_data_usd = resolvidos["taxas_data_usd"]
    operacao.taxas_cambio_usd_fonte = resolvidos["taxas_fonte"]
    operacao.taxas_valor_usd = dados.taxas * resolvidos["taxas_cambio_usd"]
    sessao.flush()
    auditoria.registrar(sessao, operacao, "alterado" if anterior is not None else "criado", anterior)
    sessao.commit()
    sessao.refresh(operacao)
    return operacao


def salvar_troca_ticker(sessao: Session, dados) -> tuple[Operacao, Operacao]:
    origem = sessao.get(Ativo, dados.ativo_origem_id)
    destino = sessao.get(Ativo, dados.ativo_destino_id)
    if origem is None or origem.classe != "CRIPTO" or destino is None or destino.classe != "CRIPTO":
        raise ValueError("Origem e destino da troca precisam ser ativos CRIPTO")

    resolvidos = cambios_operacao(
        sessao, dados.data, dados.moeda, dados.taxas_moeda,
        dados.cambio_usd if dados.cambio_usd_manual else None,
        dados.taxas_cambio_usd if dados.taxas_cambio_usd_manual else None,
    )
    observacao = f"AT {origem.ticker}->{destino.ticker}"
    if dados.observacao:
        observacao = f"{observacao} | {dados.observacao}"

    def criar_perna(ativo_id: int, quantidade: Decimal, preco: Decimal, saida: bool) -> Operacao:
        return Operacao(
            investidor_id=dados.investidor_id,
            ativo_id=ativo_id,
            corretora_id=dados.corretora_id,
            data=dados.data,
            evento="TRANSFERENCIA",
            quantidade=quantidade,
            preco=preco,
            taxas=dados.taxas if saida else ZERO,
            irrf=dados.irrf if saida else ZERO,
            moeda=dados.moeda,
            cambio=resolvidos["cambio_brl"],
            observacao=observacao,
            origem="manual",
            cripto_cambio_usd=resolvidos["cambio_usd"],
            cripto_cambio_usd_data_moeda=resolvidos["data_moeda"],
            cripto_cambio_usd_data_usd=resolvidos["data_usd"],
            cripto_cambio_usd_fonte=resolvidos["fonte"],
            taxas_moeda=dados.taxas_moeda,
            taxas_cambio_brl=resolvidos["taxas_cambio_brl"],
            taxas_cambio_usd=resolvidos["taxas_cambio_usd"],
            taxas_cambio_usd_data_moeda=resolvidos["taxas_data_moeda"],
            taxas_cambio_usd_data_usd=resolvidos["taxas_data_usd"],
            taxas_cambio_usd_fonte=resolvidos["taxas_fonte"],
            taxas_valor_usd=dados.taxas * resolvidos["taxas_cambio_usd"] if saida else ZERO,
        )

    preco_destino = dados.quantidade_origem * dados.preco_origem / dados.quantidade_destino
    saida = criar_perna(dados.ativo_origem_id, -dados.quantidade_origem, dados.preco_origem, True)
    entrada = criar_perna(dados.ativo_destino_id, dados.quantidade_destino, preco_destino, False)
    sessao.add_all((saida, entrada))
    sessao.flush()
    saida.transferencia_pareada_id = entrada.id
    entrada.transferencia_pareada_id = saida.id
    auditoria.registrar(sessao, saida, "criado")
    auditoria.registrar(sessao, entrada, "criado")
    sessao.commit()
    sessao.refresh(saida)
    sessao.refresh(entrada)
    return saida, entrada


def _historico_cambio(sessao: Session) -> dict[str, tuple[list[date], list[Decimal]]]:
    historico: dict[str, list[tuple[date, Decimal]]] = {m: [] for m in MOEDAS_CRIPTO}
    for moeda, dia, valor in sessao.execute(
        select(CotacaoMoeda.moeda, CotacaoMoeda.data, CotacaoMoeda.valor)
        .where(CotacaoMoeda.moeda.in_(MOEDAS_CRIPTO))
        .order_by(CotacaoMoeda.data)
    ):
        historico.setdefault(moeda, []).append((dia, valor))
    return {
        moeda: ([dia for dia, _ in valores], [valor for _, valor in valores])
        for moeda, valores in historico.items()
    }


def _cambio_na_data(
    historico: dict[str, tuple[list[date], list[Decimal]]], moeda: str, dia: date
) -> Decimal | None:
    datas, valores = historico.get(moeda, ([], []))
    posicao = bisect_right(datas, dia) - 1
    return valores[posicao] if posicao >= 0 else None


def _posicoes_em_moeda(
    sessao: Session, investidores: Sequence[int] | None, ativos: set[int], moeda_visualizacao: str
) -> tuple[dict[int, object], set[int]]:
    consulta = (
        select(Operacao)
        .where(Operacao.ativo_id.in_(ativos))
        .order_by(Operacao.data, Operacao.id)
    )
    if investidores:
        consulta = consulta.where(Operacao.investidor_id.in_(investidores))
    historico = _historico_cambio(sessao)
    movimentos = []
    incompletos: set[int] = set()
    for op in sessao.scalars(consulta):
        usd_brl = _cambio_na_data(historico, "USD", op.data)
        moeda_brl = _cambio_na_data(historico, moeda_visualizacao, op.data)
        taxa_usd = op.cripto_cambio_usd
        if taxa_usd is None:
            if usd_brl is None:
                incompletos.add(op.ativo_id)
                taxa_usd = ZERO
            else:
                taxa_usd = op.cambio / usd_brl
        usd_para_visualizacao = (
            Decimal(1) if moeda_visualizacao == "USD"
            else usd_brl / moeda_brl if usd_brl is not None and moeda_brl is not None
            else None
        )
        if usd_para_visualizacao is None:
            incompletos.add(op.ativo_id)
            usd_para_visualizacao = ZERO

        principal_usd = op.cripto_valor_usd
        if principal_usd is None and op.evento in ("C", "V"):
            total_original = op.cripto_valor_original or (abs(op.quantidade) * op.preco)
            principal_usd = total_original * taxa_usd
        preco = op.preco * taxa_usd * usd_para_visualizacao
        valor_original = None
        if op.evento in ("C", "V") and principal_usd is not None:
            valor_original = principal_usd * usd_para_visualizacao
            preco = valor_original / abs(op.quantidade) if op.quantidade else ZERO
        taxas_usd = op.taxas_valor_usd
        if taxas_usd is None:
            taxas_usd = op.taxas * taxa_usd
        irrf_usd = op.irrf * taxa_usd
        movimentos.append(Movimento(
            op.investidor_id, op.ativo_id, op.data, op.evento, op.quantidade, preco,
            taxas_usd * usd_para_visualizacao, op.daytrade, op.id, Decimal(1),
            irrf_usd * usd_para_visualizacao, valor_original, Decimal(1),
        ))
    posicoes = calcular_posicoes(movimentos)
    return consolidar(posicoes.values()), incompletos


def painel(
    sessao: Session, investidores: Sequence[int] | None, moeda_visualizacao: str = "BRL"
) -> dict:
    ativos = list(sessao.scalars(select(Ativo).where(Ativo.classe == "CRIPTO").order_by(Ativo.ticker)))
    ids = {a.id for a in ativos}
    linhas = montar_carteira(sessao, investidores, consolidado=True, ativo_ids=ids)
    por_ativo = {l.ativo.id: l for l in linhas}
    snapshots = {s.ativo_id: s for s in sessao.scalars(select(CriptoMercado).where(CriptoMercado.ativo_id.in_(ids)))}
    moeda_visualizacao = moeda_visualizacao.upper()
    if moeda_visualizacao not in MOEDAS_CRIPTO:
        raise ValueError(f"Moeda de visualização de cripto deve ser uma de {MOEDAS_CRIPTO}")
    cambio = sessao.scalar(
        select(CotacaoMoeda).where(CotacaoMoeda.moeda == "USD").order_by(CotacaoMoeda.data.desc()).limit(1)
    )
    cambios = cambios_atuais(sessao)
    if moeda_visualizacao == "USD":
        cambio_usd_visualizacao = Decimal(1)
        cambio_data_visualizacao = cambio.data if cambio else None
    elif moeda_visualizacao == "BRL":
        cambio_usd_visualizacao = cambios.get("USD")
        cambio_data_visualizacao = cambio.data if cambio else None
    elif cambios.get("USD") and cambios.get(moeda_visualizacao):
        cambio_usd_visualizacao = cambios["USD"] / cambios[moeda_visualizacao]
        cambio_data_visualizacao = min(
            sessao.scalar(
                select(CotacaoMoeda.data).where(CotacaoMoeda.moeda == moeda_visualizacao)
                .order_by(CotacaoMoeda.data.desc()).limit(1)
            ),
            cambio.data,
        ) if cambio else None
    else:
        cambio_usd_visualizacao = None
        cambio_data_visualizacao = None

    posicoes_moeda, custos_incompletos = _posicoes_em_moeda(
        sessao, investidores, ids, moeda_visualizacao,
    ) if moeda_visualizacao != "BRL" else ({}, set())
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
        quantidade = linha.posicao.quantidade if linha else ZERO
        if moeda_visualizacao == "BRL":
            custo_visualizacao = linha.posicao.custo if linha else ZERO
            preco_medio_visualizacao = linha.posicao.preco_medio if linha else ZERO
        elif ativo.id in custos_incompletos:
            custo_visualizacao = preco_medio_visualizacao = None
        else:
            posicao_moeda = posicoes_moeda.get(ativo.id)
            custo_visualizacao = posicao_moeda.custo if posicao_moeda else ZERO
            preco_medio_visualizacao = posicao_moeda.preco_medio if posicao_moeda else ZERO
        mercado_visualizacao = (
            ZERO if not quantidade else
            quantidade * snapshot.preco_usd * cambio_usd_visualizacao
            if snapshot and cambio_usd_visualizacao is not None else None
        )
        lucro_visualizacao = (
            mercado_visualizacao - custo_visualizacao
            if mercado_visualizacao is not None and custo_visualizacao is not None else None
        )
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
            "quantidade": quantidade,
            "preco_medio_brl": linha.posicao.preco_medio if linha else ZERO,
            "investido_brl": linha.posicao.custo if linha else ZERO,
            "mercado_brl": linha.valor_mercado if linha else ZERO,
            "lucro_aberto_brl": linha.lucro_aberto if linha else ZERO,
            "preco_visualizacao": snapshot.preco_usd * cambio_usd_visualizacao
            if snapshot and cambio_usd_visualizacao is not None else None,
            "preco_medio_visualizacao": preco_medio_visualizacao,
            "investido_visualizacao": custo_visualizacao,
            "mercado_visualizacao": mercado_visualizacao,
            "lucro_aberto_visualizacao": lucro_visualizacao,
        })
        if ativo.id in custos_incompletos:
            avisos.append(
                f"{ativo.ticker}: câmbio histórico ausente; custo em {moeda_visualizacao} indisponível"
            )
        if snapshot and cambio_usd_visualizacao is None:
            avisos.append(
                f"{ativo.ticker}: câmbio atual USD/{moeda_visualizacao} indisponível; valor de mercado não convertido"
            )
    return {
        "itens": itens, "cambio_usd_brl": cambio.valor if cambio else None,
        "cambio_data": cambio.data if cambio else None, "avisos": avisos,
        "moeda_visualizacao": moeda_visualizacao,
        "cambio_usd_visualizacao": cambio_usd_visualizacao,
        "cambio_data_visualizacao": cambio_data_visualizacao,
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
            valor_original=op.cripto_valor_original,
            taxas_cambio=op.taxas_cambio_brl,
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
        valor_venda = op.cripto_valor_original or (-op.quantidade * op.preco)
        linha["vendas_brl"] += valor_venda * op.cambio
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
