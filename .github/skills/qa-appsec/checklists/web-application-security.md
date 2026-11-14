# Segurança de aplicações web

## Escopo
Frontend, backend web, sessão, navegadores, assets, formulários, upload/download e configuração de
origem. Revisão estática por padrão.

## Revisão
- Entradas são validadas no servidor conforme tipo, formato, tamanho e contexto?
- Templates escapam saída de acordo com o contexto; conteúdo rico usa sanitização apropriada?
- Operações que mudam estado têm proteção contra requisições cruzadas e validação de origem?
- Cookies de sessão usam atributos seguros, escopo restrito, expiração e revogação?
- Políticas de origem, CSP, HSTS, frame e MIME são deliberadas e compatíveis com o produto?
- Redirecionamentos, CORS, cache e resolução de host não ampliam confiança ou exposição?
- Upload/download limita tipo, tamanho, armazenamento, nomes, acesso e retenção?
- Erros não exibem stack traces, configuração, tokens ou dados de outros usuários?
- Secrets e dados sensíveis estão ausentes de HTML, bundles, source maps, URLs e storage do cliente?
- Rotas administrativas e recursos por usuário são autorizados no servidor?

## Evidência e validação
Referenciar código/configuração/rota e dados fictícios. Validações dinâmicas só em ambiente local ou
autorizado, sem dados reais; registrar resultado e escopo. Não executar payloads ou exploração contra
ambiente real.