# Checklist — Documentação Funcional

Marque `OK`, `ACHADO (DOC-XXX)`, `N/A` ou `NÃO VERIFICADO` (com motivo). Toda afirmação
conferida deve ter fonte (arquivo:linha, teste ou execução).

## 1. README
- [ ] Objetivo da aplicação em 1–3 frases.
- [ ] Requisitos com versões (linguagens, runtimes, SO) iguais às dos manifestos/CI.
- [ ] Instalação passo a passo reproduzível em máquina limpa (comandos executados no modo `test`).
- [ ] Configuração: nomes de variáveis/arquivos, valores padrão, onde ficam dados e logs — **sem valores sensíveis**.
- [ ] Uso: como iniciar, acessar e parar; principais funcionalidades com link para detalhes.
- [ ] Como rodar lint/testes (mesmos comandos do script local e do CI).
- [ ] Estrutura de pastas coerente com o repositório atual.
- [ ] Links internos válidos; sem caminhos absolutos de máquina pessoal.

## 2. CHANGELOG
- [ ] Formato Keep a Changelog; seção `Unreleased` no topo.
- [ ] Versões em ordem decrescente com data ISO (`AAAA-MM-DD`).
- [ ] Versão mais recente do CHANGELOG = versão da fonte única = última tag.
- [ ] Entradas escritas para o usuário (o quê e impacto), não lista de commits.
- [ ] Mudanças incompatíveis e passos de migração destacados.
- [ ] Toda funcionalidade visível nova/alterada desde a última versão tem entrada.

## 3. FAQ / solução de problemas
- [ ] Mensagens de erro exibidas pela app (busque no código) têm entrada correspondente quando o usuário pode agir.
- [ ] Formato sintoma → causa provável → solução.
- [ ] Problemas de ambiente comuns (porta ocupada, dependência ausente, proxy/registry, permissão de pasta).
- [ ] Soluções não instruem apagar dados sem backup prévio.

## 4. Regras de cálculo
- [ ] Cada cálculo exibido ao usuário tem documento: fórmula, entradas, unidades, arredondamento, datas de corte, tratamento de casos-limite.
- [ ] Fonte de dados externa e periodicidade indicadas.
- [ ] Exemplo numérico com **dados fictícios** que coincide com um teste automatizado (citar o teste).
- [ ] Referência ao código (módulo/função) que implementa.
- [ ] Divergência doc × código × teste registrada como achado (não escolher lado sozinho).

## 5. API (OpenAPI)
- [ ] Cada endpoint com `summary` e `description`; parâmetros descritos.
- [ ] Schemas com `description` e `examples` fictícios.
- [ ] Códigos de erro documentados com significado.
- [ ] Ajustes de documentação não alteram contrato (path, tipos, obrigatoriedade, status).

## 6. Ajuda in-app, ADR, runbook, limitações
- [ ] Tooltips/ajuda/estado vazio coerentes com o comportamento e com a documentação.
- [ ] ADRs para decisões estruturais (persistência, framework, integração, formato de backup) com status.
- [ ] Runbook: iniciar, parar, atualizar versão, aplicar migrações, backup, restaurar, verificar saúde, localizar logs, rollback.
- [ ] Procedimentos do runbook testados em ambiente isolado ou marcados `NÃO EXECUTADO`.
- [ ] Limitações conhecidas e avisos (dados de terceiros podem atrasar/falhar; resultados informativos; precisão) visíveis no README e/ou na app.
- [ ] Screenshots atualizados, com dados fictícios e sem usuário/caminho da máquina.

## 7. Detecção de drift

| Afirmação no doc | Como verificar no código |
|---|---|
| Comando (`npm run x`, `python -m y`) | `package.json` scripts, módulos/entrypoints, scripts `.bat`/`.sh` |
| Porta, host, URL | Configuração do servidor, scripts de inicialização |
| Variável de ambiente | `rg -n "getenv\|environ\|import.meta.env\|process.env"` |
| Caminho de dados/logs | Código de configuração/paths |
| Endpoint | Decorators de rota / `/openapi.json` |
| Menu/página | Router e componente de navegação |
| Fórmula/limite/formato | Função de cálculo e seus testes |
| Versão | Fonte única de versão, tags (`git tag --list "v*"`) |

Sentidos do drift:
- **Código sem doc**: funcionalidade/configuração existente não documentada.
- **Doc sem código**: documento descreve algo removido ou nunca implementado.
- **Doc divergente**: ambos existem, mas diferem (valor, passo, nome, fórmula).

## 8. Higiene
- [ ] Sem segredos, tokens, senhas, nomes pessoais, dados reais ou caminhos com usuário da máquina.
- [ ] Terminologia igual à da interface.
- [ ] Idioma e tom consistentes (pt-BR).
- [ ] Documentação atualizada no mesmo commit/MR da funcionalidade (verificável no histórico).
