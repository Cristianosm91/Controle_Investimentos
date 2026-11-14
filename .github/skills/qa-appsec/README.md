# QA AppSec

Skill de avaliação defensiva de segurança, privacidade e resiliência. Analisa somente o escopo
fornecido/autorizado, usa leitura estática como padrão e respeita os requisitos de segurança e
autorização aplicáveis ao ambiente (ver [SKILL.md](SKILL.md)).

## Uso

```text
/qa-appsec [perfil] [modo] [caminho] [escopo autorizado]
```

Exemplos:

```text
/qa-appsec quick-scan review ./src
/qa-appsec standard review ./app
/qa-appsec deep test ./service "sandbox local; autorização registrada conforme política aplicável; endpoints e janela autorizados"
```

`standard` é o perfil padrão. Os perfis não autorizam atividades por si só. Rede, testes dinâmicos,
ferramentas externas, instalação de ferramentas e alterações permanecem desabilitados até haver
autorização explícita e serem cumpridos os requisitos de aprovação aplicáveis.

## Perfis

| Perfil | Uso |
|---|---|
| `quick-scan` | Triagem estática e priorização de riscos críticos/altos. |
| `standard` | Revisão estática, arquitetural e manual, threat modeling, dependências, dados e resiliência. |
| `deep` | `standard` mais validações dinâmicas seguras, somente com autorização explícita. |

## Defaults

- Somente leitura; análise dinâmica, carga, acesso externo e mudanças desabilitados.
- Sem instalar ferramentas ou enviar código, manifestos, artefatos ou dados para terceiros.
- Evidências mínimas e mascaradas; dados de teste sintéticos.
- Segredos encontrados nunca são revelados ou reutilizados.
- Achados separados por estado, severidade, probabilidade e confiança.

## Materiais

- [SKILL.md](SKILL.md): workflow, limites, perfis, critérios e saída.
- [Checklists](checklists/README.md): roteiros selecionados conforme a tecnologia e o escopo.
- [Templates](templates/README.md): relatórios, risco, remediação e reteste.
- [Referências e limites](references/README.md): autorização, testes, evidências e severidade.

Consulte também a skill `qa-application-auditor` quando o objetivo incluir regressão funcional,
desempenho, consumo de recursos ou estabilidade operacional.