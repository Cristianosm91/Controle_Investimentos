# Ferramentas — UX Web e Acessibilidade

Instalação de ferramentas novas **só com autorização**. Prefira o que o projeto já tem.
Ferramentas automáticas detectam parte dos problemas WCAG; complete com testes manuais.

## 1. axe-core via Playwright (automático, por página)

```ts
import AxeBuilder from '@axe-core/playwright';
const r = await new AxeBuilder({ page })
  .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
  .exclude('[data-a11y-ignorar]')   // só com justificativa registrada
  .analyze();
```
Python: `axe-playwright-python` (`Axe().run(page)`). Integre aos cenários de `testes-e2e`
para avaliar também modais abertos e estados de erro/vazio.

## 2. eslint-plugin-jsx-a11y (estático, React)

```js
// eslint.config.js (flat config)
import jsxA11y from 'eslint-plugin-jsx-a11y';
export default [jsxA11y.flatConfigs.recommended];
```
Execução: `npx eslint "src/**/*.{ts,tsx}"`. Se o projeto não tem ESLint, registre como
recomendação — não adicione sem confirmação.

## 3. Lighthouse (auditoria por página)

```powershell
npx lighthouse http://127.0.0.1:8000/ --only-categories=accessibility,best-practices,performance `
  --output html --output-path qa-report\web-ux-acessibilidade\evidencias\lighthouse.html `
  --chrome-flags="--headless"
```
Lighthouse CI (`@lhci/cli`) pode virar job no pipeline (`ci-cd-release`) com orçamento mínimo.
Rode contra a app **local** com dados fictícios.

## 4. Testes manuais roteirizados

| Teste | Como | Evidência |
|---|---|---|
| Teclado | Percorrer cada página com Tab/Shift+Tab, Enter/Espaço, setas, Esc | Lista de passos + onde falhou |
| Foco em modal | Abrir, tabular até o fim, Esc, verificar retorno ao gatilho | Screenshot do foco |
| Zoom 200% | `Ctrl` `+` até 200% em 1280px | Screenshot |
| Reflow | Viewport 320px CSS (`page.setViewportSize({ width: 320, height: 800 })`) | Screenshot |
| Leitor de tela | NVDA (Windows) ou VoiceOver: títulos, rótulos, anúncios de erro | Transcrição resumida |
| Contraste | DevTools (Inspect → contraste) ou Colour Contrast Analyser | Valores medidos |
| Movimento reduzido | `page.emulateMedia({ reducedMotion: 'reduce' })` | Observação |
| Daltonismo | DevTools → Rendering → Emulate vision deficiencies | Screenshot |

## 5. Formatos pt-BR (verificação)

```ts
new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(1234.56); // "R$ 1.234,56"
new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2 }).format(0.1234 * 100) + '%'; // "12,34%"
new Intl.DateTimeFormat('pt-BR').format(new Date(2026, 0, 31));                           // "31/01/2026"
```
Procure formatação ad hoc que contorne o utilitário da app:
`rg -n "toFixed\(|replace\('\.'|toLocaleString\(\)" src` (sem locale explícito → achado).
Atenção: `Intl` usa espaço não separável após `R$`; asserções devem normalizar.

## 6. Busca rápida de sinais (revisão estática)

```powershell
rg -n "onClick=" src --glob "*.tsx" | rg "<div|<span"         # elemento não interativo clicável
rg -n "outline:\s*none|outline:\s*0" src                       # foco removido
rg -n "<img(?![^>]*alt=)" -P src --glob "*.tsx"                # imagem sem alt
rg -n "<input(?![^>]*(aria-label|id=))" -P src --glob "*.tsx"  # campo possivelmente sem rótulo
rg -n "window\.confirm\(" src                                   # confirmação nativa (avaliar padrão)
rg -n "#[0-9a-fA-F]{3,6}" src --glob "*.{css,tsx}"             # cores fora dos tokens
```
Sinais são **pontos de partida**: abra o trecho e confirme antes de registrar achado.
