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
  coingecko_id: string | null;
  data_vencimento: string | null;
  isento_ir: boolean;
}

export interface MoedaCripto {
  id: string;
  ticker: string;
  nome: string;
}

export interface ItemCripto {
  ativo_id: number;
  ticker: string;
  nome: string | null;
  coingecko_id: string | null;
  preco_usd: number | null;
  preco_brl: number | null;
  market_cap_usd: number | null;
  variacao_24h: number | null;
  variacao_7d: number | null;
  variacao_30d: number | null;
  fonte: string | null;
  atualizado_em: string | null;
  quantidade: number;
  preco_medio_brl: number;
  investido_brl: number;
  mercado_brl: number | null;
  lucro_aberto_brl: number | null;
}

export interface PainelCripto {
  itens: ItemCripto[];
  cambio_usd_brl: number | null;
  cambio_data: string | null;
  avisos: string[];
}

export interface MonitorCripto {
  meses: {
    investidor_id: number;
    investidor: string;
    competencia: string;
    vendas_brl: number;
    ganhos_brl: number | null;
    perdas_brl: number | null;
    resultado_brl: number | null;
    limite_brl: number;
    saldo_limite_brl: number;
    acima_limite: boolean;
  }[];
  avisos: string[];
}

export interface PontoCripto {
  instante: string;
  preco_usd: number;
}

export interface ItemRadar {
  ativo_id: number;
  ticker: string;
  nome: string | null;
  classe: string;
  moeda: string;
  tem_posicao: boolean;
  cotacao: number | null;
  cotacao_data: string | null;
  cotacao_fonte: string | null;
  variacao_1d_pct: number | null;
  variacao_7d_pct: number | null;
  variacao_14d_pct: number | null;
  drawdown_60d_pct: number | null;
  minimo_52s: number | null;
  maximo_52s: number | null;
  preco_teto_graham: number | null;
  upside_graham_pct: number | null;
  preco_lucro: number | null;
  preco_valor_patrimonial: number | null;
  dividend_yield: number | null;
  roe: number | null;
  roic: number | null;
  fii_ffo_yield: number | null;
  data_ref_fundamentos: string | null;
  yoc_12m: number | null;
  preco_alvo: number | null;
  atingiu_alvo: boolean;
}

export interface ParcelaLucro {
  categoria: "aberto" | "swing" | "daytrade" | "proventos";
  rotulo: string;
  valor: number | null;
}

export interface EventoStatus {
  id: number;
  ativo_id: number;
  ticker: string;
  data: string;
  tipo: "operacao" | "provento";
  evento: string;
  rotulo: string;
  investidor_id: number;
  quantidade: number | null;
  preco: number | null;
  valor_brl: number | null;
  moeda: string;
  daytrade: boolean;
  participacao: number;
}

export interface StatusAtivo {
  escopo: "ativo" | "carteira" | "book";
  escopo_id: number;
  nome: string;
  ativos: number;
  investido: number;
  mercado: number | null;
  lucro_aberto: number | null;
  lucro_swing: number;
  lucro_daytrade: number;
  proventos_total: number;
  proventos_12m: number;
  yoc_12m: number | null;
  lucro_total: number | null;
  distribuicao: ParcelaLucro[];
  total_eventos: number;
  eventos: EventoStatus[];
  limite: number;
  deslocamento: number;
}

export interface PremissasValuation {
  lpa: number | null;
  vpa: number | null;
  dividendo_anual: number | null;
  roe: number | null;
  payout: number | null;
  g: number | null;
  ke: number | null;
  pl_historico: number | null;
  pl_setor: number | null;
  fcfe_1: number | null;
  fcfe_2: number | null;
  fcfe_3: number | null;
  fcfe_4: number | null;
  fcfe_5: number | null;
}

export interface ModeloValuation {
  id: "graham" | "bazin" | "dcf_fcfe" | "gordon" | "pl_historico" | "pl_setor" | "pvp_justificado";
  rotulo: string;
  preco_justo: number | null;
  motivo: string | null;
}

export interface MesValuation {
  data: string;
  investido: number;
  mercado: number;
  fluxo: number;
  twr: number;
  twr_acumulado: number;
  sem_cotacao: boolean;
}

export interface Valuation {
  ativo_id: number;
  ticker: string;
  nome: string | null;
  classe: string;
  moeda: string;
  cotacao: number | null;
  cotacao_data: string | null;
  cotacao_fonte: string | null;
  fundamento_data: string | null;
  fundamento_fonte: string | null;
  premissas_salvas_em: string | null;
  premissas: PremissasValuation;
  modelos: ModeloValuation[];
  analise: {
    modelos_disponiveis: number;
    total_modelos: number;
    preco_mediano: number | null;
    upside_mediano: number | null;
  };
  rentabilidade: {
    data_referencia: string | null;
    tir_aa: number | null;
    tir_am: number | null;
    twr_acumulado: number | null;
    meses: MesValuation[];
  };
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

export interface Backup {
  nome: string;
  tipo: "manual" | "automatico" | "antes-restauracao";
  tamanho: number;
  criado_em: string;
}

export interface Backups {
  disponivel: boolean;
  motivo: string | null;
  pasta: string | null;
  itens: Backup[];
}

export interface Restauracao {
  restaurado: string;
  revisao: string;
  copia_anterior: string;
}

export type StatusExtrato = "novo" | "duplicado" | "verificar" | "ignorado";

export interface LinhaExtrato {
  numero: number;
  descricao: string;
  data: string | null;
  ticker: string | null;
  tipo: "OPERACAO" | "PROVENTO" | "IGNORADA";
  evento: string | null;
  quantidade: number;
  preco: number;
  valor: number;
  instituicao: string | null;
  daytrade: boolean;
  status: StatusExtrato;
  motivo: string | null;
}

export interface PreviaExtrato {
  relatorio: "NEGOCIACAO" | "MOVIMENTACAO" | "PROVENTOS";
  linhas: LinhaExtrato[];
  ativos_novos: Record<string, string>;
  corretoras_novas: string[];
}

export interface ResultadoExtrato {
  operacoes: number;
  proventos: number;
  ativos_criados: string[];
  corretoras_criadas: string[];
  lote_id: number | null;
}

export interface TotaisAluguel {
  bruto: number;
  taxas: number;
  irrf: number;
  liquido: number;
}

export interface ResumoAluguel {
  anos: number[];
  totais: TotaisAluguel;
  lancamentos: number;
  por_ativo: (TotaisAluguel & { ticker: string; lancamentos: number; ultimo: string })[];
  por_mes: (TotaisAluguel & { mes: string })[];
}

export interface ItemAluguel {
  data: string;
  ticker: string | null;
  raiz: string;
  valor: number;
  taxas: number;
  irrf: number;
  linhas: number[];
  status: "novo" | "duplicado" | "verificar" | "sem_ativo";
  motivo: string | null;
  hash: string;
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
  real_acumulado: number | null;
}

export interface Janela {
  nome: string;
  inicio: string;
  twr: number | null;
  ibov: number | null;
  ifix: number | null;
  cdi: number | null;
  ipca: number | null;
  real: number | null;
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
  ir_opcoes_no_limite: boolean;
  ir_outras_classes_no_limite: boolean;
  ir_subscricao_fii_isenta: boolean;
  alerta_desvio_pp: number | null;
  alerta_vencimento_dias: number | null;
  alerta_cotacao_dias: number | null;
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

// ---------- Planejamento e monitoramento ----------

export interface ItemRendaFixa {
  investidor_id: number;
  ativo_id: number;
  ticker: string;
  nome: string | null;
  classe: string;
  moeda: string;
  descricao: string;
  isento_ir: boolean;
  data_vencimento: string | null;
  dias_para_vencer: number | null;
  quantidade: number;
  custo: number;
  bruto: number;
  iof: number;
  ir: number;
  liquido: number;
  aliquota_ir: number | null;
  bruto_vencimento: number | null;
  liquido_vencimento: number | null;
}

export interface RendaFixa {
  itens: ItemRendaFixa[];
  custo: number;
  bruto: number;
  impostos: number;
  liquido: number;
  liquido_vencimento: number | null;
}

export interface ProventoAgenda {
  id: number;
  investidor_id: number;
  ticker: string;
  evento: string;
  data_com: string | null;
  data_pagamento: string;
  liquido: number;
}

export interface AgendaProventos {
  a_receber: ProventoAgenda[];
  total_a_receber: number;
  meses: { mes: string; confirmado: number; estimado: number }[];
  por_ativo: { ativo_id: number; ticker: string; classe: string; confirmado: number; estimado: number; total: number; yoc: number | null }[];
  total_12m: number;
  media_mensal: number;
  yoc_projetado: number | null;
}

export interface LoteImportacao {
  id: number;
  tipo: string;
  arquivo: string | null;
  investidor_id: number | null;
  criado_em: string;
  desfeito_em: string | null;
  operacoes: number;
  proventos: number;
  caixa: number;
}

export interface Verificacao {
  codigo: string;
  titulo: string;
  severidade: "erro" | "aviso" | "info";
  descricao: string;
  link: string | null;
  itens: string[];
}

export interface ExposicaoCorretora {
  corretora: string;
  valor: number;
  ativos: number;
}

export interface Alerta {
  codigo: string;
  severidade: "alta" | "media" | "info";
  titulo: string;
  detalhe: string;
  link: string | null;
}

export type TipoMeta = "PATRIMONIO" | "RENDA";

export interface Meta {
  id: number;
  nome: string;
  tipo: TipoMeta;
  valor_alvo: number;
  data_alvo: string;
  aporte_mensal: number;
  rentabilidade_aa: number;
  rendimento_aa: number | null;
  investidores: number[] | null;
  valor_atual: number;
  progresso: number;
  meses_restantes: number;
  projetado_pessimista: number;
  projetado_base: number;
  projetado_otimista: number;
  atinge: boolean;
  data_estimada: string | null;
  aporte_necessario: number;
  rendimento_usado: number | null;
  serie: { mes: string; pessimista: number; base: number; otimista: number }[];
}
