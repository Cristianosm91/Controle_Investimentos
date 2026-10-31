"""Modelos de preço justo e rentabilidade mensal por ativo."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Ativo, Cotacao, Fundamento, ValuationPremissa
from . import rentabilidade as r

ZERO = Decimal(0)
UM = Decimal(1)
_CAMPOS_PREMISSAS = (
    "lpa",
    "vpa",
    "dividendo_anual",
    "roe",
    "payout",
    "g",
    "ke",
    "pl_historico",
    "pl_setor",
    "fcfe_1",
    "fcfe_2",
    "fcfe_3",
    "fcfe_4",
    "fcfe_5",
)


def _premissas_automaticas(cotacao: Cotacao | None, fundamento: Fundamento | None) -> dict[str, Decimal | None]:
    preco = cotacao.preco if cotacao else None
    pl = fundamento.preco_lucro if fundamento else None
    pvp = fundamento.preco_valor_patrimonial if fundamento else None
    dy = fundamento.dividend_yield if fundamento else None
    roe_publicado = fundamento.roe if fundamento else None

    lpa = preco / pl if preco is not None and preco > 0 and pl is not None and pl > 0 else None
    vpa = preco / pvp if preco is not None and preco > 0 and pvp is not None and pvp > 0 else None
    dividendo = preco * dy / Decimal(100) if preco is not None and preco > 0 and dy is not None and dy > 0 else None
    roe = roe_publicado / Decimal(100) if roe_publicado is not None else None
    payout = dividendo / lpa if dividendo is not None and lpa is not None and lpa > 0 else None
    g = roe * (UM - payout) if roe is not None and payout is not None else None

    return {
        "lpa": lpa,
        "vpa": vpa,
        "dividendo_anual": dividendo,
        "roe": roe,
        "payout": payout,
        "g": g,
        "ke": None,
        "pl_historico": None,
        "pl_setor": None,
        "fcfe_1": None,
        "fcfe_2": None,
        "fcfe_3": None,
        "fcfe_4": None,
        "fcfe_5": None,
    }


def _modelo(id_: str, rotulo: str, valor: Decimal | None, motivo: str | None = None) -> dict:
    if valor is not None and valor > 0:
        return {"id": id_, "rotulo": rotulo, "preco_justo": valor, "motivo": None}
    return {
        "id": id_,
        "rotulo": rotulo,
        "preco_justo": None,
        "motivo": motivo or "As premissas não resultam em um preço positivo",
    }


def _modelos(premissas: dict[str, Decimal | None]) -> list[dict]:
    lpa, vpa = premissas["lpa"], premissas["vpa"]
    dividendo = premissas["dividendo_anual"]
    roe, g, ke = premissas["roe"], premissas["g"], premissas["ke"]
    resultados = []

    graham = (
        (Decimal("22.5") * lpa * vpa).sqrt()
        if lpa is not None and vpa is not None and lpa > 0 and vpa > 0
        else None
    )
    resultados.append(
        _modelo("graham", "Graham", graham, "LPA e VPA positivos são necessários")
    )

    bazin = dividendo / Decimal("0.06") if dividendo is not None and dividendo > 0 else None
    resultados.append(_modelo("bazin", "Bazin (DY de 6%)", bazin, "Dividendo anual positivo é necessário"))

    fcfe = [premissas[f"fcfe_{ano}"] for ano in range(1, 6)]
    dcf = None
    dcf_motivo = None
    if ke is None or g is None or any(valor is None for valor in fcfe):
        dcf_motivo = "Informe Ke, g e as cinco projeções anuais de FCFE por ação"
    elif ke <= g or ke <= -UM or g <= -UM:
        dcf_motivo = "Ke deve ser maior que g, e ambos precisam ser maiores que -100%"
    else:
        fluxos = [valor for valor in fcfe if valor is not None]
        valor_terminal = fluxos[-1] * (UM + g) / (ke - g)
        dcf = sum((valor / (UM + ke) ** ano for ano, valor in enumerate(fluxos, start=1)), ZERO)
        dcf += valor_terminal / (UM + ke) ** 5
    resultados.append(_modelo("dcf_fcfe", "DCF (FCFE, 5 anos)", dcf, dcf_motivo))

    gordon = None
    gordon_motivo = None
    if dividendo is None or dividendo <= 0 or ke is None or g is None:
        gordon_motivo = "Informe dividendo anual, Ke e g"
    elif ke <= g or g <= -UM:
        gordon_motivo = "Ke deve ser maior que g, e g precisa ser maior que -100%"
    else:
        gordon = dividendo * (UM + g) / (ke - g)
    resultados.append(_modelo("gordon", "Gordon (dividendos)", gordon, gordon_motivo))

    for id_, rotulo, campo in (
        ("pl_historico", "P/L histórico", "pl_historico"),
        ("pl_setor", "P/L do setor", "pl_setor"),
    ):
        multiplo = premissas[campo]
        valor = lpa * multiplo if lpa is not None and lpa > 0 and multiplo is not None and multiplo > 0 else None
        resultados.append(_modelo(id_, rotulo, valor, "LPA positivo e múltiplo-alvo positivo são necessários"))

    pvp = None
    pvp_motivo = None
    if vpa is None or vpa <= 0 or roe is None or ke is None or g is None:
        pvp_motivo = "Informe VPA positivo, ROE, Ke e g"
    elif ke <= g:
        pvp_motivo = "Ke deve ser maior que g"
    else:
        pvp = vpa * (roe - g) / (ke - g)
    resultados.append(_modelo("pvp_justificado", "P/VP justificado", pvp, pvp_motivo))
    return resultados


def _mediana(valores: list[Decimal]) -> Decimal | None:
    ordenados = sorted(valores)
    if not ordenados:
        return None
    meio = len(ordenados) // 2
    if len(ordenados) % 2:
        return ordenados[meio]
    return (ordenados[meio - 1] + ordenados[meio]) / Decimal(2)


def _rentabilidade(
    sessao: Session,
    ativo_id: int,
    investidores: Sequence[int] | None,
    hoje: date,
) -> dict:
    dados = r.carregar_dados(sessao, investidores, [ativo_id])
    movimentos = [m for m in dados.movimentos if m.ativo_id == ativo_id]
    proventos = [(dia, valor) for _, id_ativo, dia, valor in dados.proventos if id_ativo == ativo_id]
    serie = r.serie_mensal(movimentos, proventos, dados.precificacao, hoje)
    if not serie:
        return {
            "data_referencia": None,
            "tir_aa": None,
            "tir_am": None,
            "twr_acumulado": None,
            "meses": [],
        }

    atual = serie[-1]
    sem_cotacao = ativo_id in atual.sem_cotacao
    tir_aa = None if sem_cotacao else r.tir(movimentos, proventos, atual.mercado, hoje)
    return {
        "data_referencia": atual.data,
        "tir_aa": tir_aa,
        "tir_am": r.ao_mes(tir_aa),
        "twr_acumulado": atual.twr_acumulado,
        "meses": [
            {
                "data": mes.data,
                "investido": mes.investido,
                "mercado": mes.mercado,
                "fluxo": mes.fluxo,
                "twr": mes.twr,
                "twr_acumulado": mes.twr_acumulado,
                "sem_cotacao": ativo_id in mes.sem_cotacao,
            }
            for mes in serie
        ],
    }


def _consultar(sessao: Session, ativo_id: int, investidores: Sequence[int] | None) -> dict:
    ativo = sessao.get(Ativo, ativo_id)
    if ativo is None:
        raise LookupError(f"Ativo {ativo_id} não encontrado")

    cotacao = sessao.scalar(
        select(Cotacao).where(Cotacao.ativo_id == ativo_id).order_by(Cotacao.data.desc(), Cotacao.id.desc()).limit(1)
    )
    fundamento = sessao.scalar(
        select(Fundamento)
        .where(Fundamento.ativo_id == ativo_id)
        .order_by(Fundamento.data_ref.desc(), Fundamento.atualizado_em.desc(), Fundamento.id.desc())
        .limit(1)
    )
    salvo = sessao.scalar(select(ValuationPremissa).where(ValuationPremissa.ativo_id == ativo_id))
    premissas = (
        {campo: getattr(salvo, campo) for campo in _CAMPOS_PREMISSAS}
        if salvo
        else _premissas_automaticas(cotacao, fundamento)
    )
    modelos = _modelos(premissas)
    precos = [modelo["preco_justo"] for modelo in modelos if modelo["preco_justo"] is not None]
    mediana = _mediana(precos)
    preco_atual = cotacao.preco if cotacao else None
    return {
        "ativo_id": ativo.id,
        "ticker": ativo.ticker,
        "nome": ativo.nome,
        "classe": ativo.classe,
        "moeda": ativo.moeda,
        "cotacao": preco_atual,
        "cotacao_data": cotacao.data if cotacao else None,
        "cotacao_fonte": cotacao.fonte if cotacao else None,
        "fundamento_data": fundamento.data_ref if fundamento else None,
        "fundamento_fonte": fundamento.fonte if fundamento else None,
        "premissas_salvas_em": salvo.atualizado_em if salvo else None,
        "premissas": premissas,
        "modelos": modelos,
        "analise": {
            "modelos_disponiveis": len(precos),
            "total_modelos": len(modelos),
            "preco_mediano": mediana,
            "upside_mediano": mediana / preco_atual - UM if mediana is not None and preco_atual and preco_atual > 0 else None,
        },
        "rentabilidade": _rentabilidade(sessao, ativo_id, investidores, date.today()),
    }


def consultar(sessao: Session, ativo_id: int, investidores: Sequence[int] | None) -> dict:
    return _consultar(sessao, ativo_id, investidores)


def salvar_premissas(
    sessao: Session,
    ativo_id: int,
    valores: dict[str, Decimal | None],
    investidores: Sequence[int] | None,
) -> dict:
    if sessao.get(Ativo, ativo_id) is None:
        raise LookupError(f"Ativo {ativo_id} não encontrado")
    registro = sessao.scalar(select(ValuationPremissa).where(ValuationPremissa.ativo_id == ativo_id))
    if registro is None:
        registro = ValuationPremissa(ativo_id=ativo_id)
        sessao.add(registro)
    for campo in _CAMPOS_PREMISSAS:
        setattr(registro, campo, valores[campo])
    sessao.commit()
    return _consultar(sessao, ativo_id, investidores)
