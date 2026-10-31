from decimal import Decimal

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..models import Ativo, AtivoBook, Book, Carteira, CarteiraAtivo, ClasseBook, Estrategia
from ..schemas import (
    BookIn,
    BookOut,
    CarteiraIn,
    CarteiraOut,
    EstrategiaIn,
    EstrategiaOut,
    ExcecaoBookIn,
    ExcecaoBookOut,
    ParametrosIO,
)
from ..services import parametros
from .deps import SessaoDep, obter_ou_404

router = APIRouter(tags=["configurações"])


def _gravar(sessao: Session, msg_duplicado: str, flush: bool = False) -> None:
    """Commit (ou só flush, para seguir na mesma transação) traduzindo nome duplicado em 409."""
    try:
        sessao.flush() if flush else sessao.commit()
    except IntegrityError:
        sessao.rollback()
        raise HTTPException(409, msg_duplicado)


# ---------- Estratégias ----------

@router.get("/estrategias", response_model=list[EstrategiaOut])
def listar_estrategias(sessao: SessaoDep):
    return sessao.scalars(select(Estrategia).order_by(Estrategia.ordem, Estrategia.nome)).all()


@router.post("/estrategias", response_model=EstrategiaOut, status_code=201)
def criar_estrategia(dados: EstrategiaIn, sessao: SessaoDep):
    obj = Estrategia(**dados.model_dump())
    sessao.add(obj)
    _gravar(sessao, "Já existe estratégia com esse nome")
    return obj


@router.put("/estrategias/{id_}", response_model=EstrategiaOut)
def alterar_estrategia(id_: int, dados: EstrategiaIn, sessao: SessaoDep):
    obj = obter_ou_404(sessao, Estrategia, id_)
    for campo, valor in dados.model_dump().items():
        setattr(obj, campo, valor)
    _gravar(sessao, "Já existe estratégia com esse nome")
    return obj


@router.delete("/estrategias/{id_}", status_code=204)
def excluir_estrategia(id_: int, sessao: SessaoDep):
    obj = obter_ou_404(sessao, Estrategia, id_)
    if sessao.scalar(select(exists().where(Book.estrategia_id == id_))):
        raise HTTPException(409, "Estratégia possui books; exclua ou mova os books antes")
    sessao.delete(obj)
    sessao.commit()


# ---------- Books ----------

def _book_out(sessao: Session, b: Book) -> BookOut:
    classes = sessao.scalars(select(ClasseBook.classe).where(ClasseBook.book_id == b.id).order_by(ClasseBook.classe))
    return BookOut(id=b.id, estrategia_id=b.estrategia_id, nome=b.nome, peso=b.peso, ordem=b.ordem, classes=list(classes))


def _salvar_book(sessao: Session, obj: Book, dados: BookIn) -> BookOut:
    obter_ou_404(sessao, Estrategia, dados.estrategia_id)
    for campo, valor in dados.model_dump(exclude={"classes"}).items():
        setattr(obj, campo, valor)
    sessao.add(obj)
    _gravar(sessao, "Já existe book com esse nome", flush=True)
    # Classe tem um único book padrão: atribuir aqui retira do book anterior.
    sessao.execute(delete(ClasseBook).where(ClasseBook.book_id == obj.id))
    sessao.execute(delete(ClasseBook).where(ClasseBook.classe.in_(dados.classes)))
    sessao.add_all(ClasseBook(classe=c, book_id=obj.id) for c in dados.classes)
    sessao.commit()
    return _book_out(sessao, obj)


@router.get("/books", response_model=list[BookOut])
def listar_books(sessao: SessaoDep):
    return [_book_out(sessao, b) for b in sessao.scalars(select(Book).order_by(Book.ordem, Book.nome))]


@router.post("/books", response_model=BookOut, status_code=201)
def criar_book(dados: BookIn, sessao: SessaoDep):
    return _salvar_book(sessao, Book(), dados)


@router.put("/books/{id_}", response_model=BookOut)
def alterar_book(id_: int, dados: BookIn, sessao: SessaoDep):
    return _salvar_book(sessao, obter_ou_404(sessao, Book, id_), dados)


@router.delete("/books/{id_}", status_code=204)
def excluir_book(id_: int, sessao: SessaoDep):
    obj = obter_ou_404(sessao, Book, id_)
    # Exceção que usava o book deixaria de somar 100%: o ativo volta ao book da classe.
    afetados = select(AtivoBook.ativo_id).where(AtivoBook.book_id == id_)
    sessao.execute(delete(AtivoBook).where(AtivoBook.ativo_id.in_(afetados)))
    sessao.delete(obj)
    sessao.commit()


@router.get("/classes", response_model=list[str])
def listar_classes(sessao: SessaoDep):
    """Classes em uso nos ativos ou mapeadas em algum book."""
    em_uso = set(sessao.scalars(select(Ativo.classe).distinct()))
    return sorted(em_uso | set(sessao.scalars(select(ClasseBook.classe))))


# ---------- Exceções de book por ativo ----------

@router.get("/books/excecoes", response_model=list[ExcecaoBookOut])
def listar_excecoes(sessao: SessaoDep):
    por_ativo: dict[int, ExcecaoBookOut] = {}
    consulta = select(AtivoBook, Ativo.ticker).join(Ativo, Ativo.id == AtivoBook.ativo_id).order_by(Ativo.ticker)
    for e, ticker in sessao.execute(consulta):
        por_ativo.setdefault(e.ativo_id, ExcecaoBookOut(ativo_id=e.ativo_id, ticker=ticker, books=[])).books.append(
            (e.book_id, e.percentual)
        )
    return list(por_ativo.values())


@router.put("/ativos/{id_}/books", status_code=204)
def definir_excecao(id_: int, dados: list[ExcecaoBookIn], sessao: SessaoDep):
    """Distribui o ativo entre books (soma 100%); lista vazia volta ao book da classe."""
    obter_ou_404(sessao, Ativo, id_)
    for d in dados:
        obter_ou_404(sessao, Book, d.book_id)
    if dados and abs(sum((d.percentual for d in dados), Decimal(0)) - 1) > Decimal("0.0001"):
        raise HTTPException(422, "Os percentuais devem somar 100%")
    if len({d.book_id for d in dados}) != len(dados):
        raise HTTPException(422, "Book repetido")
    sessao.execute(delete(AtivoBook).where(AtivoBook.ativo_id == id_))
    sessao.add_all(AtivoBook(ativo_id=id_, book_id=d.book_id, percentual=d.percentual) for d in dados)
    sessao.commit()


# ---------- Carteiras ----------

def _carteira_out(sessao: Session, c: Carteira) -> CarteiraOut:
    vinculos = sessao.scalars(
        select(CarteiraAtivo)
        .options(joinedload(CarteiraAtivo.ativo))
        .where(CarteiraAtivo.carteira_id == c.id)
    ).all()
    vinculos = sorted(vinculos, key=lambda v: (v.ranking is None, v.ranking or 0, v.ativo.ticker))
    return CarteiraOut(
        id=c.id, nome=c.nome, categoria=c.categoria, ativa=c.ativa, ordem=c.ordem,
        ativos=[
            {
                "ativo_id": v.ativo_id, "ticker": v.ativo.ticker, "peso": v.peso, "preco_teto": v.preco_teto,
                "ranking": v.ranking, "entra_preco_teto": v.entra_preco_teto,
            }
            for v in vinculos
        ],
    )


def _salvar_carteira(sessao: Session, obj: Carteira, dados: CarteiraIn) -> CarteiraOut:
    ids = [a.ativo_id for a in dados.ativos]
    existentes = set(sessao.scalars(select(Ativo.id).where(Ativo.id.in_(ids)))) if ids else set()
    if faltando := set(ids) - existentes:
        raise HTTPException(404, f"Ativo(s) não encontrado(s): {sorted(faltando)}")
    em_outra = sessao.execute(
        select(Ativo.ticker, Carteira.nome)
        .join(CarteiraAtivo, CarteiraAtivo.ativo_id == Ativo.id)
        .join(Carteira, Carteira.id == CarteiraAtivo.carteira_id)
        .where(Ativo.id.in_(ids), CarteiraAtivo.carteira_id != (obj.id or 0))
    ).all()
    if em_outra:
        lista = ", ".join(f"{t} ({c})" for t, c in em_outra)
        raise HTTPException(409, f"Ativo já pertence a outra carteira: {lista}")

    for campo, valor in dados.model_dump(exclude={"ativos"}).items():
        setattr(obj, campo, valor)
    sessao.add(obj)
    _gravar(sessao, "Já existe carteira com esse nome", flush=True)
    sessao.execute(delete(CarteiraAtivo).where(CarteiraAtivo.carteira_id == obj.id))
    sessao.add_all(CarteiraAtivo(carteira_id=obj.id, **a.model_dump()) for a in dados.ativos)
    sessao.commit()
    return _carteira_out(sessao, obj)


@router.get("/carteiras", response_model=list[CarteiraOut])
def listar_carteiras(sessao: SessaoDep):
    return [_carteira_out(sessao, c) for c in sessao.scalars(select(Carteira).order_by(Carteira.ordem, Carteira.nome))]


@router.post("/carteiras", response_model=CarteiraOut, status_code=201)
def criar_carteira(dados: CarteiraIn, sessao: SessaoDep):
    return _salvar_carteira(sessao, Carteira(), dados)


@router.put("/carteiras/{id_}", response_model=CarteiraOut)
def alterar_carteira(id_: int, dados: CarteiraIn, sessao: SessaoDep):
    return _salvar_carteira(sessao, obter_ou_404(sessao, Carteira, id_), dados)


@router.delete("/carteiras/{id_}", status_code=204)
def excluir_carteira(id_: int, sessao: SessaoDep):
    sessao.delete(obter_ou_404(sessao, Carteira, id_))
    sessao.commit()


# ---------- Parâmetros ----------

@router.get("/parametros", response_model=ParametrosIO)
def ler_parametros(sessao: SessaoDep):
    return ParametrosIO(**vars(parametros.carregar(sessao)))


@router.put("/parametros", response_model=ParametrosIO)
def salvar_parametros(dados: ParametrosIO, sessao: SessaoDep):
    return ParametrosIO(**vars(parametros.salvar(sessao, parametros.Parametros(**dados.model_dump()))))
