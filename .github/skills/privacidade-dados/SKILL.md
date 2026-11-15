---
name: privacidade-dados
description: 'Use ao revisar, testar ou validar a privacidade técnica de aplicações que tratam dados pessoais e financeiros (documentos como CPF, patrimônio, operações, dados de familiares) — inventário de dados, minimização, mascaramento em UI/exportações/logs/prints, exportações marcadas, exclusão/anonimização de pessoa e dados vinculados (inclusive limitação em backups), dados em repouso, fixtures e seeds fictícios, higiene do repositório (.gitignore, secret scanning), dados enviados a serviços externos, área de transferência/impressão/PDF, retenção de temporários e telemetria opt-in — alinhado aos princípios da LGPD, sem processo jurídico e sem alterar regras de negócio. Modos review (padrão, somente leitura), test e fix. Palavras-gatilho: privacidade, dados pessoais, LGPD, CPF, PII, minimização, mascaramento, anonimização, exclusão de dados, direito de exclusão, inventário de dados, dados sensíveis, exportação, planilha, gitignore, secret scanning, fixtures fictícias, seed, criptografia em repouso, BitLocker, temporários, telemetria, opt-in.'
argument-hint: '[modo: review | test | fix] [caminho] [foco opcional]'
---

# Privacidade de Dados

Valida, do ponto de vista **técnico**, se a aplicação trata dados pessoais e financeiros com
minimização, mascaramento, controle de saída, retenção definida e capacidade de exclusão — e se
nenhum desses dados vaza para logs, repositório, fixtures, serviços externos ou arquivos esquecidos.
**Processo formal de conformidade legal (LGPD: bases legais, DPO, RIPD, contratos, políticas) está
fora de escopo**; práticas técnicas alinhadas aos princípios da LGPD (finalidade, necessidade,
segurança, prevenção, transparência) estão dentro.

## Quando usar
- Auditar o tratamento de dados pessoais/financeiros antes de considerar a aplicação pronta.
- Validar uma **nova funcionalidade** que coleta, exibe, exporta, importa ou envia dados pessoais.
- Implementar/verificar exclusão ou anonimização de pessoa e dados vinculados.
- Revisar exportações, relatórios, PDFs, prints para documentação, fixtures e seeds.

## Quando NÃO usar
- Parecer jurídico, políticas de privacidade, termos de uso, bases legais ou relação com titulares (fora de escopo).
- Autenticação, autorização, multiusuário/multi-tenant (fora de escopo desta skill).
- Pentest, exploração de vazamento ou varredura de segredos com validação ativa → `qa-appsec`.
- Redigir dados em screenshots já existentes → skill dedicada de redação de imagens, se houver.

---

## Princípios obrigatórios (inegociáveis)

1. **Não alterar regras de negócio, funcionalidades ou comportamento visível sem solicitação explícita do usuário** (inclui o que é exibido, exportado ou apagado).
2. **Divergência encontrada vira achado com evidência e proposta** — nunca correção silenciosa.
3. **Modo padrão `review` é somente leitura.**
4. **`fix` só com pedido explícito e confirmação**; mudanças mínimas, com teste que **falha antes e passa depois**.
5. **Diferenciar análise teórica de teste efetivamente executado.**
6. **Nunca chamar serviços externos reais em testes automatizados** — usar mocks e capturar o que *seria* enviado.
7. **Nunca usar dados reais ou pessoais em fixtures, seeds, exemplos ou relatórios**; usar dados fictícios (CPF gerado válido e marcado como fictício, nomes genéricos).
8. **Nunca abrir, copiar ou exibir o conteúdo de bancos, planilhas, backups ou arquivos de configuração com segredos** do usuário para "comprovar" um achado: evidenciar pelo código, pelo caminho e pelo tipo do arquivo.
9. **Exclusão de dados reais só com pedido explícito**, backup prévio e confirmação.
10. **Informar limitações** (ex.: backups antigos não podem ser expurgados; criptografia de disco depende do SO).

---

## Modos de operação

Sem modo informado, use **`review`**. Pedido de "corrigir" sem modo → confirme antes de usar `fix`.

| Modo | Faz | Não faz |
|---|---|---|
| `review` (padrão) | Monta inventário de dados, mapeia fluxos de saída, aplica o checklist, gera relatório | Não modifica arquivos; não abre bases/planilhas reais |
| `test` | Executa testes existentes; cria testes **em arquivos próprios** com dados fictícios (mascaramento, exportação, exclusão em cascata, ausência de PII em logs e chamadas externas) | Não altera código produtivo |
| `fix` | Corrige achados comprovados (ex.: CPF em log, seed com dado real, `.gitignore` incompleto, temporário não apagado) com diff mínimo e regressão | Não muda o que é exibido/exportado/apagado sem pedido |

---

## Fluxo de trabalho

1. **Inventário de dados** — a partir de models, schemas, importadores e telas: quais dados pessoais/financeiros existem, classificação (identificador, pessoal, financeiro, de terceiros/familiares), onde são armazenados (tabelas, arquivos, cache, localStorage), finalidade e quem os lê.
2. **Fluxo de dados** — origem → coleta/importação → processamento → armazenamento → exibição/exportação → envio externo → retenção → descarte. Use o mapa de [data-leakage-prevention](../qa-appsec/checklists/data-leakage-prevention.md).
3. **Canais de saída** — UI, exportações (CSV/XLSX/PDF), relatórios, logs, mensagens de erro, pacote de diagnóstico, área de transferência, impressão, chamadas externas, backups, temporários.
4. **Capacidade de exclusão** — o que acontece ao apagar uma pessoa: cascata, órfãos, arquivos, backups.
5. **Repouso e repositório** — local do banco, criptografia, `.gitignore`, segredos, histórico Git, fixtures e seeds.
6. **Checklist** — [references/checklist.md](references/checklist.md).
7. **Testes** (`test`/`fix`) e **relatório** em [templates/relatorio.md](templates/relatorio.md).

---

## Checklist

Checklist completo: [references/checklist.md](references/checklist.md).
Não duplicar — referenciar:
[qa-appsec/checklists/data-leakage-prevention.md](../qa-appsec/checklists/data-leakage-prevention.md) (canais de vazamento) e
[qa-appsec/checklists/secrets-and-data-protection.md](../qa-appsec/checklists/secrets-and-data-protection.md) (segredos e proteção de dados).

Achados mais comuns:
- Documento completo exibido em listas/exportações sem necessidade; dado pessoal em log.
- Exportação/backup gravado em pasta sincronizada sem aviso.
- Exclusão de pessoa deixa lançamentos, anexos ou arquivos órfãos.
- Fixture/seed/print de documentação com dado real.
- Banco, planilhas ou backups não ignorados no Git.
- Arquivo de importação mantido em diretório temporário após processamento.

---

## Validação de novas funcionalidades

Toda funcionalidade que toca dados pessoais/financeiros só é aceita com:
- [ ] Inventário atualizado (campo, classificação, finalidade, onde fica, retenção).
- [ ] Minimização justificada: o dado é necessário? precisa ser completo? (ex.: só os últimos dígitos).
- [ ] Mascaramento definido em UI, exportação, logs e mensagens de erro.
- [ ] Exportações com dados pessoais avisam o usuário e marcam o arquivo (nome/cabeçalho "contém dados pessoais").
- [ ] Exclusão da pessoa remove/anonimiza o novo dado (teste de cascata).
- [ ] Nenhum dado pessoal enviado a serviços externos (teste captura a requisição mockada).
- [ ] Temporários removidos após uso (teste verifica o diretório).
- [ ] Fixtures e seeds só com dados fictícios.

---

## Entregáveis

Gerados em `qa-report/privacidade-dados/` na raiz do projeto (não comitar sem pedido):
- `relatorio.md` — a partir de [templates/relatorio.md](templates/relatorio.md): inventário de dados, mapa de saídas, matriz de exclusão, achados `PRIV-XXX` (severidade **Crítica/Alta/Média/Baixa/Informativa**, evidência, proposta, status), testes e limitações.
- `evidencias/` — saídas de testes com dados fictícios, diffs (modo `fix`). **Nunca** dados reais.

Severidade de referência: **Crítica** = dado pessoal real versionado/enviado a terceiro, banco ou backup no repositório; **Alta** = dado pessoal em log, exclusão incompleta, exportação sem aviso em local sincronizado; **Média** = falta de mascaramento em UI/exportação, temporários retidos; **Baixa** = inventário incompleto, documentação de limitação ausente; **Informativa** = criptografia opcional do banco, melhorias.

---

## Integração com outras skills

| Skill | Relação |
|---|---|
| `prontidao-producao` | Orquestrador/gate: consome o relatório desta skill no parecer de prontidão |
| `qa-appsec` | Segredos, vazamento, varredura de histórico Git e proteção de dados (checklists referenciados) |
| `qa-application-auditor` | Temporários e arquivos crescendo em disco |
| `observabilidade-logs` | Mascaramento em logs e pacote de diagnóstico sem dados pessoais |
| `integracoes-externas` | Confirmar que só identificadores públicos saem para provedores |
| `backup-recuperacao` | Local, proteção e retenção de backups; limitação de expurgo |
| `migracoes-banco` | Cascatas/`ON DELETE` e anonimização em migrações |
| `testes-e2e` | Fluxos de exclusão e exportação com dados fictícios |
| `web-ux-acessibilidade` | Avisos, confirmações e mascaramento visual |
| `documentacao-funcional` | Inventário de dados, limitações de exclusão e orientações ao usuário |
| `ci-cd-release` | Secret scanning e bloqueio de arquivos de dados no pipeline |
| `software-engineering-refactoring` | Centralizar mascaramento/formatadores quando houver duplicação |
