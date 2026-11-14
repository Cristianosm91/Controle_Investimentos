---
name: gerar-pdf
description: 'Gera um PDF a partir de uma lista ordenada de imagens (PNG/JPG/SVG), ideal para carrossel/documento do LinkedIn. Use quando o usuario pedir para montar/criar/gerar um PDF de imagens, juntar imagens num PDF, transformar prints/SVGs em PDF, ou montar um carrossel. SVG entra como vetor (nitido); paginas quadradas com fundo de marca e imagens centralizadas.'
argument-hint: '[imagens na ordem] [--saida arquivo.pdf] [--tamanho 1080] [--fundo #0B1F3A]'
---

# Gerar PDF de imagens (carrossel)

Monta um PDF de uma ou mais paginas a partir de imagens numa ordem definida.
Cada imagem vira uma pagina quadrada com fundo de marca, centralizada.
Ideal para carrossel/documento do LinkedIn (que exige um unico PDF).

## Quando usar

- "monte um PDF com essas imagens", "junte esses prints num PDF"
- "gera o carrossel do LinkedIn" (carrossel = 1 PDF, publicado como "Documento")
- Combinar prints (`.png`) com artes vetoriais (`.svg`) num unico arquivo
- Precisa manter uma ordem especifica de paginas

## Como funciona

- **PNG/JPG**: entram como imagem, redimensionadas para caber (contain) e centralizadas.
- **SVG**: renderizados como **vetor** com `svglib` (nitido em qualquer zoom, sem browser).
- Paginas **quadradas** (padrao 1080x1080 pt) com fundo navy padrao (`#0B1F3A`).

## Pre-requisitos (instalar 1x)

```powershell
python -m pip install --quiet pillow svglib reportlab
```

## Procedimento

1. Colete os caminhos das imagens **na ordem** desejada e o caminho de saida.
2. Rode o [script montar_pdf.py](./scripts/montar_pdf.py) passando as imagens em ordem:

   ```powershell
   python "<caminho>/scripts/montar_pdf.py" `
     img1.png img2.png code.svg hero.svg `
     --saida carrossel.pdf --tamanho 1080 --fundo "#0B1F3A"
   ```

3. Confirme a saida (`[OK]` por pagina + `PDF gerado: ...`) e abra o PDF para revisar.

## Parametros do script

| Parametro | Padrao | Descricao |
|-----------|--------|-----------|
| `imagens...` | (obrigatorio) | Um ou mais arquivos `.png/.jpg/.jpeg/.svg` na ordem das paginas |
| `--saida` | `carrossel.pdf` | Caminho do PDF de saida |
| `--tamanho` | `1080` | Lado da pagina quadrada em pontos |
| `--fundo` | `#0B1F3A` | Cor de fundo (hex) |
| `--ajuste` | `contain` | `contain` (caber, letterbox) ou `cover` (preencher, corta) |

## Observacoes

- Sem dependencia de browser: contorna politicas que bloqueiam Edge/Chromium headless.
- `svglib` substitui fontes nao instaladas (ex.: *Segoe UI* -> Helvetica); layout, cores e
  gradientes sao preservados. Para fonte identica, instale a fonte no sistema.
- LinkedIn: publique via **Criar publicacao -> Documento** e envie o PDF gerado.
