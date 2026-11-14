# Segredos e proteção de dados

## Identificação e tratamento
- Procurar referências a credenciais, tokens, cookies, chaves, certificados, connection strings e PII.
- Verificar se configuração separa segredo de código e se o acesso é limitado por identidade/função.
- Avaliar rotação, revogação, expiração, armazenamento e fornecimento em runtime.
- Verificar criptografia em trânsito/repouso, gestão de chaves, rotação e validação de certificados.
- Revisar logs, erros, telemetria, URLs, temporários, cache, backups, dumps e arquivos de build.
- Verificar minimização, finalidade, acesso, retenção e descarte dos dados.

## Regra de evidência
Nunca revelar nem reutilizar o valor encontrado. Registrar somente tipo, localização e contexto
sanitizado; limitar a exibição a trecho mascarado se indispensável. Não testar credenciais. Para segredo
real, recomendar revogação/rotação pelo responsável por canal seguro.