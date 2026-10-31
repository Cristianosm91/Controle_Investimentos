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


class CriptoMercado(Base):
    """Último snapshot por ativo; preços e capitalização em USD."""

    __tablename__ = "cripto_mercado"

    ativo_id: Mapped[int] = mapped_column(ForeignKey("ativo.id", ondelete="CASCADE"), primary_key=True)
    preco_usd: Mapped[Decimal] = mapped_column(Valor)
    market_cap_usd: Mapped[Decimal | None] = mapped_column(Numeric(30, 8, asdecimal=True))
    variacao_24h: Mapped[Decimal | None] = mapped_column(Valor)
    variacao_7d: Mapped[Decimal | None] = mapped_column(Valor)
    variacao_30d: Mapped[Decimal | None] = mapped_column(Valor)
    fonte: Mapped[str] = mapped_column(String(30))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime)


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
    # Ativo personalizado (cotacao_automatica = False) com rendimento calculado: valor da cota = 1 em
    # `data_base`, corrigido por `indexador` x `indexador_pct` + `taxa_aa`. Sem indexador = saldo manual.
    indexador: Mapped[str | None] = mapped_column(String(10))
    indexador_pct: Mapped[Decimal | None] = mapped_column(Valor)
    taxa_aa: Mapped[Decimal | None] = mapped_column(Valor)
    data_base: Mapped[date | None] = mapped_column(Date)
    # CNPJ da empresa/fundo emissor (ficha Bens e Direitos da DIRPF).
    cnpj: Mapped[str | None] = mapped_column(String(14))
    coingecko_id: Mapped[str | None] = mapped_column(String(120), unique=True)
    # Renda fixa: vencimento do título e isenção de IR (LCI, LCA, CRI, CRA, poupança, debênture incentivada).
    data_vencimento: Mapped[date | None] = mapped_column(Date)
    isento_ir: Mapped[bool] = mapped_column(Boolean, default=False)


class LoteImportacao(Base):
    """Um arquivo importado; permite desfazer só os lançamentos gravados por ele."""

    __tablename__ = "lote_importacao"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(30))
    arquivo: Mapped[str | None] = mapped_column(String(200))
    investidor_id: Mapped[int | None] = mapped_column(ForeignKey("investidor.id", ondelete="SET NULL"))
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    desfeito_em: Mapped[datetime | None] = mapped_column(DateTime)
    operacoes: Mapped[int] = mapped_column(default=0)
    proventos: Mapped[int] = mapped_column(default=0)
    caixa: Mapped[int] = mapped_column(default=0)


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
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lote_importacao.id", ondelete="SET NULL"), index=True)

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
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lote_importacao.id", ondelete="SET NULL"), index=True)

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
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lote_importacao.id", ondelete="SET NULL"), index=True)

    corretora: Mapped[Corretora | None] = relationship()


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


class Fundamento(Base):
    """Snapshot de indicadores publicados por uma fonte para um ativo."""

    __tablename__ = "fundamento"
    __table_args__ = (
        UniqueConstraint("ativo_id", "data_ref", "fonte", name="uq_fundamento_ativo_data_fonte"),
        Index("ix_fundamento_ativo_data", "ativo_id", "data_ref"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ativo_id: Mapped[int] = mapped_column(ForeignKey("ativo.id", ondelete="CASCADE"))
    data_ref: Mapped[date] = mapped_column(Date)
    fonte: Mapped[str] = mapped_column(String(30))
    preco_lucro: Mapped[Decimal | None] = mapped_column(Valor)
    preco_valor_patrimonial: Mapped[Decimal | None] = mapped_column(Valor)
    dividend_yield: Mapped[Decimal | None] = mapped_column(Valor)
    psr: Mapped[Decimal | None] = mapped_column(Valor)
    roe: Mapped[Decimal | None] = mapped_column(Valor)
    roic: Mapped[Decimal | None] = mapped_column(Valor)
    margem_bruta: Mapped[Decimal | None] = mapped_column(Valor)
    margem_ebit: Mapped[Decimal | None] = mapped_column(Valor)
    margem_liquida: Mapped[Decimal | None] = mapped_column(Valor)
    liquidez_corrente: Mapped[Decimal | None] = mapped_column(Valor)
    liquidez_media_2m: Mapped[Decimal | None] = mapped_column(Valor)
    patrimonio_liquido: Mapped[Decimal | None] = mapped_column(Valor)
    valor_mercado: Mapped[Decimal | None] = mapped_column(Valor)
    divida_liquida_patrimonio: Mapped[Decimal | None] = mapped_column(Valor)
    crescimento_receita_5a: Mapped[Decimal | None] = mapped_column(Valor)
    segmento_fii: Mapped[str | None] = mapped_column(String(120))
    fii_dividendos_meses_12m: Mapped[int | None]
    fii_dividend_yield_2a: Mapped[Decimal | None] = mapped_column(Valor)
    fii_dividendos_meses_2a: Mapped[int | None]
    fii_ffo_yield: Mapped[Decimal | None] = mapped_column(Valor)
    fii_liquidez: Mapped[Decimal | None] = mapped_column(Valor)
    fii_area_m2: Mapped[Decimal | None] = mapped_column(Valor)
    fii_preco_m2: Mapped[Decimal | None] = mapped_column(Valor)
    fii_numero_imoveis: Mapped[int | None]
    fii_numero_unidades: Mapped[int | None]
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AtivoRadar(Base):
    """Ativo acompanhado no Radar, mesmo sem posição na carteira."""

    __tablename__ = "ativo_radar"
    __table_args__ = (UniqueConstraint("ativo_id", name="uq_ativo_radar_ativo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ativo_id: Mapped[int] = mapped_column(ForeignKey("ativo.id", ondelete="CASCADE"))
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Gera alerta quando a cotação fica igual ou abaixo deste preço (moeda do ativo).
    preco_alvo: Mapped[Decimal | None] = mapped_column(Valor)


class Meta(Base):
    """Objetivo financeiro: patrimônio ou renda mensal de proventos a atingir até uma data (valores de hoje)."""

    __tablename__ = "meta"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80))
    tipo: Mapped[str] = mapped_column(String(20))  # PATRIMONIO | RENDA
    valor_alvo: Mapped[Decimal] = mapped_column(Valor)
    data_alvo: Mapped[date] = mapped_column(Date)
    aporte_mensal: Mapped[Decimal] = mapped_column(Valor, default=Decimal(0))
    rentabilidade_aa: Mapped[Decimal] = mapped_column(Valor)  # real (acima da inflação), fração
    rendimento_aa: Mapped[Decimal | None] = mapped_column(Valor)  # dividend yield para metas de renda; vazio = atual
    investidores: Mapped[str | None] = mapped_column(String(200))  # IDs separados por vírgula; vazio = todos
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ValuationPremissa(Base):
    """Premissas editáveis de valuation, persistidas por ativo."""

    __tablename__ = "valuation_premissa"
    __table_args__ = (UniqueConstraint("ativo_id", name="uq_valuation_premissa_ativo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ativo_id: Mapped[int] = mapped_column(ForeignKey("ativo.id", ondelete="CASCADE"))
    lpa: Mapped[Decimal | None] = mapped_column(Valor)
    vpa: Mapped[Decimal | None] = mapped_column(Valor)
    dividendo_anual: Mapped[Decimal | None] = mapped_column(Valor)
    roe: Mapped[Decimal | None] = mapped_column(Valor)
    payout: Mapped[Decimal | None] = mapped_column(Valor)
    g: Mapped[Decimal | None] = mapped_column(Valor)
    ke: Mapped[Decimal | None] = mapped_column(Valor)
    pl_historico: Mapped[Decimal | None] = mapped_column(Valor)
    pl_setor: Mapped[Decimal | None] = mapped_column(Valor)
    fcfe_1: Mapped[Decimal | None] = mapped_column(Valor)
    fcfe_2: Mapped[Decimal | None] = mapped_column(Valor)
    fcfe_3: Mapped[Decimal | None] = mapped_column(Valor)
    fcfe_4: Mapped[Decimal | None] = mapped_column(Valor)
    fcfe_5: Mapped[Decimal | None] = mapped_column(Valor)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


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


class Estrategia(Base):
    """Divisão de primeiro nível do portfólio (ex.: Renda Variável x Renda Fixa)."""

    __tablename__ = "estrategia"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(60), unique=True)
    peso: Mapped[Decimal] = mapped_column(Valor, default=Decimal(0))  # fração do portfólio
    ordem: Mapped[int] = mapped_column(default=0)


class Book(Base):
    __tablename__ = "book"

    id: Mapped[int] = mapped_column(primary_key=True)
    estrategia_id: Mapped[int] = mapped_column(ForeignKey("estrategia.id", ondelete="RESTRICT"))
    nome: Mapped[str] = mapped_column(String(60), unique=True)
    peso: Mapped[Decimal] = mapped_column(Valor, default=Decimal(0))  # fração da estratégia
    ordem: Mapped[int] = mapped_column(default=0)

    estrategia: Mapped[Estrategia] = relationship()


class ClasseBook(Base):
    """Book padrão de cada classe de ativo."""

    __tablename__ = "classe_book"

    classe: Mapped[str] = mapped_column(String(20), primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("book.id", ondelete="CASCADE"))


class AtivoBook(Base):
    """Exceção: distribui um ativo entre books (substitui o book da classe)."""

    __tablename__ = "ativo_book"

    ativo_id: Mapped[int] = mapped_column(ForeignKey("ativo.id", ondelete="CASCADE"), primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("book.id", ondelete="CASCADE"), primary_key=True)
    percentual: Mapped[Decimal] = mapped_column(Valor)  # fração do ativo


class Carteira(Base):
    __tablename__ = "carteira"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(60), unique=True)
    categoria: Mapped[str | None] = mapped_column(String(30))
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)
    ordem: Mapped[int] = mapped_column(default=0)


class CarteiraAtivo(Base):
    """Um ativo pertence a no máximo uma carteira (agrupamentos sem dupla contagem)."""

    __tablename__ = "carteira_ativo"

    id: Mapped[int] = mapped_column(primary_key=True)
    carteira_id: Mapped[int] = mapped_column(ForeignKey("carteira.id", ondelete="CASCADE"))
    ativo_id: Mapped[int] = mapped_column(ForeignKey("ativo.id", ondelete="CASCADE"), unique=True)
    # Peso-alvo do ativo dentro do seu book (fração); vazio = divide o restante do book igualmente.
    peso: Mapped[Decimal | None] = mapped_column(Valor)
    preco_teto: Mapped[Decimal | None] = mapped_column(Valor)
    ranking: Mapped[int | None] = mapped_column()
    entra_preco_teto: Mapped[bool] = mapped_column(Boolean, default=True)

    carteira: Mapped[Carteira] = relationship()
    ativo: Mapped[Ativo] = relationship()


class DarfPago(Base):
    __tablename__ = "darf_pago"

    id: Mapped[int] = mapped_column(primary_key=True)
    investidor_id: Mapped[int] = mapped_column(ForeignKey("investidor.id", ondelete="RESTRICT"))
    competencia: Mapped[date] = mapped_column(Date)  # 1º dia do mês de apuração
    data_pagamento: Mapped[date] = mapped_column(Date)
    valor: Mapped[Decimal] = mapped_column(Valor)


class RegraFiscal(Base):
    """Alíquota e isenção de uma categoria de IR em um período de vigência (mudam por legislação)."""

    __tablename__ = "regra_fiscal"

    id: Mapped[int] = mapped_column(primary_key=True)
    categoria: Mapped[str] = mapped_column(String(20))
    vigencia_inicio: Mapped[date] = mapped_column(Date)
    vigencia_fim: Mapped[date | None] = mapped_column(Date)
    aliquota: Mapped[Decimal] = mapped_column(Valor)
    # Vendas no mês até este valor tornam o lucro isento; vazio = sem isenção.
    limite_isencao: Mapped[Decimal | None] = mapped_column(Valor)
    apuracao: Mapped[str] = mapped_column(String(10), default="MENSAL")  # MENSAL | ANUAL
    observacao: Mapped[str | None] = mapped_column(String(200))


class PrejuizoInicial(Base):
    """Prejuízo a compensar trazido de antes do início da apuração no app (por CPF e grupo de compensação)."""

    __tablename__ = "prejuizo_inicial"

    investidor_id: Mapped[int] = mapped_column(ForeignKey("investidor.id", ondelete="CASCADE"), primary_key=True)
    grupo: Mapped[str] = mapped_column(String(20), primary_key=True)
    valor: Mapped[Decimal] = mapped_column(Valor)  # > 0
