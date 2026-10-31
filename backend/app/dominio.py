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

MOEDAS = ("BRL", "USD", "EUR")
