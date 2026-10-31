"""Vocabulário de negócio compartilhado entre API, serviços e importador."""

# Convenção de sinal de `quantidade` (igual à planilha):
#   C, BONIFICACAO ............ > 0 (entra na posição pelo preço informado)
#   V, VENDA_SUBSCRICAO ....... < 0 (sai da posição)
#   DESDOBRAMENTO ............. +/- (só altera quantidade; custo total mantido)
#   TRANSFERENCIA ............. +/- (troca de ticker/incorporação; sai sem lucro, entra pelo custo)
#   AMORTIZACAO, CISAO ........ > 0 com preco <= 0 (reduz custo: quantidade x preco)
EVENTOS_OPERACAO: dict[str, str] = {
    "C": "Compra",
    "V": "Venda",
    "BONIFICACAO": "Bonificação",
    "DESDOBRAMENTO": "Desdobramento/Grupamento",
    "TRANSFERENCIA": "Transferência/Troca de ticker",
    "AMORTIZACAO": "Amortização",
    "CISAO": "Cisão",
    "VENDA_SUBSCRICAO": "Venda de direito de subscrição",
}

EVENTOS_PROVENTO: dict[str, str] = {
    "DIVIDENDO": "Dividendo",
    "JSCP": "Juros sobre capital próprio",
    "RENDIMENTO": "Rendimento",
    "BONIFICACAO": "Bonificação em dinheiro",
    "REEMBOLSO_JSCP": "Reembolso de JSCP",
    "AMORTIZACAO": "Amortização",
    "ALUGUEL": "Aluguel de ações (BTC)",
}

EVENTOS_CAIXA: dict[str, str] = {
    "APORTE": "Aporte",
    "SAQUE": "Saque",
    "CREDITO": "Crédito",
    "DEBITO": "Débito",
}

# Convenção de sinal de `valor` no caixa: entradas > 0, saídas < 0.
EVENTOS_CAIXA_ENTRADA = frozenset({"APORTE", "CREDITO"})

MOEDAS = ("BRL", "USD", "EUR")

# Indexadores da renda fixa automática (ativos personalizados).
INDEXADORES: dict[str, str] = {
    "CDI": "CDI",
    "SELIC": "SELIC",
    "IPCA": "IPCA +",
    "IGPM": "IGP-M +",
    "PRE": "Prefixado",
}

CATEGORIAS_CARTEIRA = ("Conservador", "Arrojado", "Renda Passiva")

# ---------- Imposto de renda (renda variável) ----------

CATEGORIAS_IR: dict[str, str] = {
    "ACAO": "Ações (swing trade)",
    "BDR": "BDR",
    "ETF": "ETF Brasil",
    "OPCAO": "Opções",
    "DAYTRADE": "Day trade",
    "FII": "FII / Fiagro",
    "EXTERIOR": "Exterior",
}

# Prejuízo só compensa lucro do mesmo grupo: operações comuns, day trade, FII e exterior.
GRUPO_PREJUIZO: dict[str, str] = {
    "ACAO": "COMUM", "BDR": "COMUM", "ETF": "COMUM", "OPCAO": "COMUM",
    "DAYTRADE": "DAYTRADE", "FII": "FII", "EXTERIOR": "EXTERIOR",
}

GRUPOS_PREJUIZO: dict[str, str] = {
    "COMUM": "Operações comuns (ações, BDR, ETF, opções)",
    "DAYTRADE": "Day trade",
    "FII": "FII / Fiagro",
    "EXTERIOR": "Exterior",
}

APURACOES_IR = ("MENSAL", "ANUAL")

DARF_CODIGO_RV = "6015"
DARF_MINIMO = 10
