# Segurança da cadeia de suprimentos

## Origem e integridade
- Repositórios, registries, imagens e downloads têm origem confiável e versão fixada?
- Lockfiles, hashes, assinaturas, tags e artefatos de release são verificados onde suportado?
- Há inventário/SBOM, proveniência e rastreabilidade entre fonte, build e distribuição?
- Builds são reproduzíveis ou existem controles equivalentes de integridade?

## CI/CD e release
- Tokens de pipeline têm escopo e duração mínimos; segredos são protegidos e mascarados?
- Jobs privilegiados, runners, actions/plugins e scripts de instalação são revisados e fixados?
- Branches, aprovações, artefatos e ambientes de release têm segregação adequada?
- Atualizadores validam autenticidade/integridade e evitam downgrade não autorizado?
- Logs de build e artefatos não contêm credenciais, dados de produção ou conteúdo indevido?
- Processo de incidente pode identificar versões afetadas e interromper distribuição com segurança?

## Evidência
Revisar arquivos de pipeline, lockfiles, Dockerfiles, assinatura e documentação. Não publicar, baixar,
instalar ou executar artefatos externos durante a auditoria sem autorização específica.