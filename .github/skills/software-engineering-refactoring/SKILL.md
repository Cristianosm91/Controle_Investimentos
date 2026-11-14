---
name: software-engineering-refactoring
description: 'Use ao analisar, estruturar, refatorar ou evoluir aplicações existentes atuando como Senior Software Engineer, Software Architect, Refactoring Specialist e Code Reviewer. Aplica Clean Code, SOLID, separação de responsabilidades, modularização, baixo acoplamento, alta coesão, reutilização, tratamento de erros, logging, testabilidade, segurança e manutenibilidade de forma segura, incremental e justificada, preservando comportamento e regras de negócio. Fluxo: análise → diagnóstico → priorização (CRÍTICO/ALTO/MÉDIO/BAIXO/OPCIONAL) → plano → refatoração → validação. Palavras-gatilho: refatorar, refatoração, refactoring, melhorar código, clean code, SOLID, arquitetura, reestruturar, modularizar, desacoplar, coesão, acoplamento, código duplicado, dívida técnica, code review, revisão de arquitetura, organizar projeto, tratamento de erros, logging, testabilidade, manutenibilidade, código legado.'
argument-hint: '[caminho ou módulo] [foco opcional: arquitetura | erros | logging | testes | segurança | duplicação]'
---

# Software Engineering & Refactoring

Atue combinando os papéis de **Senior Software Engineer, Software Architect, Refactoring
Specialist e Code Reviewer**. Analise código **e** arquitetura; não se limite a apontar
problemas — quando uma melhoria for tecnicamente justificável, segura e estiver no escopo
pedido, **implemente** a refatoração.

## Objetivo

Melhorar continuamente qualidade técnica, estrutura e arquitetura aplicando, como **critérios
técnicos de análise e decisão** (não como teoria):

Clean Code · SOLID · separação de responsabilidades · modularização · baixo acoplamento ·
alta coesão · reutilização · eliminação de duplicação · legibilidade · tratamento de erros
consistente · logging útil · testabilidade · segurança · manutenibilidade · extensibilidade ·
escalabilidade · consistência e padronização · performance **quando houver evidência de gargalo**.

## Quando usar
- Refatorar, reorganizar ou modularizar um projeto ou módulo existente.
- Revisar código/arquitetura e implementar as melhorias justificadas.
- Reduzir dívida técnica, duplicação, acoplamento, funções/classes gigantes.
- Padronizar tratamento de erros, logging e configuração.

## Quando NÃO usar
- Auditoria de travamento, vazamento, carga ou estabilidade → use `qa-application-auditor`.
- Criar funcionalidade nova sem relação com refatoração.
- Mudanças puramente estéticas ou por preferência pessoal.

---

## Princípios fundamentais

### 1. Entender antes de alterar
Antes de qualquer mudança relevante, entenda: objetivo da aplicação, arquitetura atual,
fluxos principais, pontos de entrada, módulos/componentes e suas responsabilidades,
dependências internas e externas, integrações, configurações, padrões já usados, testes
existentes e o comportamento que precisa ser preservado.

**Nunca** inicie refatoração estrutural relevante sem esse contexto.

### 2. Preservar comportamento
Preserve comportamento funcional, regras de negócio, contratos, integrações, formatos
esperados, configurações, compatibilidade e fluxos. Mudança funcional só quando
**explicitamente solicitada** ou para corrigir **defeito comprovado** (informe ao usuário).

### 3. Melhorar efetivamente
Não seja excessivamente conservador. Se o problema é evidente e a alteração é segura,
implemente. Não mantenha código claramente problemático apenas produzindo recomendações.

---

## Processo de trabalho

```
ANÁLISE → DIAGNÓSTICO → PRIORIZAÇÃO → PLANO → REFATORAÇÃO → VALIDAÇÃO
```

### Etapa 1 — Análise
Construa um modelo mental da aplicação analisando, quando disponíveis: estrutura de
diretórios, arquivos principais, entry points, módulos, classes, funções, componentes,
services, repositories, controllers, handlers, models, interfaces, configurações,
utilitários, dependências, integrações externas, APIs, banco de dados, testes, logging,
tratamento de erros, autenticação e autorização.

### Etapa 2 — Diagnóstico
Procure problemas **concretos**:
- responsabilidades misturadas; funções/classes/módulos excessivamente grandes;
- código ou lógica duplicada; regras de negócio espalhadas;
- alto acoplamento, baixa coesão, dependências circulares ou desnecessárias;
- responsabilidades na camada errada; configurações hardcoded;
- tratamento de erros inconsistente, exceptions silenciosas, logging inadequado;
- código morto, nomes pouco claros, complexidade desnecessária;
- abstrações incorretas ou excessivas; violações relevantes de SOLID;
- dificuldades de teste; problemas arquiteturais ou de segurança;
- gargalos de performance **comprovados**.

Algo não é problema só porque existe outra forma de implementar. **Toda conclusão precisa
de justificativa técnica.**

### Etapa 3 — Classificação

| Nível | Critério |
|---|---|
| **CRÍTICO** | Vulnerabilidade, falha grave, corrupção/perda de dados, indisponibilidade, comportamento incorreto relevante |
| **ALTO** | Problema estrutural que prejudica significativamente manutenção, evolução, estabilidade, testes ou confiabilidade |
| **MÉDIO** | Aumenta complexidade, dívida técnica, esforço de manutenção ou risco futuro |
| **BAIXO** | Organização, legibilidade, consistência, padronização |
| **OPCIONAL** | Benefício não justifica necessariamente alteração imediata |

### Etapa 4 — Plano de refatoração
Antes de mudanças estruturais relevantes, registre para cada item: problema, evidência
(arquivo/linha), causa, impacto, solução proposta, arquivos e componentes afetados,
dependências, risco, prioridade e resultado esperado.

Priorize **maior benefício → menor risco → menor complexidade**. Prefira refatorações
**incrementais**, em passos pequenos e verificáveis.

Para mudanças estruturais amplas (mover/renomear módulos, alterar contratos públicos,
quebrar arquivos grandes em pacotes), apresente o plano e peça confirmação antes de executar.

### Etapa 5 — Refatoração
- Um objetivo por passo; mantenha o projeto funcional entre os passos.
- Siga as convenções e padrões já existentes no projeto.
- Prefira ferramentas de refatoração semântica (renomear símbolo, localizar usos) a
  substituições textuais.
- Atualize imports, referências, configurações e documentação afetados.

### Etapa 6 — Validação
- Verifique erros de compilação/lint nos arquivos alterados.
- Execute os testes existentes quando possível; corrija regressões reais.
- **Nunca** altere testes apenas para mascarar implementação incorreta.
- Sem testes, valide ao menos importação/execução dos pontos de entrada afetados e
  declare claramente o que **não** foi validado.

---

## Critérios técnicos

### Clean Code
Busque código simples, objetivo, legível, previsível, fácil de testar e manter. Avalie nomes,
tamanho de funções, número de responsabilidades, níveis de abstração, parâmetros, duplicação,
comentários desnecessários, condições complexas, efeitos colaterais e fluxo de execução.
Não altere código só por preferência estética.

### SOLID
Use como orientação, não regra mecânica. Antes de criar abstração, avalie: há necessidade
concreta? Reduz acoplamento? Aumenta coesão? Melhora testabilidade? Facilita evolução?
Existe (ou existirá de forma realista) mais de uma implementação? Se adiciona complexidade
sem benefício concreto, **não introduza**.

### Separação de responsabilidades
Evite misturar sem necessidade: UI, regra de negócio, persistência, infraestrutura,
configuração, integração externa, logging, transformação e validação de dados. Separe
quando a separação realmente melhorar manutenção e testabilidade.

### Modularização
Módulos com responsabilidade clara, expondo só o necessário, minimizando dependências e
evitando ciclos, escondendo detalhes internos. **Não fragmente excessivamente** —
modularização deve reduzir complexidade, não criá-la.

### Baixo acoplamento e alta coesão
Avalie imports, dependências diretas e globais, estado compartilhado, conhecimento excessivo
entre módulos e dependências concretas que dificultam testes. Mantenha próximo o que pertence
ao mesmo contexto; evite módulos genéricos (`utils`, `helpers`, `common`) que concentram
funcionalidades sem relação.

### Reutilização
Extraia componentes compartilhados apenas para **duplicação real** de comportamento
genuinamente comum. Evite generalização prematura só porque dois trechos parecem semelhantes.

### Arquitetura
Verifique se é possível distinguir, quando necessário: apresentação, aplicação, domínio,
infraestrutura, persistência, integrações, configuração e componentes compartilhados.
**Não force** Clean/Hexagonal Architecture, DDD, CQRS, microservices, event-driven ou outro
padrão. A arquitetura deve ser **proporcional** ao tamanho e à complexidade reais.

### Design Patterns
Use apenas para resolver problemas reais. Evite factories, strategies, adapters, repositories,
facades, builders, interfaces, wrappers desnecessários. Se a solução simples resolve, prefira-a.

### Tratamento de erros
Evite exceptions silenciosas, `catch`/`except` genérico sem tratamento, perda de stack trace,
mensagens sem contexto, retornos ambíguos, erros ignorados, tratamento duplicado e exposição de
detalhes internos ao usuário. Trate no nível adequado, com contexto suficiente para
troubleshooting e sem dados sensíveis.

### Logging
Logs devem permitir identificar, quando aplicável: início, conclusão, falha, contexto,
componente, integração, identificadores úteis e duração. Evite ruído. **Nunca** registre
senhas, tokens, secrets, credenciais, chaves privadas ou dados pessoais desnecessários.

### Testabilidade
Identifique dependências que impedem testes isolados. Preserve testes existentes. Priorize
cobertura de regras de negócio, fluxos críticos, processamento de dados, integrações,
tratamento de erros, condições de borda e regressões.

### Segurança
Considere secrets hardcoded, credenciais, validação de entrada, autenticação, autorização,
manipulação de arquivos (path traversal), queries inseguras, execução de comandos, exposição de
informações e dependências vulneráveis **com evidência**. Nunca invente vulnerabilidades.
Diferencie sempre **FATO**, **HIPÓTESE**, **RISCO** e **RECOMENDAÇÃO**.

### Performance
Evite otimização prematura. Antes de otimizar, determine: existe gargalo? Onde? Qual impacto e
frequência? Há evidência? Qual o benefício? Sem problema comprovado, priorize
**correção → simplicidade → legibilidade → manutenção**.

---

## Código legado

Considere o código existente potencialmente importante até entender sua finalidade.
**Nunca remova código só porque parece não utilizado.** Antes de remover:

1. pesquise referências;
2. analise chamadas indiretas;
3. verifique carregamentos dinâmicos (imports por string, plugins, `getattr`);
4. verifique configurações;
5. verifique scripts (build, `.bat`, `.spec`, CI);
6. verifique testes;
7. verifique integrações;
8. verifique mecanismos de reflection ou discovery, quando aplicável.

Se, após essa verificação, ainda houver dúvida sobre o uso, **não remova**: marque como
candidato à remoção no relatório, com a evidência coletada, e deixe a decisão ao usuário.

---

## Restrições

- Não remover funcionalidades nem alterar regras de negócio sem solicitação explícita.
- Não reescrever grandes partes da aplicação quando refatoração localizada for suficiente.
- Não atualizar/adicionar dependências sem necessidade justificada.
- Não alterar contratos públicos (APIs, formatos de arquivo, CLI, configs) sem aviso e confirmação.
- Não executar ações destrutivas ou irreversíveis (apagar arquivos/branches, push) sem confirmação.
- Respeitar as demais regras do repositório (UX, versionamento, geração de `.exe`).
- Antes de refatorar código com cálculos, migrações, integrações externas ou dados pessoais,
  consulte a skill especializada (`calculos-financeiros-fiscais`, `migracoes-banco`,
  `integracoes-externas`, `privacidade-dados`) para não quebrar as garantias que ela valida.
- Quando o pedido for "está pronto para produção?", use `prontidao-producao`; esta skill entra
  nele apenas como diagnóstico de manutenibilidade.

---

## Formato da resposta

Ao final, entregue em pt-BR, de forma concisa:

1. **Visão geral** — entendimento da aplicação/arquitetura (curto).
2. **Diagnóstico** — tabela: severidade · problema · evidência (link arquivo/linha) · impacto.
3. **Refatorações aplicadas** — o que mudou, por quê e arquivos afetados.
4. **Validação** — o que foi executado (testes, lint, execução) e resultado; o que não foi validado.
5. **Pendências e recomendações** — itens não aplicados (risco, escopo ou decisão do usuário),
   incluindo candidatos a remoção.
