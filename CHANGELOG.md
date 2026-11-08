# Changelog

Todas as mudanças relevantes deste projeto são documentadas aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o versionamento segue
`MAJOR.MINOR.CORREÇÃO`.

## [Não lançado]

### Corrigido
- Operações: ações Editar/Excluir alinhadas com ou sem vínculo de transferência; textos longos não ampliam as colunas.
- Eventos compactos na tabela (Desd./Grup., Troca Ticker e Venda subscr.), com legenda no botão de ajuda do cabeçalho e nomes completos preservados na exportação.
- Filtro de operações contempla todos os eventos do cadastro de domínio.
- Valuation: unidades e campos das premissas alinhados mesmo quando os títulos ocupam mais de uma linha.

## [1.4.0] - 2026-11-08

### Adicionado
- Barra lateral recolhível com preferência persistida, identificação dos itens por tooltip e navegação em drawer em telas menores.
- Operações: criação conjunta das pernas de saída e entrada em trocas de ticker, com vínculo entre os lançamentos; operações de transferência existentes também podem ser vinculadas ou desvinculadas.
- Filtro por evento na listagem de operações e na API.
- Configurações → Classes dos ativos: opção de listar todos os ativos e buscar por ticker, incluindo cadastros sem posição aberta.
- Valuation: dicas explicativas para as premissas de cálculo.

### Alterado
- Cadastro rápido de ativos nos campos de ticker solicita classe, mercado e moeda explicitamente.

## [1.3.0] - 2026-11-07

### Adicionado
- Modelo personalizado de proventos com os tipos da planilha de referência e importação de IRRF, taxas, moeda, data-com e observação.
- Nomes explícitos para modelos personalizados e modelos da B3 na importação.
- Coluna opcional de classe no modelo personalizado de operações; arquivos antigos continuam aceitos e ativos já cadastrados preservam a classe.
- Configurações → Classes dos ativos: edição confirmada de classe e bolsa das posições abertas, preservando moeda e lançamentos.
- Botão para desfazer o lote recém-importado diretamente no resultado da importação.
- Operações e Proventos: filtro por corretora e seleção de intervalos com Shift, mantendo seleção individual e exclusão múltipla.
- Fundamentos básicos via Yahoo Finance para ações e outros ativos listados nos mercados dos EUA; a disponibilidade dos indicadores varia por ativo.

### Corrigido
- Fundamentos: resultado da atualização diferencia ativos fora dos mercados cobertos, tickers ausentes na fonte, falhas de consulta, classe incompatível e códigos históricos conhecidos; sugestões de ticker não alteram cadastros.
- Respostas vazias do Yahoo são sinalizadas como falhas de consulta; os dados disponíveis de outros ativos são preservados.
- Consulta SGS do Banco Central repete até três vezes em falhas transitórias de transporte, HTTP 429 ou 5xx.

### Alterado
- Versão do backend e metadados do frontend sincronizados em 1.3.0, consolidando também o modelo personalizado de proventos integrado após 1.2.1 sem incremento anterior.
- Documentação de importação, seleção, classificação, fontes de fundamentos e API atualizada. Integração SEC EDGAR permanece adiada.

### Limitações conhecidas
- O Yahoo Finance tem cobertura variável e termos de uso pessoal; FFO/AFFO de REITs e métricas próprias de ETFs não são calculados nem substituídos por indicadores de ações.
- A consulta real ao Yahoo neste ambiente retornou erros de certificado e HTTP 401; sucesso de coleta externa ainda não foi validado, embora os testes automatizados passem.

## [1.2.1] - 2026-11-02

### Corrigido
- Operações: exibe o IRRF como coluna própria ao lado das taxas.
- Planilha de operações: V.SUB aceita quantidade positiva ou negativa e sempre registra saída.

## [1.2.0] - 2026-11-02

### Adicionado
- Importação de planilha: correção e revalidação de várias linhas com erro diretamente na aplicação.
- Filtros de lançamentos por múltiplos ativos e opção de exibir todas as linhas na mesma página.
- Exemplos preenchidos de todos os eventos aceitos no modelo de operações, incluindo S/I positivo e negativo.

### Corrigido
- Planilha de operações aceita venda negativa, moedas USD/EUR, ticker de um caractere e S/I.
- Bonificação preserva o preço informado para calcular o PM sem aumentar o capital investido.

## [1.1.0] - 2026-11-02

### Adicionado
- Valuation: campo de ticker livre — qualquer ticker B3 digitado é cadastrado e já recebe cotação e fundamentos.
- Valuations salvos: nova tela com o último preço justo de cada ativo calculado e os dois cálculos anteriores
  (data, cotação no momento, diferença então e hoje, preço por modelo); "Calcular e salvar" registra o histórico.
- Portfólio: botão "🧮 Valuation" em cada posição abre a calculadora já com o ativo selecionado.
- Portfólio: seletor "Valuation" (oculto por padrão) mostra o preço justo salvo — mediana, um modelo ou todos —
  com a diferença para a cotação; clicar no valor ou em "▾ Modelos" abre todos os modelos do ativo.
- Portfólio: filtro de classes de ativo (exibir só uma ou algumas, ou excluir uma); cards, pesos e exposições
  passam a considerar apenas as classes visíveis.
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
- Segurança: uploads exigem `application/octet-stream` (415 caso contrário); respostas trazem `X-Frame-Options`,
  CSP `frame-ancestors 'none'`, `nosniff`, `Referrer-Policy` e `Cross-Origin-Resource-Policy`; planilhas que
  expandem além de 200 MB ou passam de 100 mil linhas são recusadas; backups com triggers ou views não são
  restaurados.
- Dependências Python fixadas nas versões testadas; `pytest` e `ruff` passam para `backend/requirements-dev.txt`.
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
- `iniciar.bat` não aborta mais quando o Node.js está indisponível ou a compilação da interface falha: avisa e
  usa a interface já compilada em `frontend\dist`.

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

[Não lançado]: https://github.com/Cristianosm91/Controle_Investimentos/compare/v1.2.1...HEAD
[1.2.1]: https://github.com/Cristianosm91/Controle_Investimentos/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/Cristianosm91/Controle_Investimentos/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/Cristianosm91/Controle_Investimentos/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Cristianosm91/Controle_Investimentos/releases/tag/v1.0.0
