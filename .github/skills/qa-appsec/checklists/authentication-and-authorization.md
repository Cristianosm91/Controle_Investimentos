# Autenticação e autorização

## Identidades e autenticação
- Fluxos de login, recuperação, MFA, revogação e logout são documentados e testáveis?
- Senhas são protegidas por mecanismo apropriado; credenciais padrão e segredos fixos estão ausentes?
- Sessões/tokens têm audiência, emissor, escopo, expiração, rotação e revogação coerentes?
- Cookies e armazenamento local reduzem exposição conforme o tipo de cliente?
- Erros de autenticação não revelam contas ou detalhes sensíveis; controles de abuso não bloqueiam usuários legítimos indevidamente?

## Autorização
- O servidor verifica acesso em cada ação, objeto, campo, tenant e transição de estado?
- Papéis e permissões seguem menor privilégio e segregação de funções?
- Tarefas agendadas, jobs, suporte e contas de serviço usam identidades distintas e restritas?
- Operações administrativas/críticas têm proteção reforçada, auditoria e aprovação apropriada?
- A aplicação não confia em controles exclusivamente visuais ou em valores enviados pelo cliente?

## Evidência e teste
Mapear identidade -> decisão -> recurso -> operação. Usar contas sintéticas e papéis de teste somente
com autorização; nunca acessar dados de outro usuário ou testar credenciais reais.