# Release — roteiro e verificações

Complementa `git-workflow` (fluxo de branches, tag e pacotes piloto/produção). Esta referência
**não** redefine esse fluxo; descreve o que validar tecnicamente em cada release.

## 1. Versão em fonte única
- Defina **um** lugar canônico (ex.: `__version__` no pacote Python, `version` no `package.json`,
  ou arquivo `VERSION`). Os demais pontos (UI, API `/status`, empacotador) **leem** dessa fonte.
- Verificação: procure a string da versão em todo o repositório; mais de uma ocorrência
  editável manualmente → achado (Média). Divergência entre ocorrências → achado (Alta).
- Semver `MAJOR.MINOR.CORREÇÃO` conforme `git-workflow`.

## 2. CHANGELOG
- Formato [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/): `Unreleased` no topo,
  seções `Adicionado`, `Alterado`, `Corrigido`, `Removido`, `Obsoleto`, `Segurança`.
- Na release: mover `Unreleased` para `## [X.Y.Z] - AAAA-MM-DD`.
- Toda funcionalidade visível ao usuário tem entrada (ver `documentacao-funcional`).
- Sem dados internos, nomes pessoais, caminhos de máquina ou valores reais.

## 3. Sequência (respeitando `git-workflow`)
1. Atualizar versão (fonte única) + CHANGELOG na branch de desenvolvimento.
2. MR para a branch de homologação; pipeline verde é pré-requisito.
3. Pacote piloto gerado a partir da homologação (se o projeto usar).
4. MR para a branch de produção com as aprovações exigidas; pipeline verde.
5. Tag anotada `vX.Y.Z` **no commit integrado** na produção: `git tag -a vX.Y.Z -m "vX.Y.Z"`.
6. Pipeline de release gera artefatos a partir da tag.

> Push de tag e operações em branches protegidas seguem a proteção e o protocolo de confirmação
> do `git-workflow`. Esta skill nunca executa push sem esse fluxo.

## 4. Artefatos
- Gerados pelo pipeline, a partir da tag (não da máquina do desenvolvedor), quando possível.
- Checksum SHA-256 publicado junto (`SHA256SUMS`).
- SBOM opcional: `cyclonedx-py requirements backend/requirements.txt -o sbom-backend.json`,
  `npx @cyclonedx/cyclonedx-npm --output-file sbom-frontend.json`.
- Sem `.env`, bancos locais, logs, relatórios de QA ou dados reais no pacote.

## 5. Notas de release
- Derivadas da seção do CHANGELOG da versão; linguagem para o usuário final.
- Incluem: novidades, correções, mudanças incompatíveis, passos de atualização (migrações,
  backup prévio — ver `backup-recuperacao`), limitações conhecidas.

## 6. Verificação pós-release
- Tag aponta para o commit esperado: `git rev-parse vX.Y.Z^{commit}`.
- Versão exibida pela app/artefato = versão da tag.
- Artefato instala/executa em ambiente limpo (smoke).
- Registrar `NÃO EXECUTADO` para o que não puder ser verificado.
