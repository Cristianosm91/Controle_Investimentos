# Segurança de código-fonte

## Revisão estática
- Validação de entrada e codificação de saída são feitas no contexto correto?
- Consultas de banco usam APIs parametrizadas e escopo de autorização explícito?
- Processos externos recebem argumentos controlados sem composição insegura de comandos?
- Desserialização, reflexão, templates e carregamento dinâmico restringem fontes e formatos?
- Caminhos de arquivo são confinados ao destino esperado e operações têm permissões mínimas?
- Erros e exceções falham de forma segura sem ocultar sinais operacionais relevantes?
- Criptografia usa bibliotecas e configurações aprovadas; segredos ficam fora do código?
- Concorrência, transações, idempotência e estados preservam invariantes de negócio?
- Bibliotecas externas, entrada do usuário e conteúdo de IA são tratados como não confiáveis?
- Há testes para autorização, limites, falhas e comportamentos negativos seguros?

## Revisão de evidências
Vincular fluxo de origem, validação, operação sensível e controle. Um padrão ou alerta de ferramenta
isolado não confirma exploração; revisar alcançabilidade, sanitização e contexto. Não executar código
desconhecido para confirmar uma hipótese.