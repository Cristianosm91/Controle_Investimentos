"""Parâmetros de cálculo editáveis na tela de Configurações (tabela `parametro`, chave → texto)."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Parametro


@dataclass
class Parametros:
    # A partir desta data o saldo do caixa considera compras, vendas e proventos; vazio = só movimentações.
    caixa_data_inicio: date | None = None
    # Soma o saldo em caixa ao patrimônio do Portfólio.
    caixa_no_portfolio: bool = False


def _ler(texto: str, tipo):
    if tipo is bool:
        return texto == "1"
    if tipo is date:
        return date.fromisoformat(texto) if texto else None
    return texto


def _escrever(valor) -> str:
    if isinstance(valor, bool):
        return "1" if valor else "0"
    if isinstance(valor, date):
        return valor.isoformat()
    return "" if valor is None else str(valor)


_TIPOS = {"caixa_data_inicio": date, "caixa_no_portfolio": bool}


def carregar(sessao: Session) -> Parametros:
    gravados = {p.chave: p.valor for p in sessao.scalars(select(Parametro).where(Parametro.chave.in_(_TIPOS)))}
    return Parametros(**{chave: _ler(texto, _TIPOS[chave]) for chave, texto in gravados.items()})


def salvar(sessao: Session, parametros: Parametros) -> Parametros:
    for chave in _TIPOS:
        sessao.merge(Parametro(chave=chave, valor=_escrever(getattr(parametros, chave))))
    sessao.commit()
    return parametros
