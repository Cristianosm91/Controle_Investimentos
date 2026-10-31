"""Verificações de qualidade e completude dos dados que afetam posição, rentabilidade e IR."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Ativo, IndiceMensal, Investidor, MovCaixa, Operacao, Provento
from . import configuracao, parametros
from .carteira import carregar_posicoes, ultimas_cotacoes
from .posicao import consolidar

_LIMITE_ITENS = 50


@dataclass
class Verificacao:
    codigo: str
    titulo: str
    severidade: str  # erro | aviso | info
    descricao: str
    link: str | None = None
    itens: list[str] = field(default_factory=list)


def verificar(sessao: Session, investidor_ids: Sequence[int] | None = None, hoje: date | None = None) -> list[Verificacao]:
    """Só devolve as verificações com pendências; lista vazia = dados sem problemas conhecidos."""
    hoje = hoje or date.today()
    params = parametros.carregar(sessao)
    nomes = dict(sessao.execute(select(Investidor.id, Investidor.nome)).all())
    posicoes = carregar_posicoes(sessao, investidor_ids)
    ativos = {a.id: a for a in sessao.scalars(select(Ativo).where(Ativo.id.in_({a for _, a in posicoes})))} if posicoes else {}
    abertas = {a: p for a, p in consolidar(p for p in posicoes.values() if p.aberta).items()}
    resultado: list[Verificacao] = []

    def adicionar(v: Verificacao, itens: list[str]) -> None:
        if itens:
            v.itens = sorted(itens)[:_LIMITE_ITENS]
            if len(itens) > _LIMITE_ITENS:
                v.itens.append(f"… e mais {len(itens) - _LIMITE_ITENS}")
            resultado.append(v)

    adicionar(
        Verificacao(
            "posicao_negativa", "Posição negativa", "erro",
            "Há mais vendas que compras: falta lançar uma compra, bonificação, desdobramento ou transferência. "
            "Preço médio, lucro e IR desses ativos ficam incorretos.", "/operacoes",
        ),
        [
            f"{ativos[a].ticker} · {nomes.get(inv, inv)} · {p.quantidade.normalize():f}"
            for (inv, a), p in posicoes.items() if p.quantidade < Decimal("-1e-9")
        ],
    )

    cambio_zerado = sessao.execute(
        select(Ativo.ticker, Operacao.data)
        .join(Ativo, Ativo.id == Operacao.ativo_id)
        .where(Operacao.moeda != "BRL", Operacao.cambio == 1, *_filtro(Operacao, investidor_ids))
    ).all()
    adicionar(
        Verificacao(
            "cambio_ausente", "Lançamento no exterior sem câmbio", "erro",
            "Operações em moeda estrangeira com câmbio 1: o custo em reais fica errado. Edite e use a PTAX da data.",
            "/operacoes",
        ),
        [f"{t} em {d:%d/%m/%Y}" for t, d in cambio_zerado],
    )

    cotacoes = ultimas_cotacoes(sessao, set(abertas))
    automaticas = [a for a in abertas if ativos[a].cotacao_automatica]
    adicionar(
        Verificacao(
            "sem_cotacao", "Posição sem cotação", "aviso",
            "Esses ativos entram no patrimônio pelo custo. Confira o ticker/mercado do ativo ou atualize as cotações.",
            "/configuracoes?secao=atualizacoes",
        ),
        [ativos[a].ticker for a in abertas if a not in cotacoes],
    )
    if params.alerta_cotacao_dias:
        limite = hoje - timedelta(days=params.alerta_cotacao_dias)
        adicionar(
            Verificacao(
                "cotacao_antiga", "Cotação desatualizada", "aviso",
                f"Cotação automática sem atualização há mais de {params.alerta_cotacao_dias} dias "
                "(ativo deslistado, ticker alterado ou falha da fonte).", "/configuracoes?secao=atualizacoes",
            ),
            [
                f"{ativos[a].ticker} · {cotacoes[a].data:%d/%m/%Y}"
                for a in automaticas if a in cotacoes and cotacoes[a].data < limite
            ],
        )

    em_carteira = [ativos[a] for a in abertas]
    classificacao = configuracao.carregar(sessao)
    if classificacao.books:
        adicionar(
            Verificacao(
                "sem_book", "Ativo sem book", "aviso",
                "A classe desses ativos não está mapeada para nenhum book: ficam fora da alocação-alvo.",
                "/configuracoes?secao=estrategias",
            ),
            [f"{a.ticker} ({a.classe})" for a in em_carteira if classificacao.book_principal(a) is None],
        )
    adicionar(
        Verificacao(
            "sem_setor", "Ativo sem setor", "info",
            "Ações e FIIs sem setor aparecem como \"Sem setor\" na exposição.", "/portfolio",
        ),
        [a.ticker for a in em_carteira if a.cotacao_automatica and a.classe in ("AÇÃO", "FII") and not a.setor],
    )
    adicionar(
        Verificacao(
            "rf_sem_vencimento", "Renda fixa sem vencimento", "info",
            "Informe o vencimento para ver a projeção no vencimento e receber alertas.", "/configuracoes?secao=ativos",
        ),
        [a.ticker for a in em_carteira if not a.cotacao_automatica and a.indexador and not a.data_vencimento],
    )

    sem_corretora = sum(
        sessao.scalar(select(func.count()).where(m.corretora_id.is_(None), *_filtro(m, investidor_ids))) or 0
        for m in (Operacao, Provento, MovCaixa)
    )
    if sem_corretora:
        resultado.append(Verificacao(
            "sem_corretora", "Lançamentos sem corretora", "info",
            "Não entram no saldo por corretora nem na exposição por instituição.", "/operacoes",
            [f"{sem_corretora} lançamento(s)"],
        ))

    ultimo_indice = sessao.scalar(select(func.max(IndiceMensal.competencia)).where(IndiceMensal.cdi.is_not(None)))
    if abertas and (ultimo_indice is None or ultimo_indice < (hoje.replace(day=1) - timedelta(days=62)).replace(day=1)):
        resultado.append(Verificacao(
            "indices_antigos", "Índices desatualizados", "aviso",
            "CDI/IPCA do Banco Central sem atualização recente: benchmarks e renda fixa automática ficam defasados.",
            "/configuracoes?secao=atualizacoes",
            [f"Último mês: {ultimo_indice:%m/%Y}" if ultimo_indice else "Nenhum índice carregado"],
        ))

    ordem = {"erro": 0, "aviso": 1, "info": 2}
    return sorted(resultado, key=lambda v: ordem[v.severidade])


def _filtro(modelo, investidor_ids: Sequence[int] | None) -> list:
    return [modelo.investidor_id.in_(investidor_ids)] if investidor_ids else []
