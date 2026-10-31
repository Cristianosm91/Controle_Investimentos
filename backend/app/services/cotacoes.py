from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Ativo, AtivoRadar, Cotacao, CotacaoMoeda, ValuationHistorico
from ..providers.base import AtivoRef, ProvedorCotacao
from ..providers.bcb import ProvedorBcb
from ..providers.yahoo import ProvedorYahoo
from . import renda_fixa
from .carteira import carregar_posicoes
from .cotahist import FONTE as FONTE_B3


def provedores_padrao() -> list[ProvedorCotacao]:
    """Ordem de prioridade: câmbio oficial pela PTAX; ativos pelo Yahoo."""
    return [ProvedorBcb(), ProvedorYahoo()]


@dataclass
class ResultadoAtualizacao:
    atualizados: dict[str, str] = field(default_factory=dict)
    sem_cotacao: list[str] = field(default_factory=list)


def ativos_monitorados(sessao: Session) -> list[Ativo]:
    ids = {p.ativo_id for p in carregar_posicoes(sessao, None).values() if p.aberta}
    acompanhados = select(AtivoRadar.ativo_id)
    com_valuation = select(ValuationHistorico.ativo_id)
    return list(
        sessao.scalars(
            select(Ativo).where(
                Ativo.cotacao_automatica,
                Ativo.id.in_(ids) | Ativo.id.in_(acompanhados) | Ativo.id.in_(com_valuation),
            )
        )
    )


def atualizar_cotacoes(
    sessao: Session, provedores: Sequence[ProvedorCotacao] | None = None, ativos: Sequence[Ativo] | None = None
) -> ResultadoAtualizacao:
    """Consulta os provedores em ordem; cada um só recebe os ativos que os anteriores não resolveram."""
    provedores = provedores if provedores is not None else provedores_padrao()
    ativos_padrao = ativos is None
    ativos = [
        ativo for ativo in (ativos if ativos is not None else ativos_monitorados(sessao))
        if ativo.classe != "CRIPTO"
    ]
    pendentes = {a.ticker: a for a in ativos}
    resultado = ResultadoAtualizacao()

    for provedor in provedores:
        if not pendentes:
            break
        refs = [AtivoRef(a.ticker, a.mercado, a.moeda) for a in pendentes.values()]
        for ticker, cot in provedor.cotacoes(refs).items():
            ativo = pendentes.pop(ticker, None)
            if ativo is None:
                continue
            linha = sessao.scalar(select(Cotacao).where(Cotacao.ativo_id == ativo.id, Cotacao.data == cot.data))
            if linha is None:
                linha = Cotacao(ativo_id=ativo.id, data=cot.data)
                sessao.add(linha)
            if linha.fonte != FONTE_B3:  # fechamento oficial prevalece
                linha.preco, linha.variacao_pct, linha.fonte = cot.preco, cot.variacao_pct, cot.fonte
            resultado.atualizados[ticker] = linha.fonte

    moedas_pendentes = {a.moeda for a in ativos if a.moeda != "BRL"}
    for provedor in provedores:
        if not moedas_pendentes:
            break
        for moeda, cot in provedor.cambios(sorted(moedas_pendentes)).items():
            moedas_pendentes.discard(moeda)
            linha = sessao.scalar(
                select(CotacaoMoeda).where(CotacaoMoeda.moeda == moeda, CotacaoMoeda.data == cot.data)
            )
            if linha is None:
                linha = CotacaoMoeda(moeda=moeda, data=cot.data)
                sessao.add(linha)
            linha.valor, linha.fonte = cot.preco, cot.fonte
            resultado.atualizados[moeda] = cot.fonte

    sessao.commit()
    if ativos_padrao:
        resultado.atualizados.update(renda_fixa.atualizar(sessao))
    resultado.sem_cotacao = sorted(pendentes) + sorted(moedas_pendentes)
    return resultado
