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
from .posicao import Carteira, Movimento, consolidar, ordenar

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

    ops_moeda = sessao.scalars(
        select(Operacao)
        .join(Ativo, Ativo.id == Operacao.ativo_id)
        .where(Operacao.moeda == "BRL", *_filtro(Operacao, investidor_ids))
    ).all()
    itens_moeda = []
    for op in ops_moeda:
        at = op.ativo
        classe = (at.classe or "").strip().upper()
        mercado = (at.mercado or "").strip().upper()
        eh_bdr = classe == "BDR" or at.ticker.endswith(("31", "32", "33", "34", "35", "39"))
        eh_ext = classe in ("STOCK", "REIT", "ETF_US") or mercado in ("NYSE", "NASDAQ")
        if eh_ext and not eh_bdr:
            itens_moeda.append(f"{at.ticker} em {op.data:%d/%m/%Y}: ativo internacional em BRL (esperado: USD com PTAX)")
    adicionar(
        Verificacao(
            "moeda_incompativel", "Moeda incompatível com o ativo", "erro",
            "Ativos no exterior (STOCK, REIT, ETF_US) devem ter lançamentos em USD com PTAX. "
            "Lançamentos em BRL subestimam severamente o custo de aquisição.",
            "/operacoes",
        ),
        itens_moeda,
    )

    todos_ativos = {a.id: a for a in sessao.scalars(select(Ativo))}
    todas_ops = [
        Movimento(r.investidor_id, r.ativo_id, r.data, r.evento, r.quantidade, r.preco, r.taxas, r.daytrade, r.id, r.cambio)
        for r in sessao.execute(
            select(Operacao.investidor_id, Operacao.ativo_id, Operacao.data, Operacao.evento, Operacao.quantidade,
                   Operacao.preco, Operacao.taxas, Operacao.daytrade, Operacao.id, Operacao.cambio)
            .where(*_filtro(Operacao, investidor_ids))
        )
    ]
    carteira_audit = Carteira()
    saidas_at = []
    entradas_at = []
    compras_c = []

    for m in ordenar(todas_ops):
        if m.evento == "TRANSFERENCIA":
            if m.quantidade < 0:
                p_ant = carteira_audit.posicoes.get((m.investidor_id, m.ativo_id))
                pm_ant = p_ant.preco_medio if p_ant else Decimal(0)
                custo_saida = abs(m.quantidade) * pm_ant
                saidas_at.append({
                    "id": m.ordem, "inv_id": m.investidor_id, "ativo_id": m.ativo_id,
                    "data": m.data, "qtd": abs(m.quantidade), "custo": custo_saida,
                    "volume": abs(m.quantidade * m.preco * m.cambio), "pareado": False,
                })
            else:
                custo_entrada = m.quantidade * m.preco * m.cambio
                entradas_at.append({
                    "id": m.ordem, "inv_id": m.investidor_id, "ativo_id": m.ativo_id,
                    "data": m.data, "qtd": m.quantidade, "custo": custo_entrada,
                    "volume": abs(m.quantidade * m.preco * m.cambio), "pareado": False,
                })
        elif m.evento == "C" and not m.daytrade:
            compras_c.append({
                "id": m.ordem, "inv_id": m.investidor_id, "ativo_id": m.ativo_id,
                "data": m.data, "volume": (m.quantidade * m.preco + m.taxas) * m.cambio,
            })
        carteira_audit.aplicar(m)

    itens_custo_divergente = []
    itens_compra_troca = []
    itens_orfas = []

    for ent in entradas_at:
        candidatos = [
            s for s in saidas_at
            if s["inv_id"] == ent["inv_id"] and not s["pareado"] and abs((ent["data"] - s["data"]).days) <= 7
        ]
        if candidatos:
            melhor = min(candidatos, key=lambda s: (abs(ent["custo"] - s["custo"]), abs((ent["data"] - s["data"]).days)))
            melhor["pareado"] = True
            ent["pareado"] = True
            dif = abs(ent["custo"] - melhor["custo"])
            if dif > Decimal("0.05"):
                tik_saida = todos_ativos[melhor["ativo_id"]].ticker
                tik_entrada = todos_ativos[ent["ativo_id"]].ticker
                itens_custo_divergente.append(
                    f"{tik_saida} → {tik_entrada} ({ent['data']:%d/%m/%Y}): custo de saída R$ {melhor['custo']:.2f} difere da entrada R$ {ent['custo']:.2f} (dif: R$ {dif:.2f})"
                )

    for sai in saidas_at:
        if not sai["pareado"]:
            c_cands = [
                c for c in compras_c
                if c["inv_id"] == sai["inv_id"] and abs((c["data"] - sai["data"]).days) <= 7 and abs(c["volume"] - sai["volume"]) <= Decimal("1.00")
            ]
            tik_saida = todos_ativos[sai["ativo_id"]].ticker
            if c_cands:
                melhor_c = min(c_cands, key=lambda c: abs((c["data"] - sai["data"]).days))
                tik_c = todos_ativos[melhor_c["ativo_id"]].ticker
                itens_compra_troca.append(
                    f"Possível troca de ticker como compra: {tik_c} compra em {melhor_c['data']:%d/%m/%Y} (R$ {melhor_c['volume']:.2f}) coincide com saída de {tik_saida} em {sai['data']:%d/%m/%Y}. Use AT nas duas pontas para não duplicar fluxo."
                )
            else:
                itens_orfas.append(f"{tik_saida} · saída AT de {sai['qtd']} em {sai['data']:%d/%m/%Y} sem entrada correspondente na janela")

    for ent in entradas_at:
        if not ent["pareado"]:
            tik_entrada = todos_ativos[ent["ativo_id"]].ticker
            itens_orfas.append(f"{tik_entrada} · entrada AT de {ent['qtd']} em {ent['data']:%d/%m/%Y} sem saída correspondente na janela")

    adicionar(
        Verificacao(
            "transferencia_divergente", "Custo de transferência divergente", "erro",
            "Na troca de ticker (AT), o custo herdado na entrada deve ser rigorosamente igual ao PM do ticker de origem vezes a quantidade. "
            "Diferenças distorcem o preço médio e o valor investido.",
            "/operacoes",
        ),
        itens_custo_divergente,
    )
    adicionar(
        Verificacao(
            "compra_no_lugar_de_troca", "Troca de ticker lançada como compra", "erro",
            "Entrada do novo ticker lançada como Compra (C) em vez de Troca (AT): duplica indevidamente o fluxo de dinheiro que saiu do bolso.",
            "/operacoes",
        ),
        itens_compra_troca,
    )
    adicionar(
        Verificacao(
            "transferencia_orfa", "Transferência (AT) sem contraparte", "aviso",
            "Operação de transferência (AT) de saída ou entrada sem a contraparte pareada na janela de datas.",
            "/operacoes",
        ),
        itens_orfas,
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
