from fastapi import APIRouter, HTTPException
from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError

from ..models import Corretora, DarfPago, Grupo, Investidor, MovCaixa, Operacao, Provento
from ..schemas import CorretoraIn, CorretoraOut, GrupoIn, GrupoOut, InvestidorIn, InvestidorOut
from .deps import SessaoDep, obter_ou_404

router = APIRouter(tags=["cadastros"])


def _investidor_out(i: Investidor) -> InvestidorOut:
    mascara = f"***.{i.cpf[3:6]}.{i.cpf[6:9]}-**" if i.cpf else None
    return InvestidorOut(id=i.id, nome=i.nome, cpf_mascarado=mascara, grupo_id=i.grupo_id, cor=i.cor, ativo=i.ativo)


def _salvar(sessao, obj, msg_duplicado: str):
    try:
        sessao.commit()
    except IntegrityError:
        sessao.rollback()
        raise HTTPException(409, msg_duplicado)
    sessao.refresh(obj)
    return obj


# ---------- Investidores ----------

@router.get("/investidores", response_model=list[InvestidorOut])
def listar_investidores(sessao: SessaoDep):
    return [_investidor_out(i) for i in sessao.scalars(select(Investidor).order_by(Investidor.nome))]


@router.post("/investidores", response_model=InvestidorOut, status_code=201)
def criar_investidor(dados: InvestidorIn, sessao: SessaoDep):
    obj = Investidor(**dados.model_dump())
    sessao.add(obj)
    return _investidor_out(_salvar(sessao, obj, "Já existe investidor com esse nome"))


@router.put("/investidores/{id_}", response_model=InvestidorOut)
def alterar_investidor(id_: int, dados: InvestidorIn, sessao: SessaoDep):
    obj = obter_ou_404(sessao, Investidor, id_)
    novos = dados.model_dump()
    if dados.cpf is None:
        novos.pop("cpf")  # front nunca recebe o CPF completo; ausente = manter
    for campo, valor in novos.items():
        setattr(obj, campo, valor)
    return _investidor_out(_salvar(sessao, obj, "Já existe investidor com esse nome"))


@router.delete("/investidores/{id_}", status_code=204)
def excluir_investidor(id_: int, sessao: SessaoDep):
    obj = obter_ou_404(sessao, Investidor, id_)
    em_uso = any(
        sessao.scalar(select(exists().where(modelo.investidor_id == id_)))
        for modelo in (Operacao, Provento, MovCaixa, DarfPago)
    )
    if em_uso:
        raise HTTPException(409, "Investidor possui lançamentos; desative-o em vez de excluir")
    sessao.delete(obj)
    sessao.commit()


# ---------- Grupos ----------

@router.get("/grupos", response_model=list[GrupoOut])
def listar_grupos(sessao: SessaoDep):
    return sessao.scalars(select(Grupo).order_by(Grupo.nome)).all()


@router.post("/grupos", response_model=GrupoOut, status_code=201)
def criar_grupo(dados: GrupoIn, sessao: SessaoDep):
    obj = Grupo(**dados.model_dump())
    sessao.add(obj)
    return _salvar(sessao, obj, "Já existe grupo com esse nome")


@router.delete("/grupos/{id_}", status_code=204)
def excluir_grupo(id_: int, sessao: SessaoDep):
    sessao.delete(obter_ou_404(sessao, Grupo, id_))
    sessao.commit()


# ---------- Corretoras ----------

@router.get("/corretoras", response_model=list[CorretoraOut])
def listar_corretoras(sessao: SessaoDep):
    return sessao.scalars(select(Corretora).order_by(Corretora.nome)).all()


@router.post("/corretoras", response_model=CorretoraOut, status_code=201)
def criar_corretora(dados: CorretoraIn, sessao: SessaoDep):
    obj = Corretora(**dados.model_dump())
    sessao.add(obj)
    return _salvar(sessao, obj, "Já existe corretora com esse nome")
