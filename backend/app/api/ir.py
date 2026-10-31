from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import Response
from sqlalchemy import delete, select

from ..models import DarfPago, Investidor, PrejuizoInicial, RegraFiscal
from ..schemas import (
    ApuracaoIROut,
    DarfPagoIn,
    DarfPagoOut,
    DirpfOut,
    MesIROut,
    PrejuizoInicialIO,
    RegraFiscalIn,
    RegraFiscalOut,
)
from ..services import dirpf, ir
from .deps import SessaoDep, obter_ou_404

router = APIRouter(prefix="/ir", tags=["imposto de renda"])

# IR é sempre por CPF: os endpoints exigem um único investidor.
InvestidorIR = Annotated[int, Query(description="ID do investidor (IR é por CPF)")]
Ano = Annotated[int, Query(ge=1990, le=2100)]


def _mes_out(m: ir.MesIR) -> MesIROut:
    return MesIROut(**asdict(m), saldo=m.saldo)


# ---------- Regras fiscais ----------

@router.get("/regras", response_model=list[RegraFiscalOut])
def listar_regras(sessao: SessaoDep):
    return sessao.scalars(select(RegraFiscal).order_by(RegraFiscal.categoria, RegraFiscal.vigencia_inicio)).all()


@router.post("/regras", response_model=RegraFiscalOut, status_code=201)
def criar_regra(dados: RegraFiscalIn, sessao: SessaoDep):
    obj = RegraFiscal(**dados.model_dump())
    sessao.add(obj)
    sessao.commit()
    return obj


@router.put("/regras/{id_}", response_model=RegraFiscalOut)
def alterar_regra(id_: int, dados: RegraFiscalIn, sessao: SessaoDep):
    obj = obter_ou_404(sessao, RegraFiscal, id_)
    for campo, valor in dados.model_dump().items():
        setattr(obj, campo, valor)
    sessao.commit()
    return obj


@router.delete("/regras/{id_}", status_code=204)
def excluir_regra(id_: int, sessao: SessaoDep):
    sessao.delete(obter_ou_404(sessao, RegraFiscal, id_))
    sessao.commit()


# ---------- Prejuízo trazido de antes do início da apuração ----------

@router.get("/prejuizos-iniciais", response_model=list[PrejuizoInicialIO])
def listar_prejuizos(investidor: InvestidorIR, sessao: SessaoDep):
    obter_ou_404(sessao, Investidor, investidor)
    return [PrejuizoInicialIO(grupo=g, valor=v) for g, v in ir.carregar_prejuizos(sessao, investidor).items()]


@router.put("/prejuizos-iniciais", response_model=list[PrejuizoInicialIO])
def salvar_prejuizos(investidor: InvestidorIR, dados: list[PrejuizoInicialIO], sessao: SessaoDep):
    obter_ou_404(sessao, Investidor, investidor)
    sessao.execute(delete(PrejuizoInicial).where(PrejuizoInicial.investidor_id == investidor))
    sessao.add_all(PrejuizoInicial(investidor_id=investidor, grupo=d.grupo, valor=d.valor) for d in dados if d.valor)
    sessao.commit()
    return listar_prejuizos(investidor, sessao)


# ---------- Apuração ----------

@router.get("/apuracao", response_model=ApuracaoIROut)
def apuracao(investidor: InvestidorIR, sessao: SessaoDep, ano: Ano | None = None):
    obter_ou_404(sessao, Investidor, investidor)
    r = ir.apurar(sessao, investidor)
    anos = sorted({m.competencia.year for m in r.meses} | {e.ano for e in r.exterior}, reverse=True)
    meses = [m for m in r.meses if ano is None or m.competencia.year == ano]
    return ApuracaoIROut(
        anos=anos,
        meses=[_mes_out(m) for m in meses],
        exterior=[asdict(e) for e in r.exterior],
        nao_apurados=r.nao_apurados,
    )


# ---------- DARFs pagos ----------

@router.get("/darfs", response_model=list[DarfPagoOut])
def listar_darfs(investidor: InvestidorIR, sessao: SessaoDep):
    consulta = select(DarfPago).where(DarfPago.investidor_id == investidor)
    return sessao.scalars(consulta.order_by(DarfPago.competencia.desc(), DarfPago.id.desc())).all()


@router.post("/darfs", response_model=DarfPagoOut, status_code=201)
def registrar_darf(dados: DarfPagoIn, sessao: SessaoDep):
    obter_ou_404(sessao, Investidor, dados.investidor_id)
    obj = DarfPago(**dados.model_dump())
    sessao.add(obj)
    sessao.commit()
    return obj


@router.put("/darfs/{id_}", response_model=DarfPagoOut)
def alterar_darf(id_: int, dados: DarfPagoIn, sessao: SessaoDep):
    obj = obter_ou_404(sessao, DarfPago, id_)
    obter_ou_404(sessao, Investidor, dados.investidor_id)
    for campo, valor in dados.model_dump().items():
        setattr(obj, campo, valor)
    sessao.commit()
    return obj


@router.delete("/darfs/{id_}", status_code=204)
def excluir_darf(id_: int, sessao: SessaoDep):
    sessao.delete(obter_ou_404(sessao, DarfPago, id_))
    sessao.commit()


# ---------- DIRPF ----------

@router.get("/dirpf", response_model=DirpfOut)
def relatorio_dirpf(investidor: InvestidorIR, ano: Ano, sessao: SessaoDep):
    obter_ou_404(sessao, Investidor, investidor)
    r = dirpf.gerar(sessao, investidor, ano)
    return DirpfOut(**{**asdict(r), "meses": [_mes_out(m) for m in r.meses]})


@router.get("/dirpf.csv")
def exportar_dirpf(investidor: InvestidorIR, ano: Ano, sessao: SessaoDep):
    inv = obter_ou_404(sessao, Investidor, investidor)
    conteudo = dirpf.para_csv(dirpf.gerar(sessao, investidor, ano))
    nome = f"dirpf-{ano}-{inv.id}.csv"
    # BOM: o Excel reconhece UTF-8 e mostra os acentos.
    return Response(
        "\ufeff" + conteudo, media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
