"""Identificação de nomes e apelidos de corretoras."""

import re
import unicodedata
from itertools import combinations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Corretora, CorretoraApelido


class CorretoraAmbigua(ValueError):
    pass


def normalizar(nome: str) -> str:
    texto = unicodedata.normalize("NFKD", nome)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().upper()


def indice(sessao: Session) -> dict[str, dict[int, Corretora]]:
    resultado: dict[str, dict[int, Corretora]] = {}
    for corretora in sessao.scalars(select(Corretora)):
        resultado.setdefault(normalizar(corretora.nome), {})[corretora.id] = corretora
    for apelido in sessao.scalars(select(CorretoraApelido)):
        resultado.setdefault(normalizar(apelido.nome), {})[apelido.corretora_id] = apelido.corretora
    return resultado


def encontrar(indice_nomes: dict[str, dict[int, Corretora]], nome: str) -> Corretora | None:
    candidatos = indice_nomes.get(normalizar(nome), {})
    if len(candidatos) > 1:
        raise CorretoraAmbigua(
            f"A corretora '{nome}' corresponde a mais de um cadastro. Revise em Configurações → Corretoras."
        )
    return next(iter(candidatos.values()), None)


def possiveis_duplicatas(sessao: Session) -> list[tuple[Corretora, Corretora]]:
    cadastradas = list(sessao.scalars(select(Corretora).order_by(Corretora.id)))
    pares = []
    for primeira, segunda in combinations(cadastradas, 2):
        a, b = normalizar(primeira.nome), normalizar(segunda.nome)
        if a and b and (a == b or (len(a.split()) == 1 and b.startswith(a + " "))
                        or (len(b.split()) == 1 and a.startswith(b + " "))):
            pares.append((primeira, segunda))
    return pares
