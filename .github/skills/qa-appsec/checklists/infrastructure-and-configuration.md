# Infraestrutura e configuração

## Configuração
- Debug, diagnósticos, painéis administrativos e serviços expostos estão restritos?
- Portas, protocolos, permissões, ACLs e identidades seguem necessidade mínima?
- Ambientes e segredos estão separados; valores sensíveis não estão em imagens, scripts ou IaC?
- Configurações TLS, headers, CORS, armazenamento e rede são explícitas e revisáveis?
- Recursos cloud/storage/banco não estão públicos por padrão e têm política de acesso rastreável?

## Containers, IaC e host
- Imagens e módulos têm origem e versão controladas; execução evita privilégios desnecessários?
- Volumes, capabilities, namespaces, rede, usuário, filesystem e secrets têm escopo mínimo?
- IaC é revisada antes de aplicar; diffs e aprovações estão disponíveis?
- Pipelines e runners são isolados; produção exige controles e aprovação apropriados?
- Backups, restauração, atualização e resposta a configuração incorreta estão documentados?

## Método
Revisar arquivos de configuração/IaC em leitura. Não aplicar mudanças, provisionar recursos, consultar
cloud externa ou testar portas/hosts sem autorização específica.