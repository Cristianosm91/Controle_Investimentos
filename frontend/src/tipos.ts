export interface Grupo {
  id: number;
  nome: string;
}

export interface Investidor {
  id: number;
  nome: string;
  cpf_mascarado: string | null;
  grupo_id: number | null;
  cor: string;
  ativo: boolean;
}

export interface Posicao {
  investidor_id: number | null;
  ativo_id: number;
  ticker: string;
  nome: string | null;
  classe: string;
  setor: string | null;
  subsetor: string | null;
  moeda: string;
  quantidade: number;
  preco_medio: number;
  custo: number;
  cotacao: number | null;
  cotacao_data: string | null;
  cotacao_fonte: string | null;
  variacao_dia_pct: number | null;
  valor_mercado: number | null;
  lucro_dia: number | null;
  lucro_aberto: number | null;
  lucro_realizado: number;
  lucro_daytrade: number;
  proventos: number;
  data_inicio: string | null;
}

export interface Operacao {
  id: number;
  investidor_id: number;
  ativo_id: number;
  ticker: string;
  corretora_id: number | null;
  corretora: string | null;
  data: string;
  evento: string;
  quantidade: number;
  preco: number;
  taxas: number;
  irrf: number;
  moeda: string;
  cambio: number;
  daytrade: boolean;
  observacao: string | null;
  origem: string;
}

export interface Provento {
  id: number;
  investidor_id: number;
  ativo_id: number;
  ticker: string;
  corretora_id: number | null;
  corretora: string | null;
  data_pagamento: string;
  data_com: string | null;
  evento: string;
  valor: number;
  irrf: number;
  taxas: number;
  moeda: string;
  cambio: number;
  observacao: string | null;
}

export interface Pagina<T> {
  total: number;
  itens: T[];
}

export interface MovCaixa {
  id: number;
  investidor_id: number;
  corretora_id: number | null;
  corretora: string | null;
  data: string;
  evento: string;
  valor: number;
  moeda: string;
  observacao: string | null;
  origem: string;
}

export interface Ativo {
  id: number;
  ticker: string;
  nome: string | null;
  classe: string;
  setor: string | null;
  subsetor: string | null;
  moeda: string;
  mercado: string | null;
  cotacao_automatica: boolean;
}

export interface Corretora {
  id: number;
  nome: string;
  cnpj: string | null;
}

export interface Ptax {
  moeda: string;
  data_solicitada: string;
  data_cotacao: string;
  compra: number;
  venda: number;
  fonte: string;
}

export interface Tarefa {
  nome: string;
  descricao: string;
  em_execucao: boolean;
  inicio: string | null;
  fim: string | null;
  sucesso: boolean | null;
  mensagem: string | null;
  duracao_s: number | null;
  proxima: string | null;
}

export interface Dominio {
  eventos_operacao: Record<string, string>;
  eventos_provento: Record<string, string>;
  eventos_caixa: Record<string, string>;
  moedas: string[];
}
