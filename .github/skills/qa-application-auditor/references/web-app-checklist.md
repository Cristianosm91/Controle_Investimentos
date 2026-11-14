# Checklist — aplicações web (front-end)

Carregue quando houver front-end web: SPA (React/Vue/Angular/Svelte), páginas servidas por
Flask/Django/Express/ASP.NET, Streamlit, ou HTML/JS em pywebview/QtWebEngine/Electron.
Para o back-end/API, use também [api-service-checklist.md](api-service-checklist.md).

## Desempenho e recursos no navegador

| Verificar | Onde procurar | Como comprovar |
|---|---|---|
| Listeners não removidos | `addEventListener` sem `removeEventListener`; `useEffect` sem cleanup | Montar/desmontar a tela N vezes; heap snapshot no DevTools |
| Timers esquecidos | `setInterval`/`setTimeout` recorrente sem `clear*` | Idem; CPU da aba ociosa |
| Polling agressivo | `setInterval(fetch, <1000)` | Contar requisições/minuto no DevTools (Network) |
| Requisições sem timeout/cancelamento | `fetch` sem `AbortController`; troca de tela não cancela | Back-end fake lento; trocar de tela |
| Requisições duplicadas | Duplo clique em submit; efeitos executando duas vezes | Contar requisições no Network |
| DOM muito grande | Tabelas/listas renderizando milhares de linhas sem paginação/virtualização | Tempo de render, memória da aba |
| Atualização excessiva | Re-render por tecla sem debounce; estado global grande | Profiler do framework |
| Recursos pesados | Imagens/JS sem compressão, bundle grande | Network/Lighthouse (se disponível) |
| WebSocket/SSE | Reconexão sem backoff, sem limite; mensagens acumuladas em memória | Derrubar o servidor fake e observar |
| Armazenamento local | `localStorage`/`IndexedDB` crescendo sem limite | Inspecionar após uso prolongado |

## Experiência de uso e resiliência

- Indicação de progresso e estado de carregamento; botões desabilitados durante envio.
- Mensagens de erro compreensíveis para 4xx/5xx, timeout e offline; nada de tela branca.
- Recuperação: repetir a operação após erro funciona; recarregar a página não perde dados críticos.
- Responsividade e escala (100%–175%); layout sem cortes. Em apps desktop, ver também a
  skill `app-ux` (não duplicar essas regras aqui).

## Segurança (front-end)

| Verificar | Onde procurar |
|---|---|
| XSS | `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `dangerouslySetInnerHTML`, `v-html`, `\|safe` em templates |
| Segredos no bundle | Chaves de API, tokens, URLs internas com credenciais em JS/HTML |
| Armazenamento de token | Token de sessão em `localStorage` (preferir cookie `HttpOnly`/`Secure`/`SameSite`) |
| CSRF | Formulários/requisições que alteram estado sem token/`SameSite` |
| Cabeçalhos | CSP, `X-Content-Type-Options`, `frame-ancestors` (no servidor) |
| Redirecionamento aberto | `location = params.get('next')` sem validação |
| Ponte JS↔Python/Node | Métodos expostos (`js_api`, `contextBridge`, `QWebChannel`) aceitando caminhos/comandos arbitrários |

## Ferramentas (somente se já disponíveis)

Playwright/Cypress/Selenium configurados no projeto para E2E; DevTools (Performance, Memory,
Network); Lighthouse. Testes E2E sempre contra servidor **local** e dublês de APIs externas.
