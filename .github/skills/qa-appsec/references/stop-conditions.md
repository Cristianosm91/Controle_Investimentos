# Condições de parada

Interrompa imediatamente validação dinâmica quando ocorrer:

- Instabilidade, lentidão, aumento inesperado de erros ou degradação de serviço.
- Alteração, exclusão, duplicação ou corrupção de dados.
- Acesso inesperado a dados reais, credenciais ou informação de outro usuário/tenant.
- Redirecionamento, DNS ou dependência para alvo fora do escopo.
- Bloqueio de conta, alerta operacional/de segurança ou solicitação do responsável.
- Aumento relevante de consumo de CPU, memória, disco, rede ou concorrência.
- Divergência entre ambiente/autorização e o alvo efetivamente alcançado.
- Bloqueio ou alerta de controle de segurança (EDR/antivírus, DLP, proxy, firewall, SOC).
- Dúvida sobre a conformidade da ação com as políticas e autorizações aplicáveis.
- Qualquer comportamento cujo efeito ou reversibilidade seja incerto.

Ao parar: não repetir nem contornar; registrar horário, ação, ambiente e motivo sem coletar conteúdo
sensível; preservar apenas evidência mínima sanitizada; informar o responsável pelo canal acordado e
recomendar investigação isolada. Em indício de incidente, orientar o reporte pelo canal oficial de
resposta a incidentes da organização responsável. Não retomar até nova autorização e limites revisados.