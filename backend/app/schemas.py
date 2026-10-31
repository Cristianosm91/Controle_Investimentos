import re
from datetime import date
from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator, model_validator

from .dominio import EVENTOS_OPERACAO, EVENTOS_PROVENTO, MOEDAS

T = TypeVar("T")

# Decimal no banco/cálculo, número no JSON (o front só exibe).
Num = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class _Saida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Grupos / Investidores / Corretoras ----------

class GrupoIn(BaseModel):
    nome: str = Field(min_length=1, max_length=60)


class GrupoOut(_Saida):
    id: int
    nome: str


class InvestidorIn(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    cpf: str | None = None
    grupo_id: int | None = None
    cor: str = Field(default="#2563eb", pattern=r"^#[0-9a-fA-F]{6}$")
    ativo: bool = True

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, v: str | None) -> str | None:
        if not v:
            return None
        digitos = re.sub(r"\D", "", v)
        if len(digitos) != 11:
            raise ValueError("CPF deve ter 11 dígitos")
        return digitos


class InvestidorOut(_Saida):
    id: int
    nome: str
    cpf_mascarado: str | None
    grupo_id: int | None
    cor: str
    ativo: bool


class CorretoraIn(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    cnpj: str | None = Field(default=None, pattern=r"^\d{14}$")


class CorretoraOut(_Saida):
    id: int
    nome: str
    cnpj: str | None


# ---------- Ativos ----------

class AtivoIn(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    nome: str | None = None
    classe: str = Field(default="AÇÃO", max_length=20)
    setor: str | None = None
    subsetor: str | None = None
    moeda: str = "BRL"
    mercado: str | None = "BVMF"
    cotacao_automatica: bool = True

    @field_validator("ticker", "mercado", "classe")
    @classmethod
    def _maiusculo(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else v

    @field_validator("moeda")
    @classmethod
    def _moeda(cls, v: str) -> str:
        if v not in MOEDAS:
            raise ValueError(f"Moeda deve ser uma de {MOEDAS}")
        return v


class AtivoOut(_Saida):
    id: int
    ticker: str
    nome: str | None
    classe: str
    setor: str | None
    subsetor: str | None
    moeda: str
    mercado: str | None
    cotacao_automatica: bool


# ---------- Operações ----------

class OperacaoIn(BaseModel):
    investidor_id: int
    ativo_id: int
    corretora_id: int | None = None
    data: date
    evento: str
    quantidade: Decimal
    preco: Decimal = Decimal(0)
    taxas: Decimal = Field(default=Decimal(0), ge=0)
    irrf: Decimal = Field(default=Decimal(0), ge=0)
    moeda: str = "BRL"
    cambio: Decimal = Field(default=Decimal(1), gt=0, description="PTAX da data para BRL")
    daytrade: bool = False
    observacao: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _sinais(self) -> "OperacaoIn":
        ev, q, p = self.evento, self.quantidade, self.preco
        if ev not in EVENTOS_OPERACAO:
            raise ValueError(f"Evento inválido: {ev}")
        if self.moeda not in MOEDAS:
            raise ValueError(f"Moeda deve ser uma de {MOEDAS}")
        if self.moeda == "BRL" and self.cambio != 1:
            raise ValueError("Operação em BRL deve ter câmbio 1")
        regras = {
            "C": q > 0 and p >= 0,
            "BONIFICACAO": q > 0 and p >= 0,
            "V": q < 0 and p >= 0,
            "VENDA_SUBSCRICAO": q < 0 and p >= 0,
            "DESDOBRAMENTO": q != 0,
            "TRANSFERENCIA": q != 0 and p >= 0,
            "AMORTIZACAO": q > 0 and p <= 0,
            "CISAO": q > 0 and p <= 0,
        }
        if not regras[ev]:
            raise ValueError(f"Quantidade/preço incompatíveis com o evento {ev}")
        if self.daytrade and ev not in ("C", "V"):
            raise ValueError("Day trade só aceita compra (C) e venda (V)")
        return self


class OperacaoOut(_Saida):
    id: int
    investidor_id: int
    ativo_id: int
    ticker: str
    corretora: str | None
    data: date
    evento: str
    quantidade: Num
    preco: Num
    taxas: Num
    irrf: Num
    moeda: str
    cambio: Num
    daytrade: bool
    observacao: str | None
    origem: str


# ---------- Proventos ----------

class ProventoIn(BaseModel):
    investidor_id: int
    ativo_id: int
    corretora_id: int | None = None
    data_pagamento: date
    data_com: date | None = None
    evento: str
    valor: Decimal = Field(gt=0)
    irrf: Decimal = Field(default=Decimal(0), ge=0)
    taxas: Decimal = Field(default=Decimal(0), ge=0)
    moeda: str = "BRL"
    cambio: Decimal = Field(default=Decimal(1), gt=0)
    observacao: str | None = Field(default=None, max_length=200)

    @field_validator("evento")
    @classmethod
    def _evento(cls, v: str) -> str:
        if v not in EVENTOS_PROVENTO:
            raise ValueError(f"Evento inválido: {v}")
        return v


class ProventoOut(_Saida):
    id: int
    investidor_id: int
    ativo_id: int
    ticker: str
    corretora: str | None
    data_pagamento: date
    data_com: date | None
    evento: str
    valor: Num
    irrf: Num
    taxas: Num
    moeda: str
    cambio: Num
    observacao: str | None


# ---------- Carteira / Cotações ----------

class PosicaoOut(BaseModel):
    investidor_id: int | None
    ativo_id: int
    ticker: str
    nome: str | None
    classe: str
    setor: str | None
    subsetor: str | None
    moeda: str
    quantidade: Num
    preco_medio: Num
    custo: Num
    cotacao: Num | None
    cotacao_data: date | None
    cotacao_fonte: str | None
    variacao_dia_pct: Num | None
    valor_mercado: Num | None
    lucro_dia: Num | None
    lucro_aberto: Num | None
    lucro_realizado: Num
    lucro_daytrade: Num
    proventos: Num
    data_inicio: date | None


class AtualizacaoCotacoesOut(BaseModel):
    atualizados: dict[str, str]
    sem_cotacao: list[str]


class Pagina(BaseModel, Generic[T]):
    total: int
    itens: list[T]
