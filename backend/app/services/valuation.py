"""Modelos de preço justo e rentabilidade mensal por ativo."""

import logging
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal

import httpx
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Ativo, Cotacao, Fundamento, ValuationHistorico, ValuationPremissa
from ..providers.base import ProvedorCotacao
from . import cotacoes, fundamentos
from . import rentabilidade as r

log = logging.getLogger(__name__)

ZERO = Decimal(0)
UM = Decimal(1)
# Último cálculo + os 2 anteriores.
CALCULOS_MANTIDOS = 3
_MODELOS_HISTORICO = ("graham", "bazin", "dcf_fcfe", "gordon", "pl_historico", "pl_setor", "pvp_justificado")
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
    sessao.flush()
    resultado = _consultar(sessao, ativo_id, investidores)
    _registrar_historico(sessao, resultado)
    sessao.commit()
    return resultado


def _registrar_historico(sessao: Session, resultado: dict) -> None:
    ativo_id = resultado["ativo_id"]
    precos = {modelo["id"]: modelo["preco_justo"] for modelo in resultado["modelos"]}
    sessao.add(
        ValuationHistorico(
            ativo_id=ativo_id,
            calculado_em=datetime.now().replace(microsecond=0),
            cotacao=resultado["cotacao"],
            preco_mediano=resultado["analise"]["preco_mediano"],
            modelos_disponiveis=resultado["analise"]["modelos_disponiveis"],
            **{campo: precos.get(campo) for campo in _MODELOS_HISTORICO},
        )
    )
    sessao.flush()
    excedentes = sessao.scalars(
        select(ValuationHistorico.id)
        .where(ValuationHistorico.ativo_id == ativo_id)
        .order_by(ValuationHistorico.calculado_em.desc(), ValuationHistorico.id.desc())
        .offset(CALCULOS_MANTIDOS)
    ).all()
    if excedentes:
        sessao.execute(delete(ValuationHistorico).where(ValuationHistorico.id.in_(excedentes)))


def _upside(preco_justo: Decimal | None, cotacao: Decimal | None) -> Decimal | None:
    if preco_justo is None or cotacao is None or cotacao <= 0:
        return None
    return preco_justo / cotacao - UM


def historico(sessao: Session) -> list[dict]:
    """Ativos com valuation calculado: último cálculo e os anteriores mantidos, do mais recente ao mais antigo."""
    registros = sessao.scalars(
        select(ValuationHistorico).order_by(
            ValuationHistorico.ativo_id, ValuationHistorico.calculado_em.desc(), ValuationHistorico.id.desc()
        )
    ).all()
    por_ativo: dict[int, list[ValuationHistorico]] = {}
    for registro in registros:
        por_ativo.setdefault(registro.ativo_id, []).append(registro)
    if not por_ativo:
        return []

    ativos = {a.id: a for a in sessao.scalars(select(Ativo).where(Ativo.id.in_(por_ativo)))}
    itens = []
    for ativo_id, calculos in por_ativo.items():
        ativo = ativos[ativo_id]
        cotacao = sessao.scalar(
            select(Cotacao)
            .where(Cotacao.ativo_id == ativo_id)
            .order_by(Cotacao.data.desc(), Cotacao.id.desc())
            .limit(1)
        )
        preco_atual = cotacao.preco if cotacao else None
        ultimo = calculos[0]
        itens.append(
            {
                "ativo_id": ativo.id,
                "ticker": ativo.ticker,
                "nome": ativo.nome,
                "classe": ativo.classe,
                "moeda": ativo.moeda,
                "cotacao": preco_atual,
                "cotacao_data": cotacao.data if cotacao else None,
                "upside_atual": _upside(ultimo.preco_mediano, preco_atual),
                "calculos": [
                    {
                        "calculado_em": calculo.calculado_em,
                        "cotacao": calculo.cotacao,
                        "preco_mediano": calculo.preco_mediano,
                        "upside": _upside(calculo.preco_mediano, calculo.cotacao),
                        "modelos_disponiveis": calculo.modelos_disponiveis,
                        "modelos": {campo: getattr(calculo, campo) for campo in _MODELOS_HISTORICO},
                    }
                    for calculo in calculos[:CALCULOS_MANTIDOS]
                ],
            }
        )
    return sorted(itens, key=lambda item: item["calculos"][0]["calculado_em"], reverse=True)


def remover_historico(sessao: Session, ativo_id: int) -> None:
    sessao.execute(delete(ValuationHistorico).where(ValuationHistorico.ativo_id == ativo_id))
    sessao.commit()


def preparar_ativo(
    sessao: Session,
    ticker: str,
    classe: str,
    provedores: Sequence[ProvedorCotacao] | None = None,
    cliente_fundamentos: httpx.Client | None = None,
) -> dict:
    """Localiza o ticker ou o cadastra como ativo B3; busca cotação e fundamentos quando ainda não há cotação."""
    ativo = sessao.scalar(select(Ativo).where(Ativo.ticker == ticker))
    criado = ativo is None
    if criado:
        ativo = Ativo(ticker=ticker, classe=classe, moeda="BRL", mercado="BVMF", cotacao_automatica=True)
        sessao.add(ativo)
        try:
            sessao.commit()
        except IntegrityError:
            sessao.rollback()
            ativo = sessao.scalar(select(Ativo).where(Ativo.ticker == ticker))
            criado = False
            if ativo is None:
                raise
    avisos: list[str] = []
    sem_cotacao = sessao.scalar(select(Cotacao.id).where(Cotacao.ativo_id == ativo.id).limit(1)) is None
    if ativo.cotacao_automatica and (criado or sem_cotacao):
        try:
            if cotacoes.atualizar_cotacoes(sessao, provedores, [ativo]).sem_cotacao:
                avisos.append(f"Cotação de {ticker} não encontrada")
        except Exception:
            sessao.rollback()
            log.warning("Falha ao buscar cotação de %s", ticker, exc_info=True)
            avisos.append(f"Falha ao buscar a cotação de {ticker}")
        if ativo.mercado == "BVMF":
            try:
                resultado = fundamentos.atualizar(sessao, cliente_fundamentos, ativo_ids=[ativo.id])
                if resultado.sem_dados or resultado.falhas:
                    avisos.append(f"Fundamentos de {ticker} indisponíveis; informe as premissas manualmente")
            except Exception:
                sessao.rollback()
                log.warning("Falha ao buscar fundamentos de %s", ticker, exc_info=True)
                avisos.append(f"Falha ao buscar os fundamentos de {ticker}")
    return {"ativo_id": ativo.id, "ticker": ativo.ticker, "criado": criado, "avisos": avisos}
