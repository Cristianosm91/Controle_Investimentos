# Manuseio de evidências

## Requisitos
- Evidência mínima necessária, vinculada a um achado e suficiente para revisão independente.
- Registrar fonte, caminho/linha ou componente, versão/commit, data, método e contexto.
- Preservar integridade sem coletar ou copiar dados além do necessário.
- Mascarar segredos, PII, identificadores, URLs privadas e caminhos locais sensíveis.
- Diferenciar saída de ferramenta, observação manual, hipótese e resultado de teste executado.

## Proibições
- Não anexar repositórios inteiros, dumps, logs completos, tokens, credenciais, chaves ou dados reais.
- Não armazenar evidência em serviços externos sem autorização.
- Não executar scripts/binários desconhecidos para obter evidência.
- Não criar evidência manipulada que pareça saída original.

## Registro
Indicar ferramenta/versão e comando autorizado quando pertinente, código de saída, duração e ambiente.
Se uma evidência puder ampliar exposição, não a capture; descreva a localização e restrinja acesso pelo
canal aprovado. Redação e retenção devem seguir política do proprietário dos dados.