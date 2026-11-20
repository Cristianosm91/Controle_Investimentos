export const EXPLICACAO_EVENTO: Record<string, string> = {
  C: "A compra aumenta a quantidade e o custo em BRL pelo preço, taxas e IRRF convertidos pelo câmbio informado. IPO e subscrição também são compras.",
  V: "A venda reduz a quantidade e o custo pelo preço médio vigente; o resultado realizado considera o valor da venda, taxas, IRRF e câmbio.",
  BONIFICACAO: "Aumenta a quantidade. O preço informado atribui custo às novas cotas e passa a compor o preço médio, sem representar desembolso.",
  DESDOBRAMENTO: "A quantidade assinada aumenta no desdobramento e diminui no grupamento; o custo total permanece igual e o preço médio se ajusta.",
  TRANSFERENCIA: "A saída reduz a posição sem realizar lucro e a entrada transfere o custo. Vincule as duas pernas para rastrear a troca de ticker/incorporação.",
  AMORTIZACAO: "O valor negativo por cota reduz o custo em quantidade × valor devolvido, convertido pelo câmbio. Não reduz a quantidade.",
  CISAO: "Registra o ajuste de custo associado à cisão; o valor negativo por cota reduz o custo da posição sem alterar a quantidade.",
  VENDA_SUBSCRICAO: "Registra a venda de direitos de subscrição como saída, com preço, taxas, IRRF e câmbio; não altera a quantidade do ativo subjacente.",
  R_CAP: "Registra uma restituição total de capital. O valor informado reduz o custo em BRL pelo câmbio e não altera a quantidade.",
};
