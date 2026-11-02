import json
import re
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sqlalchemy import select

from ..models import TratamentoQualidade
from ..schemas import AlertaOut, DesfazerLoteOut, LoteImportacaoOut, VerificacaoOut
from ..services import alertas, lotes, qualidade
from .deps import InvestidoresDep, SessaoDep

router = APIRouter(tags=["monitoramento"])


@router.get("/alertas", response_model=list[AlertaOut])
def listar_alertas(sessao: SessaoDep, investidores: InvestidoresDep):
    return [AlertaOut(**vars(a)) for a in alertas.listar(sessao, investidores)]


@router.get("/qualidade-dados", response_model=list[VerificacaoOut])
def qualidade_dados(
    sessao: SessaoDep,
    investidores: InvestidoresDep,
    historico: bool = False,
):
    verificacoes = qualidade.verificar(sessao, investidores)
    fingerprints_atuais = {v.fingerprint for v in verificacoes}
    tratamentos = {
        tratamento.fingerprint: tratamento
        for tratamento in sessao.scalars(select(TratamentoQualidade)).all()
    }

    resultado = []
    for verificacao in verificacoes:
        tratamento = tratamentos.get(verificacao.fingerprint)
        if tratamento:
            verificacao.status = "tratado"
            verificacao.tratado_em = tratamento.tratado_em
        resultado.append(VerificacaoOut(**vars(verificacao)))

    if historico:
        for tratamento in tratamentos.values():
            if tratamento.fingerprint in fingerprints_atuais:
                continue
            investidores_registro = set(json.loads(tratamento.investidor_ids))
            if investidores and not investidores_registro.intersection(investidores):
                continue
            resultado.append(
                VerificacaoOut(
                    codigo=tratamento.codigo,
                    titulo=tratamento.titulo,
                    severidade=tratamento.severidade,
                    descricao=tratamento.descricao,
                    link=None,
                    itens=json.loads(tratamento.itens),
                    fingerprint=tratamento.fingerprint,
                    operacao_ids=json.loads(tratamento.operacao_ids),
                    provento_ids=json.loads(tratamento.provento_ids),
                    caixa_ids=json.loads(tratamento.caixa_ids),
                    ativo_ids=json.loads(tratamento.ativo_ids),
                    investidor_ids=json.loads(tratamento.investidor_ids),
                    status="resolvido",
                    tratado_em=tratamento.tratado_em,
                )
            )
    return resultado


@router.post(
    "/qualidade-dados/{fingerprint}/tratado",
    response_model=VerificacaoOut,
)
def tratar_apontamento(fingerprint: str, sessao: SessaoDep):
    if not re.fullmatch(r"[a-f0-9]{64}", fingerprint):
        raise HTTPException(404, "Apontamento não encontrado")
    verificacao = next(
        (v for v in qualidade.verificar(sessao) if v.fingerprint == fingerprint),
        None,
    )
    if verificacao is None:
        raise HTTPException(404, "Apontamento não encontrado ou já resolvido")

    tratamento = sessao.get(TratamentoQualidade, fingerprint)
    tratado_em = datetime.now(UTC).isoformat()
    if tratamento is None:
        tratamento = TratamentoQualidade(
            fingerprint=fingerprint,
            codigo=verificacao.codigo,
            titulo=verificacao.titulo,
            severidade=verificacao.severidade,
            descricao=verificacao.descricao,
            itens=json.dumps(verificacao.itens, ensure_ascii=False),
            operacao_ids=json.dumps(verificacao.operacao_ids),
            provento_ids=json.dumps(verificacao.provento_ids),
            caixa_ids=json.dumps(verificacao.caixa_ids),
            ativo_ids=json.dumps(verificacao.ativo_ids),
            investidor_ids=json.dumps(verificacao.investidor_ids),
            tratado_em=tratado_em,
        )
        sessao.add(tratamento)
    else:
        tratamento.tratado_em = tratado_em
    sessao.commit()
    verificacao.status = "tratado"
    verificacao.tratado_em = tratado_em
    return VerificacaoOut(**vars(verificacao))


@router.delete(
    "/qualidade-dados/{fingerprint}/tratado",
    status_code=204,
)
def reabrir_apontamento(fingerprint: str, sessao: SessaoDep):
    if not re.fullmatch(r"[a-f0-9]{64}", fingerprint):
        raise HTTPException(404, "Apontamento não encontrado")
    tratamento = sessao.get(TratamentoQualidade, fingerprint)
    if tratamento is None:
        raise HTTPException(404, "Tratamento não encontrado")
    sessao.delete(tratamento)
    sessao.commit()
    return Response(status_code=204)


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
