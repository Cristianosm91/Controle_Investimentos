# Aplicação web local (servidor em localhost aberto no navegador)

Para apps que sobem um servidor HTTP na própria máquina (FastAPI/Flask/Express/etc.) e usam o
navegador como interface. "Só escuta em localhost" **não** é fronteira suficiente: qualquer site
aberto no mesmo navegador alcança `127.0.0.1`.

- O servidor faz bind só em `127.0.0.1`/`::1` (nunca `0.0.0.0` por padrão)? Mudança para rede exige configuração explícita e aviso?
- O cabeçalho `Host` é validado contra uma lista de hosts permitidos (proteção contra *DNS rebinding*)?
- Requisições que alteram estado (POST/PUT/PATCH/DELETE) validam `Origin`/`Sec-Fetch-Site` e recusam outras origens (CSRF)? Origem `null` é recusada?
- A tolerância de origem é a mínima necessária (ex.: qualquer porta de `localhost` permite que outro serviço local grave — risco documentado?)
- CORS desabilitado ou restrito; nenhum `Access-Control-Allow-Origin: *` com dados sensíveis.
- Uploads exigem tipo de conteúdo que force *preflight* (ex.: `application/octet-stream`) ou token, para que formulários de outros sites não consigam enviar?
- Respostas com `X-Frame-Options`/CSP `frame-ancestors`, `nosniff`, `Referrer-Policy` e `Cross-Origin-Resource-Policy` (clickjacking e leitura cruzada)?
- Endpoints de download/exportação/backup não aceitam caminhos arbitrários (path traversal) e servem só arquivos gerados pelo app?
- Restauração/importação de arquivos (bancos SQLite, planilhas, ZIP) trata o arquivo como **não confiável**: limites de tamanho/expansão, `trusted_schema=OFF`, rejeição de triggers/views inesperados, fórmulas de planilha neutralizadas na exportação?
- A documentação interativa da API (`/docs`, `/openapi.json`) é aceitável no contexto local ou deve ser desabilitada em builds de distribuição?
- Porta ocupada, segunda instância e encerramento tratados sem expor outra aplicação na mesma porta?
- Testes automatizados cobrem: Host inválido → 400, escrita com Origin externa → 403, Origin `null` → 403, cliente sem Origin (script/teste) → aceito conforme política.
