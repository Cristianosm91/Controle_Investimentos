from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import insert_upsert
from ..models import Ativo, AtivoRadar, Cotacao, CotacaoMoeda, ValuationHistorico
from ..providers.base import AtivoRef, CotacaoAtual, ProvedorCotacao
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
    # Fonte fora do ar/resposta vazia: distinto de ticker sem cotação; não altera o que é gravado.
    falhas_fonte: list[str] = field(default_factory=list)


def _drenar_falhas(provedor: ProvedorCotacao) -> list[str]:
    falhas = getattr(provedor, "falhas", None)
    if not falhas:
        return []
    copia = list(falhas)
    falhas.clear()
    return copia


def gravar_cambio(sessao: Session, moeda: str, cot: CotacaoAtual) -> None:
    """Upsert por (moeda, data): os jobs de cotações e cripto podem gravar a mesma chave ao mesmo tempo."""
    comando = insert_upsert(sessao, CotacaoMoeda).values(moeda=moeda, data=cot.data, valor=cot.preco, fonte=cot.fonte)
    sessao.execute(
        comando.on_conflict_do_update(
            index_elements=["moeda", "data"],
            set_={"valor": comando.excluded.valor, "fonte": comando.excluded.fonte},
        )
    )


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
        encontrados = provedor.cotacoes(refs)
        resultado.falhas_fonte.extend(_drenar_falhas(provedor))
        for ticker, cot in encontrados.items():
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
        encontrados = provedor.cambios(sorted(moedas_pendentes))
        resultado.falhas_fonte.extend(_drenar_falhas(provedor))
        for moeda, cot in encontrados.items():
            moedas_pendentes.discard(moeda)
            gravar_cambio(sessao, moeda, cot)
            resultado.atualizados[moeda] = cot.fonte

    sessao.commit()
    if ativos_padrao:
        resultado.atualizados.update(renda_fixa.atualizar(sessao, falhas=resultado.falhas_fonte))
    resultado.sem_cotacao = sorted(pendentes) + sorted(moedas_pendentes)
    return resultado
