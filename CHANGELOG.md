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

### Corrigido
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
