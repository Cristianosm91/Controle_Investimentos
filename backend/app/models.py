from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

Valor = Numeric(20, 8, asdecimal=True)


class Grupo(Base):
    __tablename__ = "grupo"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(60), unique=True)


class Investidor(Base):
    __tablename__ = "investidor"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), unique=True)
    cpf: Mapped[str | None] = mapped_column(String(11))
    grupo_id: Mapped[int | None] = mapped_column(ForeignKey("grupo.id", ondelete="SET NULL"))
    cor: Mapped[str] = mapped_column(String(7), default="#2563eb")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    grupo: Mapped[Grupo | None] = relationship()


class Corretora(Base):
    __tablename__ = "corretora"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(60), unique=True)
    cnpj: Mapped[str | None] = mapped_column(String(14))


class Ativo(Base):
    __tablename__ = "ativo"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True)
    nome: Mapped[str | None] = mapped_column(String(120))
    classe: Mapped[str] = mapped_column(String(20), default="AÇÃO")
    setor: Mapped[str | None] = mapped_column(String(80))
    subsetor: Mapped[str | None] = mapped_column(String(80))
    moeda: Mapped[str] = mapped_column(String(3), default="BRL")
    # Bolsa de origem no padrão do Google Finance (BVMF, NASDAQ, NYSE...).
    mercado: Mapped[str | None] = mapped_column(String(20))
    cotacao_automatica: Mapped[bool] = mapped_column(Boolean, default=True)


class Operacao(Base):
    __tablename__ = "operacao"
    __table_args__ = (Index("ix_operacao_inv_ativo_data", "investidor_id", "ativo_id", "data"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    investidor_id: Mapped[int] = mapped_column(ForeignKey("investidor.id", ondelete="RESTRICT"))
    ativo_id: Mapped[int] = mapped_column(ForeignKey("ativo.id", ondelete="RESTRICT"))
    corretora_id: Mapped[int | None] = mapped_column(ForeignKey("corretora.id", ondelete="SET NULL"))
    data: Mapped[date] = mapped_column(Date)
    evento: Mapped[str] = mapped_column(String(20))
    quantidade: Mapped[Decimal] = mapped_column(Valor)
    preco: Mapped[Decimal] = mapped_column(Valor, default=Decimal(0))
    taxas: Mapped[Decimal] = mapped_column(Valor, default=Decimal(0))
    irrf: Mapped[Decimal] = mapped_column(Valor, default=Decimal(0))
    moeda: Mapped[str] = mapped_column(String(3), default="BRL")
    # Taxa para BRL na data (PTAX); PM e lucro são apurados em BRL, como exige a RFB.
    cambio: Mapped[Decimal] = mapped_column(Valor, default=Decimal(1))
    daytrade: Mapped[bool] = mapped_column(Boolean, default=False)
    observacao: Mapped[str | None] = mapped_column(String(200))
    origem: Mapped[str] = mapped_column(String(20), default="manual")
    hash_origem: Mapped[str | None] = mapped_column(String(64), unique=True)

    investidor: Mapped[Investidor] = relationship()
    ativo: Mapped[Ativo] = relationship()
    corretora: Mapped[Corretora | None] = relationship()


class Provento(Base):
    __tablename__ = "provento"
    __table_args__ = (Index("ix_provento_inv_ativo_data", "investidor_id", "ativo_id", "data_pagamento"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    investidor_id: Mapped[int] = mapped_column(ForeignKey("investidor.id", ondelete="RESTRICT"))
    ativo_id: Mapped[int] = mapped_column(ForeignKey("ativo.id", ondelete="RESTRICT"))
    corretora_id: Mapped[int | None] = mapped_column(ForeignKey("corretora.id", ondelete="SET NULL"))
    data_pagamento: Mapped[date] = mapped_column(Date)
    data_com: Mapped[date | None] = mapped_column(Date)
    evento: Mapped[str] = mapped_column(String(20))
    valor: Mapped[Decimal] = mapped_column(Valor)
    irrf: Mapped[Decimal] = mapped_column(Valor, default=Decimal(0))
    taxas: Mapped[Decimal] = mapped_column(Valor, default=Decimal(0))
    moeda: Mapped[str] = mapped_column(String(3), default="BRL")
    cambio: Mapped[Decimal] = mapped_column(Valor, default=Decimal(1))
    observacao: Mapped[str | None] = mapped_column(String(200))
    origem: Mapped[str] = mapped_column(String(20), default="manual")
    hash_origem: Mapped[str | None] = mapped_column(String(64), unique=True)

    investidor: Mapped[Investidor] = relationship()
    ativo: Mapped[Ativo] = relationship()
    corretora: Mapped[Corretora | None] = relationship()


class MovCaixa(Base):
    __tablename__ = "mov_caixa"

    id: Mapped[int] = mapped_column(primary_key=True)
    investidor_id: Mapped[int] = mapped_column(ForeignKey("investidor.id", ondelete="RESTRICT"))
    corretora_id: Mapped[int | None] = mapped_column(ForeignKey("corretora.id", ondelete="SET NULL"))
    data: Mapped[date] = mapped_column(Date)
    evento: Mapped[str] = mapped_column(String(20))
    valor: Mapped[Decimal] = mapped_column(Valor)
    moeda: Mapped[str] = mapped_column(String(3), default="BRL")
    observacao: Mapped[str | None] = mapped_column(String(200))
    origem: Mapped[str] = mapped_column(String(20), default="manual")
    hash_origem: Mapped[str | None] = mapped_column(String(64), unique=True)


class Cotacao(Base):
    """Uma linha por ativo e dia; a linha do dia corrente é atualizada durante o pregão."""

    __tablename__ = "cotacao"
    __table_args__ = (UniqueConstraint("ativo_id", "data", name="uq_cotacao_ativo_data"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ativo_id: Mapped[int] = mapped_column(ForeignKey("ativo.id", ondelete="CASCADE"))
    data: Mapped[date] = mapped_column(Date)
    preco: Mapped[Decimal] = mapped_column(Valor)
    variacao_pct: Mapped[Decimal | None] = mapped_column(Valor)
    fonte: Mapped[str] = mapped_column(String(30))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CotacaoMoeda(Base):
    """Valor de 1 unidade da moeda em BRL."""

    __tablename__ = "cotacao_moeda"
    __table_args__ = (UniqueConstraint("moeda", "data", name="uq_cotacao_moeda_data"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    moeda: Mapped[str] = mapped_column(String(3))
    data: Mapped[date] = mapped_column(Date)
    valor: Mapped[Decimal] = mapped_column(Valor)
    fonte: Mapped[str] = mapped_column(String(30))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class IndiceMensal(Base):
    __tablename__ = "indice_mensal"

    competencia: Mapped[date] = mapped_column(Date, primary_key=True)
    ibov: Mapped[Decimal | None] = mapped_column(Valor)
    ifix: Mapped[Decimal | None] = mapped_column(Valor)
    cdi: Mapped[Decimal | None] = mapped_column(Valor)
    ipca: Mapped[Decimal | None] = mapped_column(Valor)
    selic: Mapped[Decimal | None] = mapped_column(Valor)
    igpm: Mapped[Decimal | None] = mapped_column(Valor)


class Parametro(Base):
    __tablename__ = "parametro"

    chave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[str] = mapped_column(String(500))


class DarfPago(Base):
    __tablename__ = "darf_pago"

    id: Mapped[int] = mapped_column(primary_key=True)
    investidor_id: Mapped[int] = mapped_column(ForeignKey("investidor.id", ondelete="RESTRICT"))
    competencia: Mapped[date] = mapped_column(Date)
    data_pagamento: Mapped[date] = mapped_column(Date)
    valor: Mapped[Decimal] = mapped_column(Valor)
