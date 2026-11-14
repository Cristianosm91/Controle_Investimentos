# Segurança de aplicações com IA

## Dados e isolamento
- Dados enviados a provedores/modelos têm finalidade, retenção, região e controles documentados?
- Prompts, contexto RAG, histórico e cache são isolados entre usuários/tenants?
- Dados sensíveis e segredos são minimizados, mascarados ou excluídos quando não necessários?
- Documentos e saídas recuperadas são tratados como conteúdo não confiável?

## Ferramentas e saídas
- Acesso a arquivos, rede, APIs, banco e ferramentas é mínimo e segregado?
- Ações de impacto exigem validação determinística e aprovação humana apropriada?
- Saída do modelo é validada antes de virar comando, consulta, HTML ou decisão de negócio?
- Limites de execução, orçamento, contexto, retries e tempo evitam consumo sem controle?
- Logs e telemetria não armazenam prompts/resultados sensíveis além do necessário?
- Segredos não são incluídos em contexto ou respostas; falhas e recusas são observáveis?

## Validação
Revisar arquitetura, permissões, prompts de sistema e tratamento de dados sem enviar informações a
provedores. Testes com modelo só em sandbox autorizado, dados sintéticos e sem instruções para
contornar controles ou acessar dados reais.