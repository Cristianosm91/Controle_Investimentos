# Checklist de segurança

Referência da Etapa 3 (revisão de segurança). Foco: falhas exploráveis e exposição de dados que
comprometam o usuário, a máquina ou os sistemas integrados (alinhado ao OWASP Top 10).

## Regras de conduta

- **Nunca** exiba, copie ou use credenciais encontradas. No relatório, cite apenas
  `arquivo:linha` e o tipo (ex.: "senha em texto claro"), com valor mascarado (`ab***`).
- **Nunca** explore vulnerabilidades contra ambientes reais. Prova de conceito só local, com dados
  fictícios e sem efeitos colaterais.
- Ferramentas que consultam bases externas (`pip-audit`, `npm audit`, `dotnet list package
  --vulnerable`, `osv-scanner`) enviam a lista de dependências para fora: execute **somente** se
  já instaladas **e** com autorização do usuário/política. Caso contrário, NÃO EXECUTADO.
- Não aplique `npm audit fix`, `pip install -U` ou similares (princípio 8).

## Itens

| Verificar | Onde procurar (`detect_project.py`) | Como comprovar / testar |
|---|---|---|
| Credenciais no código | `[segredo-possivel]`, arquivos `.env`, `.ini`, `appsettings*.json`, strings de conexão | Confirmar se é valor real ou placeholder (sem copiar o valor) |
| Segredos em logs | `logging`/`print`/`console.log` de senha, token, header `Authorization`, payload completo | Rodar com log em pasta temporária e buscar padrões |
| Validação insuficiente de entrada | Entradas de UI, CLI, arquivo, rede, query string usadas sem validação | Testes de limite e entradas inválidas |
| Injeção de comandos | `[subprocess-shell]`: `shell=True`, `os.system`, `Process.Start` com string montada | Entrada com `&`, `\|`, `;`, `` ` ``, `$()` em ambiente local |
| Injeção de SQL | `[sql-concatenado]`: f-string/`%`/`+` em `execute` | Entrada `' OR '1'='1` contra banco de teste |
| Path traversal | Caminhos montados a partir de entrada (`os.path.join(base, user_input)`) | Entrada `..\..\Windows\win.ini`; verificar `resolve()` + checagem de prefixo |
| Desserialização insegura | `[execucao-dinamica]`: `pickle`, `yaml.load` sem `SafeLoader`, `eval`, `exec`, `BinaryFormatter`, `new Function` | Revisão; PoC só local |
| Arquivos não confiáveis | Abertura de arquivos do usuário/rede (zip, xlsx, xml) | Zip bomb/XXE controlados e pequenos, local |
| XSS/HTML injetado | `innerHTML`, `dangerouslySetInnerHTML`, templates sem escape, `evaluate_js` com dados externos | Entrada `<img src=x onerror=alert(1)>` local |
| TLS desabilitado | `[verificacao-tls-desligada]`: `verify=False`, `rejectUnauthorized:false`, `CERT_NONE` | Revisão |
| Dependências vulneráveis | Manifestos/lockfiles | Somente ferramenta local autorizada (ver regras) |
| Permissões excessivas | Exigir admin sem necessidade, escrever em pastas do sistema, ACL aberta em arquivos gerados | Rodar como usuário comum |
| Dados sensíveis expostos | PAN/cartão, CPF, NSU, dados pessoais em logs, telas, arquivos temporários, relatórios | Buscar padrões nos artefatos gerados pelos testes |
| Armazenamento de senha | Senha salva em texto claro/Base64 | Deve usar proteção do SO (DPAPI no Windows — ver skill `salvar-senha`) |
| Autenticação/sessão (web/API) | Ver [web-app-checklist.md](web-app-checklist.md) e [api-service-checklist.md](api-service-checklist.md) | — |

## Ferramentas locais (somente se já instaladas)

`bandit` (Python), `semgrep` (regras locais), `gitleaks`/`detect-secrets` (segredos),
`eslint-plugin-security` (JS). Rode via `run_tests.py` para ter timeout e evidência.
