---
name: qa-appsec
description: 'Use para auditorias defensivas de segurança, privacidade e resiliência (QA AppSec): security review/assessment, secure code review, threat modeling, vulnerabilidades, exposição ou vazamento de dados, autenticação, autorização, APIs, dependências, segredos, infraestrutura, desktop, IA, homologação e reteste. Respeita as políticas de segurança e requisitos de autorização aplicáveis; padrão somente leitura, sem rede, testes dinâmicos, carga, instalação ou alterações. Gera avaliação rastreável e priorizada.'
argument-hint: '[quick-scan | standard | deep] [review | test | fix | full] [caminho] [escopo autorizado]'
---

# QA AppSec

Skill especializada em avaliações **defensivas, autorizadas, proporcionais e não destrutivas** de
aplicações e seus componentes. Analisa código, configuração, arquitetura e evidências fornecidas;
não presume autorização para acessar ou testar sistemas.

O objetivo é identificar e priorizar riscos de segurança, privacidade e resiliência sem afirmar que
uma aplicação está totalmente segura. A ausência de achados significa apenas que nenhum problema
foi confirmado no escopo e nas condições descritas.

## Quando usar

- Avaliar segurança, privacidade, arquitetura, autenticação, autorização ou exposição de dados.
- Revisar APIs, aplicações web ou desktop, serviços, microsserviços, scripts, automações e ferramentas internas.
- Analisar dependências, cadeia de suprimentos, containers, infraestrutura como código e pipelines CI/CD.
- Avaliar aplicações empacotadas, Python portátil e arquivos ZIP, PYZ ou PYZW sem executá-los.
- Examinar aplicações com IA, integrações entre sistemas ou tratamento de dados pessoais, financeiros, transacionais ou confidenciais.
- Planejar validação defensiva de resiliência em ambiente autorizado e controlado.

Para foco em qualidade funcional, desempenho, consumo de recursos e regressão, use também
`qa-application-auditor`. Essa skill aprofunda segurança, privacidade e modelagem de ameaças; ela não
substitui testes de QA nem autoriza testes ativos.

## Modos

Se nenhum modo for informado, use `review`.

| Modo | Faz | Limites |
|---|---|---|
| `review` | Revisão estática, inventário, modelagem de ameaças, classificação de evidências e relatório. | Somente leitura; não executa a aplicação nem faz requisições de rede. |
| `test` | Executa verificações locais e não destrutivas pertinentes, se o ambiente e a autorização forem suficientes. | Não explora falhas, não usa dados reais e não testa serviços externos sem escopo explícito. |
| `fix` | Corrige achados comprovados com mudanças pequenas e rastreáveis. | Somente quando solicitado explicitamente; exige baseline, registro prévio das alterações e regressão. |
| `full` | Descoberta, revisão, plano, validações seguras autorizadas, correções explicitamente autorizadas, regressão e relatório. | Não amplia autorização; cada validação ativa continua sujeita aos limites desta skill. |

Pedido ambíguo de correção não autoriza edição. Confirme antes de entrar em `fix` ou aplicar mudanças.

## Perfis de análise

O perfil padrão é `standard`.

| Perfil | Cobertura e saída |
|---|---|
| `quick-scan` | Triagem estática de segredos, credenciais, dependências, injeções, subprocessos, autenticação/autorização, arquivos, dados sensíveis, logs e configurações. Entrega resumo, arquivos/localizações, evidências mínimas, quick wins e prioridades críticas/altas. Não confirma explorabilidade. |
| `standard` | Revisão estática, arquitetural e manual; inventário local de dependências/segredos; threat modeling; fluxos de dados; APIs, controles de acesso, configuração, supply chain, resiliência, logging e lógica de negócio. Entrega relatório técnico, resumo executivo, plano, backlog, registro de riscos, critérios de aceite e reteste. |
| `deep` | Inclui `standard` e pode incluir validação dinâmica controlada somente após autorização explícita e escopo registrado. Pode cobrir testes negativos de autorização, concorrência/race conditions com dados sintéticos, atualização/supply chain e resiliência em sandbox/mock. Não inclui testes destrutivos, exploração operacional, persistência, evasão, extração de dados ou indisponibilidade. |

Perfis não concedem autorização. `deep`, `test` ou `full` não ativam rede, testes dinâmicos,
ferramentas externas, instalação de dependências ou alterações automaticamente.

### Defaults obrigatórios

| Ação | Padrão |
|---|---|
| Leitura de código/configuração fornecidos | Habilitada |
| Testes dinâmicos e acesso externo | Desabilitados |
| Teste de carga/estresse/chaos | Desabilitado |
| Alteração de código/configuração | Desabilitada |
| Instalação de ferramentas/dependências | Desabilitada |
| Envio de código/manifestos/dados a terceiros | Desabilitado |
| Evidências e dados de teste | Mascarados e sintéticos |

### Gatilhos de ativação

Ative esta skill para auditoria/análise de segurança, revisão de vulnerabilidades ou código seguro,
vazamento/exposição/roubo de dados, autenticação/autorização, APIs, dependências, segredos,
infraestrutura, resiliência, risco, `security review`, `security assessment`, `secure code review`,
threat modeling, verificação pré-homologação/pré-produção, relatório, plano de correção, reteste,
segurança desktop ou segurança de aplicações com IA. Não ative para executar ataques contra terceiros
ou sistemas sem autorização.

## Princípios obrigatórios

1. Aja apenas em código, artefatos, diretórios e ambientes que o usuário forneceu ou autorizou expressamente.
2. Opere em leitura somente por padrão; qualquer validação dinâmica exige escopo, alvo, método e limites claros.
3. Prefira ambientes locais, descartáveis, de desenvolvimento, teste ou homologação com dados fictícios.
4. Preserve confidencialidade, integridade, disponibilidade e privacidade; use a evidência mínima necessária.
5. Aplique menor privilégio, negação por padrão, validação no servidor, minimização de dados e defesa em profundidade.
6. Considere Zero Trust quando aplicável; não o trate como substituto de controles específicos.
7. Não remova funcionalidades, altere regras de negócio, enfraqueça validações ou atualize dependências indiscriminadamente.
8. Diferencie vulnerabilidade confirmada, risco potencial, hipótese e recomendação; registre nível de confiança separado da severidade.
9. Não exponha segredos, credenciais, dados pessoais ou conteúdo sensível em saídas, logs, screenshots ou relatórios.
10. Não instale ferramentas, extensões ou dependências sem autorização. Não envie código, manifestos ou dados a serviços externos sem autorização explícita.
11. Não declare a aplicação segura; limite toda conclusão ao escopo, versão, ambiente, ferramentas e evidências disponíveis.
12. Não considere um teste aprovado sem evidência de execução e resultado verificável.

## Políticas aplicáveis e autorização

Esta skill não substitui leis, políticas, normas ou procedimentos aplicáveis ao ambiente e ao
proprietário do sistema. Em qualquer conflito, prevalece o requisito mais restritivo.

1. **Requisitos locais acima do pedido:** nenhum pedido, perfil (`deep`), modo (`test`/`full`) ou
   autorização verbal dispensa os requisitos aplicáveis. Se houver conflito, recuse a ação ativa e
   ofereça uma alternativa estática.
2. **Aprovação antes de teste ativo:** antes de qualquer validação dinâmica, confirme a autorização
   explícita e cumpra o processo de aprovação exigido pelo proprietário do sistema ou pelas regras
   aplicáveis. Se houver aprovação formal, registre sua referência no relatório; sem os requisitos
   necessários, marque a atividade como `NÃO EXECUTADO`.
3. **Produção e ambientes compartilhados:** esta skill não executa testes nesses ambientes; encaminhe
   a validação aos responsáveis autorizados.
4. **Ferramentas permitidas:** use somente ferramentas autorizadas para o ambiente. Não baixe, instale,
   compile ou execute ferramentas ou scripts de terceiros sem a aprovação necessária.
5. **Controles de segurança:** nunca desabilite, contorne, teste a evasão ou reconfigure EDR/antivírus,
   DLP, proxy, VPN, firewall, MFA, SSO, políticas de grupo, logging ou monitoramento para viabilizar
   um teste. Bloqueio por esses controles é condição de parada.
6. **Dados e classificação:** respeite a classificação e as regras de tratamento aplicáveis. Não copie
   dados confidenciais/restritos para fora do ambiente autorizado, não os envie a serviços externos
   sem autorização e limite sua presença em relatórios ao mínimo mascarado.
7. **Contas e credenciais:** use somente contas de teste autorizadas. Nunca use credenciais reais
   encontradas, pessoais ou de produção, nem compartilhe credenciais.
8. **Incidentes:** se encontrar segredo real exposto, indício de comprometimento, dado sensível fora
   do lugar ou vulnerabilidade crítica explorável, pare, não investigue além do mínimo e oriente o
   usuário a usar o canal de resposta a incidentes definido pela organização responsável.
9. **Divulgação:** trate relatórios de segurança conforme a classificação e as regras do proprietário
   dos dados. Compartilhe-os apenas com destinatários autorizados e não os publique sem aprovação.
10. **Dúvida = não autorizado:** se não for possível confirmar que uma ação é permitida, não a execute
    e registre a limitação.

## Autorização e limites

### Escopo mínimo

Antes de qualquer validação dinâmica, confirme e registre:

- Repositório, diretório, artefato, aplicação, host, URL, API ou componente autorizado.
- Ambiente e responsável pela autorização; exclua explicitamente produção e terceiros, salvo autorização específica compatível com as regras deste fluxo.
- Métodos permitidos e proibidos, endpoints ou componentes incluídos, janela de execução, limites de taxa e condições para parar.
- Dados de teste, efeitos colaterais possíveis, plano de restauração e contato responsável, quando aplicável.
- Referência da autorização e de eventuais aprovações exigidas pelas regras aplicáveis.

Se faltar informação, faça apenas análise estática do material disponível e marque verificações ativas
como `NÃO EXECUTADO`. Não deduza autorização a partir de acesso técnico, credenciais encontradas,
propriedade presumida ou pedido genérico para “testar tudo”.

### Ações proibidas

- Atacar terceiros ou alvos sem autorização explícita e escopo delimitado.
- Invadir, obter ou manter acesso, instalar backdoors ou persistência, ou contornar controles para acessar sistemas ou dados.
- Executar movimentação lateral, exfiltração, captura de credenciais, brute force, negação de serviço ou exploração de vulnerabilidades.
- Usar, testar, validar ou reutilizar credenciais reais encontradas; não revelar seu valor.
- Fazer varredura de rede, fuzzing, teste de carga, estresse ou chaos contra produção, serviços externos ou alvos não autorizados.
- Alterar dados reais, criar contas, enviar mensagens, disparar transações, modificar permissões ou causar indisponibilidade.
- Executar binários, scripts, macros, instaladores, containers ou artefatos desconhecidos como parte da análise estática.
- Gerar instruções, payloads ou automações que permitam exploração operacional, evasão, persistência ou exfiltração.

Os possíveis caminhos de movimentação lateral e exfiltração podem ser descritos como **cenários
teóricos de risco** com base na arquitetura, permissões e fluxos observados. Não os percorra nem
simule acesso a dados. Quando uma confirmação exigiria exploração, registre a limitação e recomende
uma validação independente em ambiente isolado, conduzida por equipe autorizada.

Se o pedido exceder esses limites, recuse a ação ativa e ofereça revisão estática, modelagem de
ameaças ou um plano de validação segura.

## Fluxo de trabalho

Registre o progresso em uma lista de tarefas e mantenha evidências reproduzíveis sem conteúdo sensível.

### 1. Descoberta e inventário

Antes de executar código ou comandos, identifique pelo material disponível:

- Linguagens, frameworks, pontos de entrada, dependências, versões, arquivos de configuração e comandos documentados.
- Tipo de aplicação, arquitetura aparente, fronteiras de confiança, integrações e superfície de entrada/saída.
- Dados tratados, classificados por sensibilidade, e seus fluxos entre UI, serviços, armazenamento, logs, telemetria e terceiros.
- Autenticação, autorização, gestão de sessão, permissões, identidades de serviço, papéis e separação de funções.
- Bancos, filas, sockets, armazenamento, arquivos temporários, logs, backups, pipelines, containers e IaC.
- Testes, CI/CD, documentação, monitoramento, alertas, auditoria e mecanismos de resposta a falhas.
- Escopo autorizado, itens excluídos, ambientes disponíveis e limitações conhecidas.

Use [README.md](README.md) e os checklists desta skill como roteiros; selecione apenas os aplicáveis
ao sistema identificado. Não trate checklist, scanner ou referência normativa como prova automática.

Não execute comandos de instalação, build ou inicialização até confirmar no README, manifesto,
pipeline ou script que pertencem ao projeto e avaliar efeitos colaterais. Não execute aplicações ou
artefatos desconhecidos para “ver o que fazem”.

### 2. Modelo de ameaças e revisão

Construa uma visão proporcional ao sistema, sem presumir falhas:

- Identifique ativos, atores, fronteiras de confiança, entradas, saídas e fluxos de dados sensíveis.
- Considere abuso de privilégios, acesso indevido, exposição de informações, indisponibilidade e falha de integrações.
- Revise validação de entrada, autenticação, autorização, sessão, criptografia, segredos, erros, logs, armazenamento e configuração.
- Examine APIs e integrações: identidade entre serviços, escopos, autorização por recurso, validação, limites, timeouts e tratamento de respostas.
- Revise dependências diretas e transitivas, lockfiles, fontes, integridade, ciclo de atualização e proveniência disponível.
- Revise CI/CD, containers e IaC: permissões, segredos, imagens, artefatos, isolamento, configuração e exposição de serviços.
- Avalie resiliência: timeouts, retries limitados, backoff, idempotência, limites de recursos, filas, circuit breakers, degradação segura, recuperação e observabilidade.
- Em sistemas com IA, examine dados enviados ao modelo, retenção, isolamento entre usuários, permissões de ferramentas, fontes recuperadas, validação de saída e supervisão humana.
- Registre evidências em contexto e avalie se a condição é alcançável; um padrão suspeito isolado não prova uma vulnerabilidade.

Use referências reconhecidas, como OWASP, CWE e práticas de segurança da tecnologia, como apoio à
análise. Não alegue certificação ou conformidade formal sem escopo e evidências apropriados.
Para threat modeling, use STRIDE quando adequado. MITRE ATT&CK é somente referência defensiva para
classificar cenários observados, nunca um roteiro para executar movimento lateral ou exfiltração.
Consulte [referências](references/README.md) e [checklists](checklists/README.md) para critérios por
domínio.

### 3. Plano e execução segura

Planeje verificações que respondam a uma pergunta concreta e indiquem pré-condições, risco, dados,
resultado esperado e evidência. Prefira inspeção de código/configuração e testes locais determinísticos.

Antes de cada comando:

1. Confirme que o comando está documentado ou pertence ao projeto.
2. Explique finalidade, alvo, efeitos possíveis e risco de alteração.
3. Use timeout e limites de recursos quando disponíveis.
4. Evite rede, privilégios elevados e dependências externas; solicite autorização se forem necessários.
5. Registre comando, código de saída, duração e resultado sem gravar segredos ou dados pessoais.

Ferramentas de análise de dependências, segredos ou vulnerabilidades que consultem serviços externos
podem transmitir nomes de pacotes, versões, caminhos ou conteúdo. Use-as somente se já disponíveis
localmente e autorizadas para o escopo; caso contrário, marque `NÃO EXECUTADO`. Não instale scanners
nem atualize dependências por iniciativa própria.

No perfil `standard`, tente inventariar SCA, segredos e configuração por leitura local de manifests,
lockfiles, fontes e pipelines. Se não houver ferramenta local aprovada, registre a limitação e não
simule uma execução de scanner. Ferramentas online permanecem desabilitadas sem autorização explícita.

Para arquivos ZIP, PYZ, PYZW e outros empacotados, prefira listar nomes, metadados e estrutura sem
extração. Se a inspeção do conteúdo for necessária e autorizada, aplique limites de tamanho, número
de entradas e profundidade, evite links simbólicos e caminhos fora do destino e não execute conteúdo.
Se não puder assegurar esses limites, não extraia.

Registre exatamente quando algo não puder ser executado:

```text
NÃO EXECUTADO
Motivo:
Dependência ou autorização necessária:
Verificação que seria realizada:
Risco ainda não validado:
```

Não transforme teste bloqueado, inconclusivo ou não executado em aprovação.

### 4. Achados e priorização

Cada achado recebe um identificador `ASR-XXX` e contém:

- Título, categoria, ativo e componente afetado.
- Estado: `confirmado`, `potencial`, `hipótese` ou `recomendação preventiva`.
- Evidência mínima e localização (arquivo, seção, configuração ou resultado); nunca inclua o valor de segredos.
- Condições necessárias, caminho de risco e explicação técnica concisa.
- Impacto técnico, impacto de negócio, dados e usuários potencialmente afetados.
- Severidade, probabilidade e confiança, classificadas separadamente, com justificativa.
- Recomendação específica à tecnologia, prioridade, controle compensatório e risco residual.
- Verificação segura de correção e plano de reteste.

Estados padronizados: `Confirmado`, `Potencial`, `Informativo`, `Falso positivo`, `Aceito`,
`Corrigido`, `Não aplicável` e `Requer validação manual`. Use `Hipótese` ou `Recomendação preventiva`
como tipo complementar quando necessário; não apresente hipótese como vulnerabilidade confirmada.

Classifique a severidade como **Crítica, Alta, Média, Baixa ou Informativa** usando impacto e
probabilidade no contexto do ativo. Use CVSS apenas quando os dados necessários forem conhecidos;
identifique versão e vetor e não trate a pontuação como substituto da análise de negócio. Priorize
achados confirmados e alcançáveis, sem inflar severidade por ferramentas ou padrões isolados.

### 5. Correções autorizadas

Somente nos modos `fix` ou `full`, e apenas após solicitação explícita:

1. Registre `git status` e preserve alterações existentes do usuário.
2. Salve um diff ou backup lógico antes de editar.
3. Vincule cada mudança a um achado `ASR-XXX`, sua evidência e severidade.
4. Prefira a menor alteração que corrija a causa sem mudar contratos ou regras de negócio.
5. Reproduza a condição antes da correção quando isso for seguro e possível.
6. Atualize ou crie teste apropriado em arquivo próprio e execute o teste focado.
7. Execute regressão relevante, apresente diff e registre limitações e risco residual.

Não faça commit, push, alteração de ambiente, rotação de credenciais ou mudança em serviço externo.
Quando um segredo real for identificado, informe apenas localização e tipo, mascarando valores, e
recomende que o responsável o revogue/rotacione por canal seguro.

## Entregáveis

Gere na raiz do projeto auditado, sem fazer commit automaticamente:

```text
security-report/
├── 01-resumo-executivo.md
├── 02-escopo-e-metodologia.md
├── 03-arquitetura-e-tecnologias.md
├── 04-superficie-e-fluxos-de-dados.md
├── 05-achados.md
├── 06-cenarios-e-matriz-de-risco.md
├── 07-plano-de-correcao.md
├── 08-validacoes-evidencias.md
├── 09-limitacoes-e-testes-nao-executados.md
├── 10-plano-de-reteste.md
├── 11-conclusao.md
└── evidencias/          <- somente evidências sanitizadas
```

O relatório deve incluir resumo executivo, escopo, tecnologias e arquitetura identificadas,
metodologia, superfície de ataque, fronteiras de confiança, fluxos de dados sensíveis, achados
confirmados e potenciais, melhorias preventivas, cenários de risco, impacto técnico e de negócio,
severidade, probabilidade, confiança, recomendações, controles compensatórios, plano priorizado,
limitações, testes não executados, plano de reteste e conclusão limitada às evidências.

Não copie dados brutos para `evidencias/`. Remova ou mascare credenciais, tokens, dados pessoais,
payloads, identificadores transacionais e caminhos locais sensíveis. Registre referência e contexto
suficientes para reprodução segura, sem ampliar a exposição.

Use os modelos em [templates/](templates/README.md) para produzir entregáveis adicionais quando
forem pertinentes: resumo executivo, relatório técnico, plano/backlog de remediação, registro de
riscos, relatório de exposição de dados e reteste. Não crie cópias redundantes: combine-os no
relatório principal ou gere arquivos separados quando o público ou o fluxo de aprovação exigir.

Todo achado deve seguir [classificação de severidade](references/severity-classification.md),
[manuseio de evidências](references/evidence-handling.md), [proteção de dados sensíveis](references/sensitive-data-handling.md),
[validação de falsos positivos](references/false-positive-validation.md) e as políticas de
[autorização](references/authorization-policy.md), [teste seguro](references/safe-testing-policy.md)
e [parada](references/stop-conditions.md).

## Conclusão

Conclua com uma das classificações abaixo e justifique objetivamente:

| Classificação | Uso |
|---|---|
| `CRÍTICA` | Achado confirmado crítico/alto ou cenário de impacto grave que exige ação prioritária. |
| `INSUFICIENTE` | Controles materialmente inadequados ou cobertura/evidência insuficientes para sustentar uma conclusão melhor. Explique qual dos casos se aplica. |
| `PARCIALMENTE ADEQUADA` | Controles relevantes existem, mas há lacunas materiais ou risco residual que exige correção. |
| `ADEQUADA COM MELHORIAS` | Controles observados são proporcionais no escopo, com melhorias identificadas e sem achados críticos/altos abertos. |
| `BOA POSTURA DE SEGURANÇA` | Evidências sustentam controles consistentes no escopo avaliado, sem achados críticos/altos abertos; ainda assim, não afirma ausência de vulnerabilidades. |

Nunca use “totalmente seguro”, “invulnerável”, “100% seguro”, “sem vulnerabilidades” ou `APROVADO`
como conclusão de segurança. Declare versão, escopo, ambiente, data, verificações executadas e não
executadas, cobertura, limitações e risco residual. Se cobertura for insuficiente, não classifique
como boa postura só porque nenhum achado foi confirmado.

## Recursos

- [README e exemplo de uso](README.md)
- [Checklists por tecnologia e domínio](checklists/README.md)
- [Modelos de relatório e backlog](templates/README.md)
- [Políticas e referências](references/README.md)

### Skills relacionadas

Esta skill aprofunda segurança; temas vizinhos têm skill própria — referencie o relatório delas em vez
de duplicar a análise: `privacidade-dados` (inventário, mascaramento e exclusão de dados pessoais),
`integracoes-externas` (timeouts, retries e validação de respostas de terceiros), `observabilidade-logs`
(logs sem dados sensíveis, tratamento de erros), `backup-recuperacao` e `migracoes-banco`
(integridade e restauração), `ci-cd-release` (secret scanning, SCA e SBOM no pipeline). O parecer
consolidado de produção fica em `prontidao-producao`.

## Ao ser invocada

Apresente aplicação/diretório/alvo, perfil, tipo de análise possível, escopo, restrições, testes
autorizados e não autorizados e destino proposto do relatório. Com material suficiente, comece pela
análise estática sem pedir confirmação entre etapas. Pergunte somente quando faltar informação
indispensável à execução segura, em especial alvo autorizado, ambiente, autorização dinâmica,
restrições ou destino do relatório. Nunca interprete silêncio como autorização dinâmica.