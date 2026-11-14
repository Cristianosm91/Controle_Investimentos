# Segurança de aplicações desktop

## Aplicação e distribuição
- Assinatura, origem, integridade e processo de atualização são verificáveis?
- Instalador, executável, bibliotecas e Python portátil são inventariados e protegidos contra substituição?
- Diretórios modificáveis não controlam carregamento de módulos ou executáveis privilegiados?
- Aplicação roda sem admin quando possível; arquivos, registro e processos seguem menor privilégio?
- Credenciais locais usam armazenamento do sistema operacional, escopo do usuário e proteção adequada?

## Arquivos e integrações
- ZIP/PYZ/PYZW têm limites de leitura e prevenção a caminhos fora do destino?
- Arquivos do usuário, temporários, exports, logs e backups têm ACL, limpeza e retenção apropriadas?
- Navegador embutido, deep links, clipboard, IPC, subprocessos e TLS são tratados como fronteiras?
- Segredos não aparecem em argumentos de processo, logs, bundles, configuração ou crash dumps?
- Atualizador valida origem/integridade e impede downgrade inseguro?

## Artefatos
Inspecionar metadados, lista de arquivos e configuração sem executar binários/scripts. Extração somente
com limites e autorização; nunca executar artefatos desconhecidos.