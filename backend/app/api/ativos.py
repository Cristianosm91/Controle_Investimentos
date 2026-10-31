from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError

from ..models import Ativo, Operacao, Provento
from ..schemas import AtivoIn, AtivoOut, CotaOut, SaldoManualIn
from ..services import renda_fixa
from .deps import SessaoDep, obter_ou_404

router = APIRouter(prefix="/ativos", tags=["ativos"])


@router.get("", response_model=list[AtivoOut])
def listar_ativos(
    sessao: SessaoDep,
    busca: Annotated[str | None, Query(max_length=40)] = None,
    personalizados: bool = False,
):
    consulta = select(Ativo).order_by(Ativo.ticker)
    if busca:
        termo = f"%{busca.strip()}%"
        consulta = consulta.where(Ativo.ticker.ilike(termo) | Ativo.nome.ilike(termo))
    if personalizados:
        consulta = consulta.where(~Ativo.cotacao_automatica)
    return sessao.scalars(consulta).all()


@router.post("", response_model=AtivoOut, status_code=201)
def criar_ativo(dados: AtivoIn, sessao: SessaoDep):
    obj = Ativo(**dados.model_dump())
    sessao.add(obj)
    try:
        sessao.commit()
    except IntegrityError:
        sessao.rollback()
        raise HTTPException(409, f"Ativo {dados.ticker} já cadastrado") from None
    sessao.refresh(obj)
    renda_fixa.atualizar(sessao, [obj])
    return obj


@router.put("/{id_}", response_model=AtivoOut)
def alterar_ativo(id_: int, dados: AtivoIn, sessao: SessaoDep):
    obj = obter_ou_404(sessao, Ativo, id_)
    if obj.coingecko_id is not None and (
        dados.classe != "CRIPTO"
        or ("coingecko_id" in dados.model_fields_set and dados.coingecko_id != obj.coingecko_id)
    ):
        raise HTTPException(409, "Não altere a identidade de uma cripto vinculada; cadastre um ativo distinto")
    era_calculado = renda_fixa.calculado(obj)
    campos = dados.model_dump()
    # Formulários que não editam estes campos não os apagam.
    for campo in ("cnpj", "data_vencimento", "isento_ir"):
        if campo not in dados.model_fields_set:
            campos.pop(campo)
    if "coingecko_id" not in dados.model_fields_set and dados.classe == "CRIPTO":
        campos.pop("coingecko_id")
    for campo, valor in campos.items():
        setattr(obj, campo, valor)
    try:
        sessao.commit()
    except IntegrityError:
        sessao.rollback()
        raise HTTPException(409, f"Ativo {dados.ticker} já cadastrado") from None
    if era_calculado and not renda_fixa.calculado(obj):
        renda_fixa.remover_calculadas(sessao, obj)
    renda_fixa.atualizar(sessao, [obj])
    return obj


@router.get("/{id_}/cota", response_model=CotaOut)
def cota(id_: int, data: date, sessao: SessaoDep):
    """Valor da cota de um ativo personalizado na data (preço das aplicações e resgates)."""
    obj = obter_ou_404(sessao, Ativo, id_)
    if obj.cotacao_automatica:
        raise HTTPException(422, f"{obj.ticker} tem cotação automática")
    return CotaOut(ativo_id=obj.id, data=data, cota=renda_fixa.valor_cota(sessao, obj, data))


@router.post("/{id_}/saldo", response_model=CotaOut)
def informar_saldo(id_: int, dados: SaldoManualIn, sessao: SessaoDep):
    obj = obter_ou_404(sessao, Ativo, id_)
    if obj.cotacao_automatica or renda_fixa.calculado(obj):
        raise HTTPException(422, f"{obj.ticker} não é ativo de saldo manual")
    try:
        valor = renda_fixa.informar_saldo(sessao, obj, dados.data, dados.saldo)
    except ValueError as erro:
        raise HTTPException(422, str(erro)) from erro
    return CotaOut(ativo_id=obj.id, data=dados.data, cota=valor)


@router.delete("/{id_}", status_code=204)
def excluir_ativo(id_: int, sessao: SessaoDep):
    obj = obter_ou_404(sessao, Ativo, id_)
    if any(sessao.scalar(select(exists().where(m.ativo_id == id_))) for m in (Operacao, Provento)):
        raise HTTPException(409, "Ativo possui lançamentos e não pode ser excluído")
    sessao.delete(obj)
    sessao.commit()
