# Changelog

Todas as mudanças relevantes deste projeto são documentadas aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o versionamento segue
`MAJOR.MINOR.CORREÇÃO`.

## [Não lançado]

### Adicionado
- Portfólio: "Outros" nas exposições é clicável e mostra todos os itens ("Mostrar menos" recolhe).
- Gráficos e barras de exposição: dica flutuante acima do cursor com o valor exato do ponto/barra.
- Rentabilidade: aviso com botão "Carregar histórico de cotações" quando há meses sem cotação histórica.
- Importador da planilha: criptos do quadro `Histórico de rendimentos` (J:L) viram posições de abertura vinculadas
  ao CoinGecko (`--data-cripto`, `--somente-cripto`).
- Histórico de preços das criptos (Yahoo Finance) na carga complementar e na rotina diária, para a Rentabilidade.
- Modelos `.xlsx` para preencher e importar (B3 Negociação, Movimentação, Proventos recebidos e aluguel BTC),
  com instruções e exemplo, baixáveis nos modais de importação.
- Renda fixa: nova tela com valor líquido de IR regressivo e IOF por aplicação (PEPS), próximos vencimentos e
  projeção do valor líquido no vencimento; ativos personalizados ganham vencimento e marcação de isento de IR.
- Retorno real (TWR descontada a inflação/IPCA) no Resumo e na Rentabilidade (card e série "Carteira real").
- Proventos → Agenda e projeção: pagamentos lançados a receber e projeção dos próximos 12 meses pela quantidade
  atual, com yield on cost projetado e detalhe por ativo.
- Importações desfazíveis: cada arquivo importado (extrato B3 ou aluguel) vira um lote que pode ser desfeito em
  Configurações → Importações sem afetar outros lançamentos.
- Configurações → Qualidade dos dados: posição negativa, câmbio ausente no exterior, posição sem cotação ou com
  cotação antiga, ativo sem book/setor, renda fixa sem vencimento, lançamentos sem corretora e índices defasados.
- Portfólio: exposição e agrupamento por moeda; exposição por corretora.
- Alertas locais (sino no topo): DARF do mês anterior em aberto, renda fixa vencendo/vencida, preço-alvo do Radar
  atingido, books fora do alvo, proventos dos próximos 7 dias e erros de dados; limiares em Parâmetros.
- Radar: preço-alvo editável por ativo.
- Metas: objetivos de patrimônio ou de renda mensal com progresso, projeção em cenários (±2 p.p.), data estimada
  e aporte necessário, em valores de hoje.

### Corrigido
- Segurança: a API recusa `Host` desconhecido (400) e gravações cuja origem é outro site (403), impedindo que
  páginas abertas no navegador desfaçam importações, restaurem backups ou leiam dados via *DNS rebinding*.
- "Carregar histórico de cotações" disparado duas vezes seguidas não roda mais duas cargas em paralelo.
- Uploads de extrato/aluguel/backup não bloqueiam mais as demais requisições durante consultas ao banco ou gravação
  do arquivo.
- Cópias "antes da restauração" limitadas às 10 mais recentes; restos `.parcial` de backups/envios interrompidos
  são removidos ao iniciar; o encerramento registra as tarefas que estavam em execução.
- Configurações → Parâmetros: valores padrão dos limiares de alerta (o build da interface falhava na checagem de
  tipos).
- Evolução patrimonial com Mercado igual ao Investido nos meses passados: sem histórico de cotações, o app agora
  carrega automaticamente na inicialização o histórico B3 (COTAHIST) e o complementar (exterior, PTAX, índices).
- Valuation: botão "Salvar premissas" usa a cor padrão da aplicação.
- `iniciar.bat` só abre o navegador quando a API responde (antes abria numa tela de erro por alguns segundos).

## [1.0.0] - 2026-10-31

Primeira versão estável: substitui a planilha de controle de investimentos (Fases 0 a 6 do
[plano de desenvolvimento](PLANO_DESENVOLVIMENTO.md)).

### Adicionado
- Multi-investidor com grupos e seletor global; IR sempre por CPF.
- Resumo, Portfólio (agrupamentos por estratégia, book, carteira, classe e setor), Rentabilidade (TWR × IBOV, IFIX,
  CDI e IPCA; TIR/XIRR) e Alocação com simulador de aporte.
- Lançamento de operações, proventos e caixa, com eventos societários e câmbio pela PTAX.
- Cotações automáticas (Yahoo Finance), fechamento oficial da B3 (COTAHIST), índices do Banco Central e da B3.
- Configurações: estratégias e books, carteiras, ativos personalizados de renda fixa, parâmetros e regras fiscais.
- Imposto de Renda: apuração mensal, DARF 6015, prejuízo por grupo, exterior (Lei 14.754/2023) e relatório de apoio à
  DIRPF.
- Radar/watchlist, fundamentos (Fundamentus), Status do ativo, Valuation (7 modelos) e Cripto (CoinGecko → Kraken).
- Aluguel de ações (BTC): resumo por ativo e por mês e importação do extrato da corretora.
- Importação dos relatórios Negociação, Movimentação e Proventos recebidos da B3, com prévia e detecção de
  duplicidade.
- Exportação CSV/XLSX das tabelas de qualquer página.
- Backup automático diário, backup manual e restauração validada do banco.
- Importação idempotente da planilha original, com conciliação.
- Versão exibida no menu lateral e em `/api/saude`.

### Corrigido
- Migrações no SQLite falhavam ao recriar tabelas referenciadas por chaves estrangeiras.
- Arquivos da B3 com dimensão declarada como `A1` eram lidos só até a primeira linha.
- Quantidades em texto pt-BR com ponto de milhar (`1.350`) eram lidas como decimais.

[Não lançado]: https://github.com/Cristianosm91/Controle_Investimentos/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Cristianosm91/Controle_Investimentos/releases/tag/v1.0.0
