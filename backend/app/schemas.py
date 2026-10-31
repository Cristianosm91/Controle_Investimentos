import re
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator, model_validator

from .dominio import EVENTOS_CAIXA, EVENTOS_CAIXA_ENTRADA, EVENTOS_OPERACAO, EVENTOS_PROVENTO, INDEXADORES, MOEDAS

T = TypeVar("T")

# Decimal no banco/cálculo, número no JSON (o front só exibe).
Num = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class _Saida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _validar_moeda(moeda: str, cambio: Decimal) -> None:
    if moeda not in MOEDAS:
        raise ValueError(f"Moeda deve ser uma de {MOEDAS}")
    if moeda == "BRL" and cambio != 1:
        raise ValueError("Lançamento em BRL deve ter câmbio 1")


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
    indexador: str | None = None
    indexador_pct: Decimal | None = Field(default=None, gt=0, description="Fração do índice (1 = 100%)")
    taxa_aa: Decimal | None = Field(default=None, gt=-1, description="Taxa adicional a.a. (fração)")
    data_base: date | None = None

    @field_validator("ticker", "mercado", "classe", "indexador")
    @classmethod
    def _maiusculo(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else v

    @field_validator("moeda")
    @classmethod
    def _moeda(cls, v: str) -> str:
        if v not in MOEDAS:
            raise ValueError(f"Moeda deve ser uma de {MOEDAS}")
        return v

    @model_validator(mode="after")
    def _renda_fixa(self) -> "AtivoIn":
        if self.indexador is None:
            self.indexador_pct = self.taxa_aa = self.data_base = None
            return self
        if self.indexador not in INDEXADORES:
            raise ValueError(f"Indexador deve ser um de {tuple(INDEXADORES)}")
        if self.cotacao_automatica:
            raise ValueError("Ativo com indexador não tem cotação automática")
        if self.data_base is None:
            raise ValueError("Informe a data-base (início do rendimento)")
        if self.indexador == "PRE" and not self.taxa_aa:
            raise ValueError("Ativo prefixado precisa de taxa a.a.")
        if self.indexador != "PRE" and self.indexador_pct is None:
            self.indexador_pct = Decimal(1)
        return self


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
    indexador: str | None = None
    indexador_pct: Num | None = None
    taxa_aa: Num | None = None
    data_base: date | None = None


class SaldoManualIn(BaseModel):
    data: date
    saldo: Decimal = Field(gt=0, description="Saldo total do ativo (todos os investidores) na moeda do ativo")


class CotaOut(BaseModel):
    ativo_id: int
    data: date
    cota: Num


# ---------- Configurações: estratégias, books, carteiras, parâmetros ----------

Fracao = Annotated[Decimal, Field(ge=0, le=1)]


class EstrategiaIn(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    peso: Fracao
    ordem: int = 0


class EstrategiaOut(_Saida):
    id: int
    nome: str
    peso: Num
    ordem: int


class BookIn(BaseModel):
    estrategia_id: int
    nome: str = Field(min_length=1, max_length=60)
    peso: Fracao
    ordem: int = 0
    classes: list[str] = Field(default_factory=list, description="Classes cujo book padrão é este")

    @field_validator("classes")
    @classmethod
    def _classes(cls, v: list[str]) -> list[str]:
        return sorted({c.strip().upper() for c in v if c.strip()})


class BookOut(_Saida):
    id: int
    estrategia_id: int
    nome: str
    peso: Num
    ordem: int
    classes: list[str]


class ExcecaoBookIn(BaseModel):
    book_id: int
    percentual: Annotated[Decimal, Field(gt=0, le=1)]


class ExcecaoBookOut(BaseModel):
    ativo_id: int
    ticker: str
    books: list[tuple[int, Num]]


class CarteiraAtivoIn(BaseModel):
    ativo_id: int
    peso: Fracao | None = Field(default=None, description="Peso-alvo dentro do book; vazio = divide o restante")
    preco_teto: Decimal | None = Field(default=None, gt=0)
    ranking: int | None = None
    entra_preco_teto: bool = True


class CarteiraAtivoOut(_Saida):
    ativo_id: int
    ticker: str
    peso: Num | None
    preco_teto: Num | None
    ranking: int | None
    entra_preco_teto: bool


class CarteiraIn(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    categoria: str | None = Field(default=None, max_length=30)
    ativa: bool = True
    ordem: int = 0
    ativos: list[CarteiraAtivoIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unicos(self) -> "CarteiraIn":
        ids = [a.ativo_id for a in self.ativos]
        if len(ids) != len(set(ids)):
            raise ValueError("Ativo repetido na carteira")
        return self


class CarteiraOut(_Saida):
    id: int
    nome: str
    categoria: str | None
    ativa: bool
    ordem: int
    ativos: list[CarteiraAtivoOut]


class ParametrosIO(BaseModel):
    caixa_data_inicio: date | None = None
    caixa_no_portfolio: bool = False


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
        _validar_moeda(self.moeda, self.cambio)
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
    corretora_id: int | None
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

    @model_validator(mode="after")
    def _validar(self) -> "ProventoIn":
        if self.evento not in EVENTOS_PROVENTO:
            raise ValueError(f"Evento inválido: {self.evento}")
        _validar_moeda(self.moeda, self.cambio)
        return self


class ProventoOut(_Saida):
    id: int
    investidor_id: int
    ativo_id: int
    ticker: str
    corretora_id: int | None
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


# ---------- Caixa ----------

class MovCaixaIn(BaseModel):
    investidor_id: int
    corretora_id: int | None = None
    data: date
    evento: str
    valor: Decimal = Field(description="Entrada > 0 (aporte/crédito); saída < 0 (saque/débito)")
    moeda: str = "BRL"
    observacao: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _validar(self) -> "MovCaixaIn":
        if self.evento not in EVENTOS_CAIXA:
            raise ValueError(f"Evento inválido: {self.evento}")
        if self.moeda not in MOEDAS:
            raise ValueError(f"Moeda deve ser uma de {MOEDAS}")
        entrada = self.evento in EVENTOS_CAIXA_ENTRADA
        if self.valor == 0 or (self.valor > 0) != entrada:
            raise ValueError(f"Valor deve ser {'positivo' if entrada else 'negativo'} para {self.evento}")
        return self


class MovCaixaOut(_Saida):
    id: int
    investidor_id: int
    corretora_id: int | None
    corretora: str | None
    data: date
    evento: str
    valor: Num
    moeda: str
    observacao: str | None
    origem: str


# ---------- Câmbio ----------

class PtaxOut(BaseModel):
    moeda: str
    data_solicitada: date
    data_cotacao: date
    compra: Num
    venda: Num
    fonte: str


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
    proventos_12m: Num | None = None
    yoc_12m: Num | None = None
    tir_aa: float | None = None
    data_inicio: date | None
    book: str | None = None
    estrategia: str | None = None
    carteira: str | None = None


class SaldoCaixaOut(BaseModel):
    corretora_id: int | None
    corretora: str | None
    moeda: str
    movimentacoes: Num
    operacoes: Num
    proventos: Num
    saldo: Num
    saldo_brl: Num | None


class CaixaSaldosOut(BaseModel):
    integrado_desde: date | None
    total_brl: Num
    saldos: list[SaldoCaixaOut]


class GrupoAlocacaoOut(BaseModel):
    nome: str
    estrategia: str | None
    peso_alvo: Num
    peso_atual: Num
    valor_atual: Num
    valor_alvo: Num
    ajuste: Num


class ItemAlocacaoOut(BaseModel):
    ativo_id: int
    ticker: str
    nome: str | None
    classe: str
    moeda: str
    book: str
    carteira: str | None
    cotacao: Num | None
    preco_teto: Num | None
    acima_teto: bool
    peso_alvo: Num
    peso_atual: Num
    valor_atual: Num
    valor_alvo: Num
    ajuste: Num
    quantidade: Num | None


class AlocacaoOut(BaseModel):
    total_atual: Num
    aporte: Num
    sobra: Num
    estrategias: list[GrupoAlocacaoOut]
    books: list[GrupoAlocacaoOut]
    ativos: list[ItemAlocacaoOut]
    avisos: list[str]


class AtualizacaoCotacoesOut(BaseModel):
    atualizados: dict[str, str]
    sem_cotacao: list[str]


class TarefaOut(BaseModel):
    nome: str
    descricao: str
    em_execucao: bool
    inicio: datetime | None
    fim: datetime | None
    sucesso: bool | None
    mensagem: str | None
    duracao_s: float | None
    proxima: datetime | None


class Pagina(BaseModel, Generic[T]):
    total: int
    itens: list[T]


# ---------- Rentabilidade ----------

class MesRentabilidadeOut(BaseModel):
    data: date
    investido: Num
    mercado: Num
    proventos: Num
    lucro_trades: Num
    lucro_daytrade: Num
    fluxo: Num
    lucro: Num
    twr: Num
    twr_acumulado: Num
    sem_cotacao: int
    ibov: Num | None
    ifix: Num | None
    cdi: Num | None
    ipca: Num | None
    ibov_acumulado: Num | None
    ifix_acumulado: Num | None
    cdi_acumulado: Num | None
    ipca_acumulado: Num | None


class JanelaOut(BaseModel):
    """Rentabilidade acumulada em uma janela (mês, ano, 12 meses, desde o início)."""

    nome: str
    inicio: date
    twr: Num | None
    ibov: Num | None
    ifix: Num | None
    cdi: Num | None
    ipca: Num | None


class ResumoOut(BaseModel):
    data_referencia: date | None
    patrimonio: Num
    investido: Num
    lucro_aberto: Num
    lucro_realizado: Num
    proventos_total: Num
    proventos_12m: Num
    yoc_12m: Num | None
    tir_aa: float | None
    tir_am: float | None
    janelas: list[JanelaOut]
    proventos_mensais: list[tuple[date, Num]]


class MatrizProventosOut(BaseModel):
    titulo_linhas: str
    linhas: list[str]
    valores: list[list[Num]]  # linhas x 12 meses
    totais_linha: list[Num]
    totais_mes: list[Num]
    total: Num
