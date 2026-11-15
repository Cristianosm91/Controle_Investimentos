import logging
import sqlite3

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.exc import IntegrityError

from ..config import settings
from ..models import (
    Corretora,
    CorretoraApelido,
    DarfPago,
    Grupo,
    Investidor,
    LoteImportacao,
    Meta,
    MovCaixa,
    Operacao,
    PrejuizoInicial,
    Provento,
)
from ..schemas import (
    CorretoraIn,
    CorretoraOut,
    CorretoraUniaoIn,
    ExclusaoInvestidorOut,
    ExclusaoInvestidorResumoOut,
    GrupoIn,
    GrupoOut,
    InvestidorIn,
    InvestidorOut,
    InvestidorRefOut,
)
from ..services import backup, corretoras, jobs
from .deps import SessaoDep, obter_ou_404

log = logging.getLogger(__name__)

router = APIRouter(tags=["cadastros"])


def _investidor_out(i: Investidor) -> InvestidorOut:
    mascara = f"***.{i.cpf[3:6]}.{i.cpf[6:9]}-**" if i.cpf else None
    return InvestidorOut(id=i.id, nome=i.nome, cpf_mascarado=mascara, grupo_id=i.grupo_id, cor=i.cor, ativo=i.ativo)


def _salvar(sessao, obj, msg_duplicado: str):
    try:
        sessao.commit()
    except IntegrityError:
        sessao.rollback()
        raise HTTPException(409, msg_duplicado) from None
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


# ---------- Exclusão completa de investidor (com backup obrigatório) ----------

MOTIVO_BACKUP_EXCLUSAO = "antes-exclusao-investidor"
_DADOS_DO_INVESTIDOR = (
    ("Operações", Operacao),
    ("Proventos", Provento),
    ("Movimentações de caixa", MovCaixa),
    ("DARFs pagos", DarfPago),
    ("Prejuízos a compensar", PrejuizoInicial),
)
_METAS = "Metas só deste investidor"
_LOTES = "Lotes de importação"


def _ids_meta(meta: Meta) -> set[int]:
    return {int(i) for i in (meta.investidores or "").split(",") if i.strip()}


def _metas_do_investidor(sessao, id_: int) -> tuple[list[Meta], list[Meta]]:
    """(metas só dele, metas compartilhadas); metas sem investidores valem para todos e ficam intactas."""
    exclusivas, compartilhadas = [], []
    for meta in sessao.scalars(select(Meta).where(Meta.investidores.is_not(None))):
        ids = _ids_meta(meta)
        if id_ in ids:
            (exclusivas if ids == {id_} else compartilhadas).append(meta)
    return exclusivas, compartilhadas


def _lotes_exclusivos(sessao, id_: int) -> list[int]:
    """Lotes do investidor sem lançamentos de outros; lotes mistos ficam (só perdem o vínculo com ele)."""
    lotes = sessao.scalars(select(LoteImportacao.id).where(LoteImportacao.investidor_id == id_)).all()
    return [
        lote
        for lote in lotes
        if not any(
            sessao.scalar(select(exists().where(modelo.lote_id == lote, modelo.investidor_id != id_)))
            for modelo in (Operacao, Provento, MovCaixa)
        )
    ]


def _ajustar_metas(sessao, id_: int) -> int:
    exclusivas, compartilhadas = _metas_do_investidor(sessao, id_)
    for meta in exclusivas:
        sessao.delete(meta)
    for meta in compartilhadas:
        meta.investidores = ",".join(str(i) for i in sorted(_ids_meta(meta) - {id_}))
    return len(exclusivas)


def _contagens_investidor(sessao, id_: int) -> dict[str, int]:
    contagens = {
        rotulo: sessao.scalar(select(func.count()).select_from(modelo).where(modelo.investidor_id == id_))
        for rotulo, modelo in _DADOS_DO_INVESTIDOR
    }
    contagens[_METAS] = len(_metas_do_investidor(sessao, id_)[0])
    contagens[_LOTES] = len(_lotes_exclusivos(sessao, id_))
    return contagens


def _excluir_dados_investidor(sessao, id_: int) -> dict[str, int]:
    """Apaga o investidor e tudo vinculado a ele, sem commit; ativos, corretoras e grupos são compartilhados."""
    sem_sync = {"synchronize_session": False}
    lotes = _lotes_exclusivos(sessao, id_)
    operacoes = select(Operacao.id).where(Operacao.investidor_id == id_)
    # A perna de outro investidor numa transferência entre investidores perde só o pareamento.
    sessao.execute(
        update(Operacao).where(Operacao.transferencia_pareada_id.in_(operacoes)).values(transferencia_pareada_id=None),
        execution_options=sem_sync,
    )
    removidos = {
        rotulo: sessao.execute(delete(modelo).where(modelo.investidor_id == id_), execution_options=sem_sync).rowcount
        for rotulo, modelo in _DADOS_DO_INVESTIDOR
    }
    removidos[_METAS] = _ajustar_metas(sessao, id_)
    if lotes:
        sessao.execute(delete(LoteImportacao).where(LoteImportacao.id.in_(lotes)), execution_options=sem_sync)
    sessao.execute(
        update(LoteImportacao).where(LoteImportacao.investidor_id == id_).values(investidor_id=None),
        execution_options=sem_sync,
    )
    removidos[_LOTES] = len(lotes)
    sessao.execute(delete(Investidor).where(Investidor.id == id_), execution_options=sem_sync)
    return removidos


def _backup_disponivel() -> bool:
    return jobs.usa_sqlite() and settings.db_path.is_file()


@router.get("/investidores/{id_}/exclusao", response_model=ExclusaoInvestidorResumoOut)
def resumo_exclusao_investidor(id_: int, sessao: SessaoDep):
    obj = obter_ou_404(sessao, Investidor, id_)
    return ExclusaoInvestidorResumoOut(
        investidor=InvestidorRefOut(id=obj.id, nome=obj.nome),
        contagens=_contagens_investidor(sessao, id_),
        backup_disponivel=_backup_disponivel(),
    )


@router.delete("/investidores/{id_}/completo", response_model=ExclusaoInvestidorOut)
def excluir_investidor_completo(id_: int, sessao: SessaoDep):
    obter_ou_404(sessao, Investidor, id_)
    if not _backup_disponivel():
        raise HTTPException(
            409,
            "A exclusão completa exige um backup local antes, indisponível com o banco em servidor. Nada foi excluído.",
        )
    try:
        arquivo = backup.gerar(settings.db_path, "manual", motivo=MOTIVO_BACKUP_EXCLUSAO)
    except (OSError, sqlite3.Error, backup.BackupInvalido) as erro:
        log.exception("Backup antes da exclusão do investidor %s falhou", id_)
        raise HTTPException(409, f"Não foi possível gerar o backup antes da exclusão ({erro}). Nada foi excluído.") from erro
    try:
        removidos = _excluir_dados_investidor(sessao, id_)
        sessao.commit()
    except Exception as erro:
        sessao.rollback()
        log.exception("Exclusão completa do investidor %s falhou e foi desfeita", id_)
        raise HTTPException(500, f"Falha ao excluir o investidor; nada foi excluído (backup {arquivo.name}).") from erro
    log.info("Investidor %s excluído com todos os dados; backup prévio %s", id_, arquivo.name)
    return ExclusaoInvestidorOut(backup=arquivo.name, removidos=removidos)


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
    for apelido in sessao.scalars(select(CorretoraApelido)):
        if corretoras.normalizar(apelido.nome) == corretoras.normalizar(dados.nome):
            raise HTTPException(409, f"Este nome é um apelido da corretora {apelido.corretora.nome}")
    obj = Corretora(**dados.model_dump())
    sessao.add(obj)
    return _salvar(sessao, obj, "Já existe corretora com esse nome")


@router.put("/corretoras/{id_}", response_model=CorretoraOut)
def alterar_corretora(id_: int, dados: CorretoraIn, sessao: SessaoDep):
    obj = obter_ou_404(sessao, Corretora, id_)
    apelidos = list(sessao.scalars(select(CorretoraApelido)))
    for apelido in apelidos:
        if apelido.corretora_id != id_ and corretoras.normalizar(apelido.nome) == corretoras.normalizar(dados.nome):
            raise HTTPException(409, f"Este nome é um apelido da corretora {apelido.corretora.nome}")
    if corretoras.normalizar(obj.nome) != corretoras.normalizar(dados.nome):
        anterior = next((apelido for apelido in apelidos if apelido.nome == obj.nome), None)
        if anterior and anterior.corretora_id != id_:
            raise HTTPException(409, "O nome anterior é um apelido de outra corretora; revise os cadastros.")
        if not anterior:
            sessao.add(CorretoraApelido(nome=obj.nome, corretora_id=id_))
    obj.nome = dados.nome
    obj.cnpj = dados.cnpj
    return _salvar(sessao, obj, "Já existe corretora com esse nome")


@router.post("/corretoras/{id_}/unir", response_model=CorretoraOut)
def unir_corretora(id_: int, dados: CorretoraUniaoIn, sessao: SessaoDep):
    if id_ == dados.destino_id:
        raise HTTPException(422, "Escolha uma corretora de destino diferente")
    origem = obter_ou_404(sessao, Corretora, id_)
    destino = obter_ou_404(sessao, Corretora, dados.destino_id)
    if origem.cnpj and destino.cnpj and origem.cnpj != destino.cnpj:
        raise HTTPException(409, "As corretoras têm CNPJs diferentes. Corrija os cadastros antes de unir.")
    apelido_existente = sessao.scalar(select(CorretoraApelido).where(CorretoraApelido.nome == origem.nome))
    if apelido_existente and apelido_existente.corretora_id not in (origem.id, destino.id):
        raise HTTPException(409, "O nome da corretora de origem é um apelido de outra corretora.")
    if not destino.cnpj:
        destino.cnpj = origem.cnpj
    for modelo in (Operacao, Provento, MovCaixa):
        sessao.execute(update(modelo).where(modelo.corretora_id == origem.id).values(corretora_id=destino.id))
    sessao.execute(
        update(CorretoraApelido).where(CorretoraApelido.corretora_id == origem.id).values(corretora_id=destino.id)
    )
    if not apelido_existente:
        sessao.add(CorretoraApelido(nome=origem.nome, corretora_id=destino.id))
    try:
        sessao.flush()
        sessao.delete(origem)
        sessao.commit()
    except IntegrityError:
        sessao.rollback()
        raise HTTPException(409, "Não foi possível unir as corretoras por conflito de cadastro") from None
    sessao.refresh(destino)
    return destino
