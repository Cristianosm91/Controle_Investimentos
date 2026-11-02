"""Verificações de qualidade e completude dos dados que afetam posição, rentabilidade e IR."""

import hashlib
import json
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
    fingerprint: str = ""
    operacao_ids: list[int] = field(default_factory=list)
    provento_ids: list[int] = field(default_factory=list)
    caixa_ids: list[int] = field(default_factory=list)
    ativo_ids: list[int] = field(default_factory=list)
    investidor_ids: list[int] = field(default_factory=list)
    status: str = "aberto"


def verificar(sessao: Session, investidor_ids: Sequence[int] | None = None, hoje: date | None = None) -> list[Verificacao]:
    """Só devolve as verificações com pendências; lista vazia = dados sem problemas conhecidos."""
    hoje = hoje or date.today()
    params = parametros.carregar(sessao)
    nomes = dict(sessao.execute(select(Investidor.id, Investidor.nome)).all())
    posicoes = carregar_posicoes(sessao, investidor_ids)
    ativos = {a.id: a for a in sessao.scalars(select(Ativo).where(Ativo.id.in_({a for _, a in posicoes})))} if posicoes else {}
    abertas = {a: p for a, p in consolidar(p for p in posicoes.values() if p.aberta).items()}
    resultado: list[Verificacao] = []
    operacoes = sessao.scalars(
        select(Operacao).where(*_filtro(Operacao, investidor_ids))
    ).all()
    operacoes_por_posicao: dict[tuple[int, int], list[int]] = {}
    for operacao in operacoes:
        operacoes_por_posicao.setdefault(
            (operacao.investidor_id, operacao.ativo_id), []
        ).append(operacao.id)

    def adicionar(
        v: Verificacao,
        itens: list[str],
        *,
        operacao_ids: Sequence[int] = (),
        ativo_ids: Sequence[int] = (),
        investidor_ids: Sequence[int] = (),
        identidade: object = None,
    ) -> None:
        if itens:
            v.itens = sorted(itens)[:_LIMITE_ITENS]
            if len(itens) > _LIMITE_ITENS:
                v.itens.append(f"… e mais {len(itens) - _LIMITE_ITENS}")
            v.operacao_ids = sorted(set(operacao_ids))
            v.ativo_ids = sorted(set(ativo_ids))
            v.investidor_ids = sorted(set(investidor_ids))

            operacoes = sessao.scalars(
                select(Operacao).where(Operacao.id.in_(v.operacao_ids))
            ).all() if v.operacao_ids else []
            ativos_ref = sessao.scalars(
                select(Ativo).where(Ativo.id.in_(v.ativo_ids))
            ).all() if v.ativo_ids else []
            contexto = {
                "codigo": v.codigo,
                "operacoes": [
                    [
                        op.id, op.investidor_id, op.ativo_id, op.data.isoformat(),
                        op.evento, _decimal_normalizado(op.quantidade),
                        _decimal_normalizado(op.preco), _decimal_normalizado(op.taxas),
                        _decimal_normalizado(op.irrf), op.moeda,
                        _decimal_normalizado(op.cambio), op.daytrade,
                    ]
                    for op in sorted(operacoes, key=lambda item: item.id)
                ],
                "ativos": [
                    [
                        at.id, at.ticker, at.classe, at.mercado, at.moeda, at.setor,
                        at.cotacao_automatica, at.indexador, at.data_vencimento.isoformat()
                        if at.data_vencimento else None,
                    ]
                    for at in sorted(ativos_ref, key=lambda item: item.id)
                ],
                "investidor_ids": v.investidor_ids,
                "identidade": identidade,
            }
            v.fingerprint = hashlib.sha256(
                json.dumps(contexto, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()
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
        operacao_ids=[
            operacao_id
            for (investidor_id, ativo_id), posicao in posicoes.items()
            if posicao.quantidade < Decimal("-1e-9")
            for operacao_id in operacoes_por_posicao.get((investidor_id, ativo_id), [])
        ],
        ativo_ids=[
            ativo_id for (_, ativo_id), posicao in posicoes.items()
            if posicao.quantidade < Decimal("-1e-9")
        ],
        investidor_ids=[
            investidor_id for (investidor_id, _), posicao in posicoes.items()
            if posicao.quantidade < Decimal("-1e-9")
        ],
        identidade=[
            (investidor_id, ativo_id, _decimal_normalizado(posicao.quantidade))
            for (investidor_id, ativo_id), posicao in posicoes.items()
            if posicao.quantidade < Decimal("-1e-9")
        ],
    )

    cambio_zerado = sessao.execute(
        select(Operacao.id, Operacao.investidor_id, Operacao.ativo_id, Ativo.ticker, Operacao.data)
        .join(Ativo, Ativo.id == Operacao.ativo_id)
        .where(Operacao.moeda != "BRL", Operacao.cambio == 1, *_filtro(Operacao, investidor_ids))
    ).all()
    adicionar(
        Verificacao(
            "cambio_ausente", "Lançamento no exterior sem câmbio", "erro",
            "Operações em moeda estrangeira com câmbio 1: o custo em reais fica errado. Edite e use a PTAX da data.",
            "/operacoes",
        ),
        [f"{ticker} em {dia:%d/%m/%Y}" for _, _, _, ticker, dia in cambio_zerado],
        operacao_ids=[operacao_id for operacao_id, *_ in cambio_zerado],
        ativo_ids=[ativo_id for _, _, ativo_id, _, _ in cambio_zerado],
        investidor_ids=[investidor_id for _, investidor_id, _, _, _ in cambio_zerado],
    )

    ops_moeda = sessao.scalars(
        select(Operacao)
        .join(Ativo, Ativo.id == Operacao.ativo_id)
        .where(Operacao.moeda == "BRL", *_filtro(Operacao, investidor_ids))
    ).all()
    itens_moeda = []
    operacoes_moeda_ids = []
    for op in ops_moeda:
        at = op.ativo
        classe = (at.classe or "").strip().upper()
        mercado = (at.mercado or "").strip().upper()
        eh_bdr = classe == "BDR" or at.ticker.endswith(("31", "32", "33", "34", "35", "39"))
        eh_ext = classe in ("STOCK", "REIT", "ETF_US") or mercado in ("NYSE", "NASDAQ")
        if eh_ext and not eh_bdr:
            operacoes_moeda_ids.append(op.id)
            itens_moeda.append(f"{at.ticker} em {op.data:%d/%m/%Y}: ativo internacional em BRL (esperado: USD com PTAX)")
    adicionar(
        Verificacao(
            "moeda_incompativel", "Moeda incompatível com o ativo", "erro",
            "Ativos no exterior (STOCK, REIT, ETF_US) devem ter lançamentos em USD com PTAX. "
            "Lançamentos em BRL subestimam severamente o custo de aquisição.",
            "/operacoes",
        ),
        itens_moeda,
        operacao_ids=operacoes_moeda_ids,
        ativo_ids=[op.ativo_id for op in ops_moeda if op.id in operacoes_moeda_ids],
        investidor_ids=[op.investidor_id for op in ops_moeda if op.id in operacoes_moeda_ids],
    )

    todos_ativos = {a.id: a for a in sessao.scalars(select(Ativo))}
    todas_ops = [
        Movimento(
            r.investidor_id, r.ativo_id, r.data, r.evento, r.quantidade, r.preco,
            r.taxas, r.daytrade, r.id, r.cambio,
        )
        for r in operacoes
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
    ids_custo_divergente = []
    ids_compra_troca = []
    ids_orfas = []
    ativos_custo_divergente = []
    ativos_compra_troca = []
    ativos_orfas = []
    investidores_custo_divergente = []
    investidores_compra_troca = []
    investidores_orfas = []

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
                    f"{tik_saida} → {tik_entrada} ({ent['data']:%d/%m/%Y}): "
                    f"custo de saída R$ {melhor['custo']:.2f} difere da entrada "
                    f"R$ {ent['custo']:.2f} (dif: R$ {dif:.2f})"
                )
                ids_custo_divergente.extend((melhor["id"], ent["id"]))
                ativos_custo_divergente.extend((melhor["ativo_id"], ent["ativo_id"]))
                investidores_custo_divergente.append(ent["inv_id"])

    for sai in saidas_at:
        if not sai["pareado"]:
            c_cands = [
                c for c in compras_c
                if c["inv_id"] == sai["inv_id"]
                and abs((c["data"] - sai["data"]).days) <= 7
                and abs(c["volume"] - sai["volume"]) <= Decimal("1.00")
            ]
            tik_saida = todos_ativos[sai["ativo_id"]].ticker
            if c_cands:
                melhor_c = min(c_cands, key=lambda c: abs((c["data"] - sai["data"]).days))
                tik_c = todos_ativos[melhor_c["ativo_id"]].ticker
                itens_compra_troca.append(
                    f"Possível troca de ticker como compra: {tik_c} compra em "
                    f"{melhor_c['data']:%d/%m/%Y} (R$ {melhor_c['volume']:.2f}) "
                    f"coincide com saída de {tik_saida} em "
                    f"{sai['data']:%d/%m/%Y}. Use AT nas duas pontas para não duplicar fluxo."
                )
                ids_compra_troca.extend((sai["id"], melhor_c["id"]))
                ativos_compra_troca.extend((sai["ativo_id"], melhor_c["ativo_id"]))
                investidores_compra_troca.append(sai["inv_id"])
            else:
                itens_orfas.append(
                    f"{tik_saida} · saída AT de {sai['qtd']} em "
                    f"{sai['data']:%d/%m/%Y} sem entrada correspondente na janela"
                )
                ids_orfas.append(sai["id"])
                ativos_orfas.append(sai["ativo_id"])
                investidores_orfas.append(sai["inv_id"])

    for ent in entradas_at:
        if not ent["pareado"]:
            tik_entrada = todos_ativos[ent["ativo_id"]].ticker
            itens_orfas.append(
                f"{tik_entrada} · entrada AT de {ent['qtd']} em "
                f"{ent['data']:%d/%m/%Y} sem saída correspondente na janela"
            )
            ids_orfas.append(ent["id"])
            ativos_orfas.append(ent["ativo_id"])
            investidores_orfas.append(ent["inv_id"])

    adicionar(
        Verificacao(
            "transferencia_divergente", "Custo de transferência divergente", "erro",
            "Na troca de ticker (AT), o custo herdado na entrada deve ser rigorosamente igual ao PM do ticker de origem "
            "vezes a quantidade. "
            "Diferenças distorcem o preço médio e o valor investido.",
            "/operacoes",
        ),
        itens_custo_divergente,
        operacao_ids=ids_custo_divergente,
        ativo_ids=ativos_custo_divergente,
        investidor_ids=investidores_custo_divergente,
    )
    adicionar(
        Verificacao(
            "compra_no_lugar_de_troca", "Troca de ticker lançada como compra", "erro",
            "Entrada do novo ticker lançada como Compra (C) em vez de Troca (AT): duplica indevidamente o fluxo de "
            "dinheiro que saiu do bolso.",
            "/operacoes",
        ),
        itens_compra_troca,
        operacao_ids=ids_compra_troca,
        ativo_ids=ativos_compra_troca,
        investidor_ids=investidores_compra_troca,
    )
    adicionar(
        Verificacao(
            "transferencia_orfa", "Transferência (AT) sem contraparte", "aviso",
            "Operação de transferência (AT) de saída ou entrada sem a contraparte pareada na janela de datas.",
            "/operacoes",
        ),
        itens_orfas,
        operacao_ids=ids_orfas,
        ativo_ids=ativos_orfas,
        investidor_ids=investidores_orfas,
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
        ativo_ids=[a for a in abertas if a not in cotacoes],
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
            ativo_ids=[
                a for a in automaticas
                if a in cotacoes and cotacoes[a].data < limite
            ],
            identidade={
                "limite_dias": params.alerta_cotacao_dias,
                "cotacoes": [
                    (a, cotacoes[a].data.isoformat())
                    for a in automaticas
                    if a in cotacoes and cotacoes[a].data < limite
                ],
            },
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
            ativo_ids=[a.id for a in em_carteira if classificacao.book_principal(a) is None],
            identidade={"books": repr(classificacao.books)},
        )
    adicionar(
        Verificacao(
            "sem_setor", "Ativo sem setor", "info",
            "Ações e FIIs sem setor aparecem como \"Sem setor\" na exposição.", "/portfolio",
        ),
        [a.ticker for a in em_carteira if a.cotacao_automatica and a.classe in ("AÇÃO", "FII") and not a.setor],
        ativo_ids=[
            a.id for a in em_carteira
            if a.cotacao_automatica and a.classe in ("AÇÃO", "FII") and not a.setor
        ],
    )
    adicionar(
        Verificacao(
            "rf_sem_vencimento", "Renda fixa sem vencimento", "info",
            "Informe o vencimento para ver a projeção no vencimento e receber alertas.", "/configuracoes?secao=ativos",
        ),
        [a.ticker for a in em_carteira if not a.cotacao_automatica and a.indexador and not a.data_vencimento],
        ativo_ids=[
            a.id for a in em_carteira
            if not a.cotacao_automatica and a.indexador and not a.data_vencimento
        ],
    )

    sem_corretora_ids = {}
    sem_corretora_registros = {}
    for modelo in (Operacao, Provento, MovCaixa):
        registros = sessao.scalars(
            select(modelo).where(
                modelo.corretora_id.is_(None), *_filtro(modelo, investidor_ids)
            )
        ).all()
        sem_corretora_ids[modelo.__tablename__] = [
            (registro.id, registro.investidor_id) for registro in registros
        ]
        sem_corretora_registros[modelo.__tablename__] = []
        for registro in registros:
            snapshot = {}
            for campo in (
                "id", "investidor_id", "ativo_id", "data", "data_pagamento",
                "evento", "quantidade", "preco", "valor", "taxas", "irrf",
                "moeda", "cambio", "daytrade", "observacao",
            ):
                valor = getattr(registro, campo, None)
                if valor is not None:
                    snapshot[campo] = valor.isoformat() if isinstance(valor, date) else str(valor)
            sem_corretora_registros[modelo.__tablename__].append(snapshot)
    sem_corretora = sum(len(ids) for ids in sem_corretora_ids.values())
    if sem_corretora:
        resultado.append(Verificacao(
            "sem_corretora", "Lançamentos sem corretora", "info",
            "Não entram no saldo por corretora nem na exposição por instituição.", "/operacoes",
            [f"{sem_corretora} lançamento(s)"],
        ))
        verificacao = resultado[-1]
        verificacao.operacao_ids = sorted(
            id_ for id_, _ in sem_corretora_ids[Operacao.__tablename__]
        )
        verificacao.provento_ids = sorted(
            id_ for id_, _ in sem_corretora_ids[Provento.__tablename__]
        )
        verificacao.caixa_ids = sorted(
            id_ for id_, _ in sem_corretora_ids[MovCaixa.__tablename__]
        )
        verificacao.investidor_ids = sorted({
            investidor_id
            for registros in sem_corretora_ids.values()
            for _, investidor_id in registros
        })
        verificacao.fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "codigo": verificacao.codigo,
                    "lancamentos": sem_corretora_registros,
                },
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            ).encode("utf-8")
        ).hexdigest()

    ultimo_indice = sessao.scalar(select(func.max(IndiceMensal.competencia)).where(IndiceMensal.cdi.is_not(None)))
    if abertas and (ultimo_indice is None or ultimo_indice < (hoje.replace(day=1) - timedelta(days=62)).replace(day=1)):
        adicionar(
            Verificacao(
                "indices_antigos", "Índices desatualizados", "aviso",
                "CDI/IPCA do Banco Central sem atualização recente: benchmarks e renda fixa automática ficam defasados.",
                "/configuracoes?secao=atualizacoes",
            ),
            [f"Último mês: {ultimo_indice:%m/%Y}" if ultimo_indice else "Nenhum índice carregado"],
            identidade={
                "ultimo_indice": ultimo_indice.isoformat() if ultimo_indice else None,
            },
            ativo_ids=list(abertas),
        )

    ordem = {"erro": 0, "aviso": 1, "info": 2}
    return sorted(resultado, key=lambda v: ordem[v.severidade])


def _filtro(modelo, investidor_ids: Sequence[int] | None) -> list:
    return [modelo.investidor_id.in_(investidor_ids)] if investidor_ids else []


def _decimal_normalizado(valor: Decimal) -> str:
    return format(valor.normalize(), "f")
