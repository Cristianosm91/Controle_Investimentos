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
  proventos_12m: number | null;
  yoc_12m: number | null;
  tir_aa: number | null;
  data_inicio: string | null;
  book: string | null;
  estrategia: string | null;
  carteira: string | null;
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
  indexador: string | null;
  indexador_pct: number | null;
  taxa_aa: number | null;
  data_base: string | null;
  cnpj: string | null;
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

export type Benchmark = "ibov" | "ifix" | "cdi" | "ipca";

export interface MesRentabilidade {
  data: string;
  investido: number;
  mercado: number;
  proventos: number;
  lucro_trades: number;
  lucro_daytrade: number;
  fluxo: number;
  lucro: number;
  twr: number;
  twr_acumulado: number;
  sem_cotacao: number;
  ibov: number | null;
  ifix: number | null;
  cdi: number | null;
  ipca: number | null;
  ibov_acumulado: number | null;
  ifix_acumulado: number | null;
  cdi_acumulado: number | null;
  ipca_acumulado: number | null;
}

export interface Janela {
  nome: string;
  inicio: string;
  twr: number | null;
  ibov: number | null;
  ifix: number | null;
  cdi: number | null;
  ipca: number | null;
}

export interface Resumo {
  data_referencia: string | null;
  patrimonio: number;
  investido: number;
  lucro_aberto: number;
  lucro_realizado: number;
  proventos_total: number;
  proventos_12m: number;
  yoc_12m: number | null;
  tir_aa: number | null;
  tir_am: number | null;
  janelas: Janela[];
  proventos_mensais: [string, number][];
}

export interface MatrizProventos {
  titulo_linhas: string;
  linhas: string[];
  valores: number[][];
  totais_linha: number[];
  totais_mes: number[];
  total: number;
}

export interface Dominio {
  eventos_operacao: Record<string, string>;
  eventos_provento: Record<string, string>;
  eventos_caixa: Record<string, string>;
  moedas: string[];
  indexadores: Record<string, string>;
  categorias_carteira: string[];
  categorias_ir: Record<string, string>;
  grupos_prejuizo: Record<string, string>;
}

// ---------- Configurações ----------

export interface Estrategia {
  id: number;
  nome: string;
  peso: number;
  ordem: number;
}

export interface Book {
  id: number;
  estrategia_id: number;
  nome: string;
  peso: number;
  ordem: number;
  classes: string[];
}

export interface ExcecaoBook {
  ativo_id: number;
  ticker: string;
  books: [number, number][];
}

export interface CarteiraAtivo {
  ativo_id: number;
  ticker: string;
  peso: number | null;
  preco_teto: number | null;
  ranking: number | null;
  entra_preco_teto: boolean;
}

export interface Carteira {
  id: number;
  nome: string;
  categoria: string | null;
  ativa: boolean;
  ordem: number;
  ativos: CarteiraAtivo[];
}

export interface Parametros {
  caixa_data_inicio: string | null;
  caixa_no_portfolio: boolean;
  ir_ano_inicio: number | null;
  ir_bdr_como_acao: boolean;
  ir_daytrade_no_limite: boolean;
}

export interface Cota {
  ativo_id: number;
  data: string;
  cota: number;
}

// ---------- Caixa / Alocação ----------

export interface SaldoCaixa {
  corretora_id: number | null;
  corretora: string | null;
  moeda: string;
  movimentacoes: number;
  operacoes: number;
  proventos: number;
  saldo: number;
  saldo_brl: number | null;
}

export interface CaixaSaldos {
  integrado_desde: string | null;
  total_brl: number;
  saldos: SaldoCaixa[];
}

export interface GrupoAlocacao {
  nome: string;
  estrategia: string | null;
  peso_alvo: number;
  peso_atual: number;
  valor_atual: number;
  valor_alvo: number;
  ajuste: number;
}

export interface ItemAlocacao {
  ativo_id: number;
  ticker: string;
  nome: string | null;
  classe: string;
  moeda: string;
  book: string;
  carteira: string | null;
  cotacao: number | null;
  preco_teto: number | null;
  acima_teto: boolean;
  peso_alvo: number;
  peso_atual: number;
  valor_atual: number;
  valor_alvo: number;
  ajuste: number;
  quantidade: number | null;
}

export interface Alocacao {
  total_atual: number;
  aporte: number;
  sobra: number;
  estrategias: GrupoAlocacao[];
  books: GrupoAlocacao[];
  ativos: ItemAlocacao[];
  avisos: string[];
}

// ---------- Imposto de renda ----------

export interface RegraFiscal {
  id: number;
  categoria: string;
  vigencia_inicio: string;
  vigencia_fim: string | null;
  aliquota: number;
  limite_isencao: number | null;
  apuracao: "MENSAL" | "ANUAL";
  observacao: string | null;
}

export interface PrejuizoInicial {
  grupo: string;
  valor: number;
}

export interface DarfPago {
  id: number;
  investidor_id: number;
  competencia: string;
  data_pagamento: string;
  valor: number;
}

export interface CategoriaMesIR {
  categoria: string;
  vendas: number;
  lucro: number;
  isento: boolean;
  base: number;
  aliquota: number | null;
  imposto: number;
}

export interface MesIR {
  competencia: string;
  categorias: CategoriaMesIR[];
  prejuizo: Record<string, number>;
  imposto: number;
  irrf: number;
  irrf_compensado: number;
  irrf_saldo: number;
  darf_mes: number;
  darf_anterior: number;
  darf: number;
  darf_transportado: number;
  pago: number;
  saldo: number;
}

export interface AnoExterior {
  ano: number;
  vendas: number;
  lucro: number;
  dividendos: number;
  imposto_pago_exterior: number;
  base: number;
  imposto: number;
  prejuizo: number;
  regimes: string[];
}

export interface ApuracaoIR {
  anos: number[];
  meses: MesIR[];
  exterior: AnoExterior[];
  nao_apurados: string[];
}

export interface BemDireito {
  ativo_id: number;
  ticker: string;
  nome: string | null;
  cnpj: string | null;
  tipo: string;
  quantidade: number;
  custo_anterior: number;
  custo_atual: number;
  discriminacao: string;
}

export interface Rendimento {
  ficha: "ISENTO" | "EXCLUSIVO" | "OUTROS";
  tipo: string;
  ativo_id: number | null;
  ticker: string | null;
  cnpj: string | null;
  valor: number;
  irrf: number;
}

export interface Dirpf {
  ano: number;
  bens: BemDireito[];
  rendimentos: Rendimento[];
  meses: MesIR[];
  prejuizo_final: Record<string, number>;
  irrf_saldo_final: number;
  exterior: AnoExterior | null;
  avisos: string[];
}
