# Segurança de APIs

## Inventário
- API, versão, transporte, endpoints, consumidores, identidades e dados tratados.
- Esquemas, autenticação, autorização por objeto/função/propriedade e limites documentados.

## Revisão
- Cada endpoint aplica autenticação e autorização no servidor, inclusive operações internas?
- O acesso é limitado ao objeto, tenant, função e campos autorizados para a identidade?
- Respostas retornam somente propriedades necessárias; erros não revelam dados internos?
- Entradas, tipos, tamanho, paginação, filtros e ordenação são validados e limitados?
- Mudanças de estado contemplam idempotência, replay, concorrência e transições válidas?
- Existem rate limits proporcionais e limites de recursos, sem confiar apenas no cliente?
- Webhooks verificam origem/autenticidade, integridade e repetição dentro do desenho do sistema?
- CORS, TLS, versões antigas, GraphQL introspection e endpoints administrativos estão deliberados?
- Chamadas a URLs fornecidas são limitadas a destinos autorizados e tratam redirecionamentos com segurança?
- Terceiros são tratados como não confiáveis e suas respostas são validadas?

## Saída
Registrar endpoint e controle observado por referência, sem tokens ou dados reais. Marcar lacunas como
potenciais quando não houver evidência suficiente. Testar somente com autorização explícita, dados
sintéticos e limites baixos documentados.