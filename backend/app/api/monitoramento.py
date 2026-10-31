from fastapi import APIRouter, HTTPException

from ..schemas import AlertaOut, DesfazerLoteOut, LoteImportacaoOut, VerificacaoOut
from ..services import alertas, lotes, qualidade
from .deps import InvestidoresDep, SessaoDep

router = APIRouter(tags=["monitoramento"])


@router.get("/alertas", response_model=list[AlertaOut])
def listar_alertas(sessao: SessaoDep, investidores: InvestidoresDep):
    return [AlertaOut(**vars(a)) for a in alertas.listar(sessao, investidores)]


@router.get("/qualidade-dados", response_model=list[VerificacaoOut])
def qualidade_dados(sessao: SessaoDep, investidores: InvestidoresDep):
    return [VerificacaoOut(**vars(v)) for v in qualidade.verificar(sessao, investidores)]


@router.get("/lotes", response_model=list[LoteImportacaoOut])
def listar_lotes(sessao: SessaoDep):
    return lotes.listar(sessao)


@router.post("/lotes/{id_}/desfazer", response_model=DesfazerLoteOut)
def desfazer_lote(id_: int, sessao: SessaoDep):
    try:
        return DesfazerLoteOut(**lotes.desfazer(sessao, id_))
    except LookupError as erro:
        raise HTTPException(404, str(erro)) from erro
    except lotes.LoteInvalido as erro:
        raise HTTPException(409, str(erro)) from erro
