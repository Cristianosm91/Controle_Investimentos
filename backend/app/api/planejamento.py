from datetime import date

from fastapi import APIRouter

from ..models import Meta
from ..schemas import (
    AgendaProventosOut,
    AtivoProjecaoOut,
    ExposicaoCorretoraOut,
    ItemRendaFixaOut,
    MesProjecaoOut,
    MetaIn,
    MetaOut,
    PontoMetaOut,
    ProventoAgendaOut,
    RendaFixaOut,
)
from ..services import agenda_proventos, exposicao, metas, renda_fixa_liquida
from .deps import InvestidoresDep, SessaoDep, obter_ou_404

router = APIRouter(tags=["planejamento"])


# ---------- Renda fixa ----------

@router.get("/renda-fixa", response_model=RendaFixaOut)
def renda_fixa(sessao: SessaoDep, investidores: InvestidoresDep):
    itens = renda_fixa_liquida.listar(sessao, investidores)
    saida = [
        ItemRendaFixaOut(
            investidor_id=i.investidor_id, ativo_id=i.ativo.id, ticker=i.ativo.ticker, nome=i.ativo.nome,
            classe=i.ativo.classe, moeda=i.ativo.moeda, descricao=i.descricao, isento_ir=i.ativo.isento_ir,
            data_vencimento=i.ativo.data_vencimento, dias_para_vencer=i.dias_para_vencer, quantidade=i.quantidade,
            custo=i.custo, bruto=i.atual.bruto, iof=i.atual.iof, ir=i.atual.ir, liquido=i.atual.liquido,
            aliquota_ir=i.aliquota_ir,
            bruto_vencimento=i.vencimento.bruto if i.vencimento else None,
            liquido_vencimento=i.vencimento.liquido if i.vencimento else None,
        )
        for i in itens
    ]
    return RendaFixaOut(
        itens=saida,
        custo=sum(i.custo for i in itens),
        bruto=sum(i.atual.bruto for i in itens),
        impostos=sum(i.atual.iof + i.atual.ir for i in itens),
        liquido=sum(i.atual.liquido for i in itens),
        liquido_vencimento=sum(i.vencimento.liquido for i in itens if i.vencimento) if any(i.vencimento for i in itens) else None,
    )


# ---------- Agenda e projeção de proventos ----------

@router.get("/proventos/agenda", response_model=AgendaProventosOut)
def agenda(sessao: SessaoDep, investidores: InvestidoresDep):
    a = agenda_proventos.calcular(sessao, investidores)
    custo = sum(p.custo for p in a.por_ativo)
    return AgendaProventosOut(
        a_receber=[ProventoAgendaOut(**vars(i)) for i in a.a_receber],
        total_a_receber=a.total_a_receber,
        meses=[MesProjecaoOut(mes=m, confirmado=c, estimado=e) for m, c, e in a.meses],
        por_ativo=[
            AtivoProjecaoOut(
                ativo_id=p.ativo_id, ticker=p.ticker, classe=p.classe, confirmado=p.confirmado, estimado=p.estimado,
                total=p.total, yoc=p.yoc,
            )
            for p in a.por_ativo
        ],
        total_12m=a.total_12m,
        media_mensal=a.total_12m / 12,
        yoc_projetado=sum(p.total for p in a.por_ativo) / custo if custo else None,
    )


# ---------- Exposição ----------

@router.get("/exposicao/corretoras", response_model=list[ExposicaoCorretoraOut])
def exposicao_corretoras(sessao: SessaoDep, investidores: InvestidoresDep):
    return [ExposicaoCorretoraOut(**vars(e)) for e in exposicao.por_corretora(sessao, investidores)]


# ---------- Metas ----------

def _meta_out(p: metas.Projecao) -> MetaOut:
    m = p.meta
    return MetaOut(
        id=m.id, nome=m.nome, tipo=m.tipo, valor_alvo=m.valor_alvo, data_alvo=m.data_alvo,
        aporte_mensal=m.aporte_mensal, rentabilidade_aa=m.rentabilidade_aa, rendimento_aa=m.rendimento_aa,
        investidores=metas.ids(m), valor_atual=p.valor_atual, progresso=p.progresso,
        meses_restantes=p.meses_restantes, projetado_pessimista=p.projetado[0], projetado_base=p.projetado[1],
        projetado_otimista=p.projetado[2], atinge=p.atinge, data_estimada=p.data_estimada,
        aporte_necessario=p.aporte_necessario, rendimento_usado=p.rendimento_usado,
        serie=[PontoMetaOut(mes=d, pessimista=a, base=b, otimista=c) for d, a, b, c in p.serie],
    )


def _gravar(obj: Meta, dados: MetaIn) -> None:
    for campo, valor in dados.model_dump(exclude={"investidores"}).items():
        setattr(obj, campo, valor)
    obj.investidores = ",".join(str(i) for i in sorted(set(dados.investidores))) if dados.investidores else None


def _projetar(sessao, obj: Meta) -> MetaOut:
    hoje = date.today()
    return _meta_out(metas.calcular(obj, metas.situacao(sessao, metas.ids(obj), hoje), hoje))


@router.get("/metas", response_model=list[MetaOut])
def listar_metas(sessao: SessaoDep):
    return [_meta_out(p) for p in metas.listar(sessao)]


@router.post("/metas", response_model=MetaOut, status_code=201)
def criar_meta(dados: MetaIn, sessao: SessaoDep):
    obj = Meta()
    _gravar(obj, dados)
    sessao.add(obj)
    sessao.commit()
    return _projetar(sessao, obj)


@router.put("/metas/{id_}", response_model=MetaOut)
def alterar_meta(id_: int, dados: MetaIn, sessao: SessaoDep):
    obj = obter_ou_404(sessao, Meta, id_)
    _gravar(obj, dados)
    sessao.commit()
    return _projetar(sessao, obj)


@router.delete("/metas/{id_}", status_code=204)
def excluir_meta(id_: int, sessao: SessaoDep):
    sessao.delete(obter_ou_404(sessao, Meta, id_))
    sessao.commit()


@router.get("/metas/{id_}", response_model=MetaOut)
def obter_meta(id_: int, sessao: SessaoDep):
    return _projetar(sessao, obter_ou_404(sessao, Meta, id_))
