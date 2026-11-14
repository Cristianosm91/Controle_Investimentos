---
name: redigir-dados-sensiveis
description: 'Use ao anonimizar/redigir dados sensíveis em SCREENSHOTS (PNG/JPG) de aplicações antes de publicar (redes sociais, documentação, changes, tutoriais). Cobre identificadores de transação/cliente (loja, terminal, NSU, valores, documentos), usuário logado, assinatura/autor no rodapé e caminhos com o login do Windows. Técnica: PIL/Pillow com calibração por grade, amostragem do fundo, retângulo de cobertura e redesenho do texto em Segoe UI. Palavras-gatilho: esconder dados sensíveis, anonimizar print, redigir screenshot, mascarar identificadores, tirar nome do usuário, borrar caminho, dados fictícios, print para post.'
---

# Redigir dados sensíveis em screenshots

Fluxo reutilizável para trocar dados reais por **valores de teste** em prints de
aplicações, mantendo o layout intacto (sem borrão feio — cobre e reescreve o texto).

## Quando usar
- Preparar **prints reais** de um app para post/tutorial/change público.
- Trocar identificadores de transação, de cliente e do usuário por dados fictícios consistentes.

## Quando NÃO usar
- Imagens vetoriais (`.svg`): edite o texto direto no XML, não precisa de PIL.
- Quando o dado não é sensível (ex.: nome do app, versão, timestamp genérico).

## Checklist do que mascarar (exemplos)
| Dado | Exemplo real | Substituir por |
|------|--------------|----------------|
| Código de loja/estabelecimento | `LOJA1234` | `XXXXXXX4` (mesmo comprimento, mantém último char) |
| Terminal / PDV | `PDV00003` | `XXXXXXX3` |
| NSU / ID de transação | `500049` | `XXXXX9` |
| Valor | `21,89` | `99,99` (valor de teste neutro) |
| Documento (CPF/CNPJ) | `12345678000190` | mascarar com `X`, manter comprimento |
| Usuário logado (topo) | `nome.sobrenome` | `usuario.teste` |
| Rodapé / autor | `By Nome.Sobrenome` | `By Usuario.Teste` |
| Caminho com login | `C:\Users\<login>\OneDrive - <Empresa>\...` | `C:\Users\usuario\Documentos\...` |

Regra de ouro: **o mesmo valor real deve virar o mesmo valor mascarado** em todos os
lugares do print (campo de entrada + tabela de resultado), para o exemplo ficar coerente.

## Regra de execução: sempre em lotes de 20
**Sempre** processe a tarefa **de 20 em 20**, independentemente do total de itens
(imagens, regiões/`ops` ou substituições):
1. Divida a lista completa em lotes de **20** itens (o último lote pode ter menos).
2. Execute **primeiro os 20 primeiros** itens por completo (mascarar + conferir).
3. Só depois **siga para os que faltarem**, no próximo lote de 20, repetindo até acabar.
4. Ao final de cada lote, faça um resumo curto (quantos concluídos / quantos restam)
   antes de iniciar o próximo lote.

## Técnica (PIL/Pillow) — passo a passo
1. **Backup primeiro:** copie o original para `_orig-*.png` (contém dado real — apagar no fim).
2. **Calibrar por grade:** gere uma cópia com linhas a cada 50px (vermelho nos múltiplos
   de 100) e rótulos, abra e leia as coordenadas exatas de cada campo. Para textos
   pequenos, recorte a região e amplie com `Image.NEAREST` (6x) para medir ao pixel.
3. **Para cada região:** amostre o fundo (`im.getpixel`) num ponto **vazio do mesmo campo**
   (mesma cor), preencha um retângulo sobre o texto antigo e **redesenhe** o novo texto.
4. **Sempre ler do backup limpo** ao reprocessar (evita acúmulo de camadas se ajustar coords).
5. **Preserve elementos ao lado:** ex.: o ponto verde de status fica à esquerda do usuário —
   comece o retângulo logo depois dele.
6. **Conferir ampliado** o resultado antes de finalizar; então **apague** `_orig-*`,
   grades e recortes temporários (não deixe o dado real no repositório).

## Parâmetros que funcionaram bem
- Fonte: `C:\Windows\Fonts\segoeui.ttf` (fallback `arial.ttf`).
- Cores: texto de campo `#374151`, caminhos `#4b5563`, rodapé `#9ca3af`.
- Tamanhos (prints ~1080px de largura): valores de campo ~17px, caminhos ~15px,
  usuário ~13px, rodapé ~13px.

## Trecho reutilizável
```python
from PIL import Image, ImageDraw, ImageFont

def font(sz):
    for fn in (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"):
        try: return ImageFont.truetype(fn, sz)
        except Exception: pass
    return ImageFont.load_default()

def redact(src, dst, ops):
    """ops: lista de (box, sample_xy, texto, text_xy, size, color)."""
    im = Image.open(src).convert("RGB")
    d = ImageDraw.Draw(im)
    for box, sample, text, txy, size, color in ops:
        d.rectangle(box, fill=im.getpixel(sample))  # cobre com o fundo amostrado
        if text:
            d.text(txy, text, fill=color, font=font(size))
    im.save(dst)
```

## Erros comuns (aprendidos)
- **Sobrou parte do texto** (ex.: "cris"): o retângulo começou tarde — meça a borda
  esquerda real do glifo no recorte ampliado e estenda o `box`.
- **Bloco branco visível:** o `sample_xy` caiu sobre texto ou fora do campo — escolha um
  pixel claramente vazio dentro do mesmo campo.
- **Rasterizar SVG p/ conferência:** `cairosvg`/`renderPM` exigem cairo (falha no Windows);
  valide o SVG como XML e cheque o comprimento do texto vs. canvas em vez de rasterizar.
