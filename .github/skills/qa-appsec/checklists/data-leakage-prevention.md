# Prevenção de exposição e vazamento de dados

## Mapa de dados
Classificar dados pessoais, financeiros, bancários, transacionais, credenciais, tokens, chaves,
segredos, informações operacionais e dados de clientes. Desenhar o fluxo:

```text
ORIGEM -> COLETA -> PROCESSAMENTO -> ARMAZENAMENTO -> TRANSMISSÃO -> COMPARTILHAMENTO -> DESTINO -> RETENÇÃO -> DESCARTE
```

## Canais a revisar
- APIs, interfaces, endpoints administrativos, exportações, downloads e relatórios.
- Logs, erros, stack traces, telemetria, URLs, headers, cookies, cache e storage local.
- Temporários, backups, dumps, arquivos compactados, diretórios de build e repositórios.
- Filas, webhooks, integrações, analytics, suporte, ferramentas de observabilidade e provedores de IA.
- Acesso entre usuários, funções, clientes/tenants e identidades de serviço.

## Controles
- Minimização, mascaramento, autorização por recurso, criptografia e retenção estão definidos?
- Há alerta/auditoria para exportação, volume anormal e acesso privilegiado?
- Destino, cópias, finalidade e descarte de cada integração são conhecidos?

Nunca extrair dados reais para comprovar exposição. Descrever caminhos potenciais e validar apenas
com dados sintéticos e autorização explícita.