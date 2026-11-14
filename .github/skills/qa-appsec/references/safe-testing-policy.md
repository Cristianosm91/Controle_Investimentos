# Política de teste seguro

## Defaults

- Análise estática/arquitetural somente leitura: habilitada.
- Teste dinâmico, rede, carga/estresse/chaos, instalação e alterações: desabilitados.
- Dados de teste: sintéticos; evidência: sanitizada.
- Ferramentas locais já disponíveis podem ser consideradas conforme o escopo; nenhuma instalação automática.

## Pré-condições para teste dinâmico

Antes de qualquer teste dinâmico, confirmar autorização explícita e cumprir os requisitos de aprovação
aplicáveis. Usar somente ferramentas permitidas e contas de teste autorizadas. Esta skill não executa
testes em produção, ambientes compartilhados ou terceiros; encaminhe-os aos responsáveis autorizados.
Nunca desabilitar ou contornar EDR, DLP, proxy, VPN, firewall, MFA/SSO ou monitoramento.

Delimitar alvo e ambiente, métodos permitidos/proibidos, janela, limites de requisição/tempo/
concorrência, dados sintéticos, plano de reversão e stop conditions. Preferir sandbox descartável. Se
a autorização ou os limites estiverem incompletos, não executar.

## Fora de escopo

Não realizar brute force, credential stuffing, DoS, exfiltração, acesso a dados de outros usuários,
persistência, evasão, alteração/exclusão de dados, bypass de controles reais, exploração destrutiva,
varredura fora do escopo ou acesso a rede interna via SSRF. Não testar produção ou terceiros.

Teste dinâmico autorizado não significa pentest irrestrito: cada ação deve ser necessária, proporcional,
reversível e interrompida ao primeiro comportamento inesperado.