"""Filtros compartilhados para classificar e selecionar ativos."""

from collections.abc import Sequence

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from ..models import Ativo, Operacao, Provento

MERCADOS = ("BRASIL", "EUA", "CRIPTO")
_BOLSAS_BRASIL = frozenset({"B3", "BVMF"})
_BOLSAS_EUA = frozenset({"BATS", "NASDAQ", "NYSE", "NYSEAMERICAN", "NYSEARCA"})


def classificar_mercado(ativo: Ativo) -> str | None:
    if ativo.classe.strip().upper() == "CRIPTO" or ativo.coingecko_id:
        return "CRIPTO"
    mercado = (ativo.mercado or "").strip().upper()
    if mercado in _BOLSAS_BRASIL:
        return "BRASIL"
    if mercado in _BOLSAS_EUA:
        return "EUA"
    return None


_NENHUM = "__NENHUM__"


def _lista_csv(valor: str | None, nome: str) -> list[str] | None:
    if valor is None or not valor.strip():
        return None
    if valor.strip() == _NENHUM:
        return []
    itens = [item.strip() for item in valor.split(",") if item.strip()]
    return itens


def parsear_ids_ativos(valor: str | None) -> list[int] | None:
    if valor is None or not valor.strip():
        return None
    if valor.strip() == _NENHUM:
        return []
    try:
        ids = [int(item) for item in (_lista_csv(valor, "ativo_ids") or [])]
    except ValueError as erro:
        raise ValueError("Parâmetro 'ativo_ids' deve conter IDs numéricos separados por vírgula") from erro
    if any(id_ <= 0 for id_ in ids):
        raise ValueError("IDs de ativos devem ser positivos")
    return list(dict.fromkeys(ids))


def ids_filtrados(
    sessao: Session,
    mercados: str | None = None,
    classes: str | None = None,
    ativo_ids: str | None = None,
) -> list[int] | None:
    mercados_lista = _lista_csv(mercados, "mercados")
    mercados_selecionados = {item.upper() for item in mercados_lista or []}
    invalidos = mercados_selecionados - set(MERCADOS)
    if invalidos:
        raise ValueError(f"Mercados inválidos: {', '.join(sorted(invalidos))}")
    classes_lista = _lista_csv(classes, "classes")
    classes_selecionadas = {item.upper() for item in classes_lista or []}
    ids_lista = parsear_ids_ativos(ativo_ids)
    ids_selecionados = set(ids_lista or [])
    if mercados_lista is None and classes_lista is None and ids_lista is None:
        return None

    ativos = sessao.scalars(select(Ativo)).all()
    return [
        ativo.id
        for ativo in ativos
        if (mercados_lista is None or classificar_mercado(ativo) in mercados_selecionados)
        and (classes_lista is None or ativo.classe.upper() in classes_selecionadas)
        and (ids_lista is None or ativo.id in ids_selecionados)
    ]


def ativos_disponiveis(
    sessao: Session,
    investidores: Sequence[int] | None,
    mercados: str | None = None,
    classes: str | None = None,
) -> list[Ativo]:
    consulta = select(Ativo).order_by(Ativo.ticker)
    if investidores:
        operacoes = exists(
            select(Operacao.id).where(
                Operacao.ativo_id == Ativo.id,
                Operacao.investidor_id.in_(investidores),
            )
        )
        proventos = exists(
            select(Provento.id).where(
                Provento.ativo_id == Ativo.id,
                Provento.investidor_id.in_(investidores),
            )
        )
        consulta = consulta.where(operacoes | proventos)

    mercado_lista = _lista_csv(mercados, "mercados")
    mercado_set = {item.upper() for item in mercado_lista or []}
    invalidos = mercado_set - set(MERCADOS)
    if invalidos:
        raise ValueError(f"Mercados inválidos: {', '.join(sorted(invalidos))}")
    classes_lista = _lista_csv(classes, "classes")
    classes_set = {item.upper() for item in classes_lista or []}
    return [
        ativo
        for ativo in sessao.scalars(consulta)
        if (mercado_lista is None or classificar_mercado(ativo) in mercado_set)
        and (classes_lista is None or ativo.classe.upper() in classes_set)
    ]
