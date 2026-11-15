"""Gera um PDF a partir de uma lista ordenada de imagens (PNG/JPG/SVG).

Cada imagem vira uma pagina quadrada, com fundo de marca e imagem centralizada.
SVG e renderizado como vetor (nitido, sem browser).

Uso:
    python montar_pdf.py img1.png img2.png code.svg hero.svg \
        --saida carrossel.pdf --tamanho 1080 --fundo "#0B1F3A"
"""

import argparse
import sys
from pathlib import Path

from PIL import Image
from reportlab.graphics import renderPDF
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from svglib.svglib import svg2rlg

SVG_EXT = {".svg"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}


def _fundo(c: canvas.Canvas, lado: float, cor: HexColor) -> None:
    c.setFillColor(cor)
    c.rect(0, 0, lado, lado, stroke=0, fill=1)


def _pagina_imagem(c: canvas.Canvas, caminho: Path, lado: float,
                   cor: HexColor, ajuste: str) -> None:
    _fundo(c, lado, cor)
    with Image.open(caminho) as img:
        w, h = img.size
    if ajuste == "cover":
        escala = max(lado / w, lado / h)
    else:  # contain
        escala = min(lado / w, lado / h)
    nw, nh = w * escala, h * escala
    x, y = (lado - nw) / 2, (lado - nh) / 2
    if ajuste == "cover":
        c.saveState()
        p = c.beginPath()
        p.rect(0, 0, lado, lado)
        c.clipPath(p, stroke=0, fill=0)
    c.drawImage(ImageReader(str(caminho)), x, y, nw, nh,
                preserveAspectRatio=True, mask="auto")
    if ajuste == "cover":
        c.restoreState()
    c.showPage()


def _pagina_svg(c: canvas.Canvas, caminho: Path, lado: float,
                cor: HexColor, ajuste: str) -> None:
    _fundo(c, lado, cor)
    desenho = svg2rlg(str(caminho))
    if desenho is None:
        raise RuntimeError(f"Falha ao ler SVG: {caminho.name}")
    if ajuste == "cover":
        escala = max(lado / desenho.width, lado / desenho.height)
    else:
        escala = min(lado / desenho.width, lado / desenho.height)
    desenho.scale(escala, escala)
    x = (lado - desenho.width * escala) / 2
    y = (lado - desenho.height * escala) / 2
    renderPDF.draw(desenho, c, x, y)
    c.showPage()


def montar(imagens, saida: Path, lado: float, cor: HexColor, ajuste: str) -> None:
    c = canvas.Canvas(str(saida), pagesize=(lado, lado))
    for nome in imagens:
        caminho = Path(nome).expanduser().resolve()
        if not caminho.exists():
            print(f"[ERRO] Arquivo nao encontrado: {caminho}", file=sys.stderr)
            sys.exit(1)
        ext = caminho.suffix.lower()
        if ext in SVG_EXT:
            _pagina_svg(c, caminho, lado, cor, ajuste)
        elif ext in IMG_EXT:
            _pagina_imagem(c, caminho, lado, cor, ajuste)
        else:
            print(f"[ERRO] Extensao nao suportada: {caminho.name}", file=sys.stderr)
            sys.exit(1)
        print(f"[OK] {caminho.name}")
    c.save()
    print(f"\nPDF gerado: {saida}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Gera um PDF a partir de imagens (PNG/JPG/SVG) em ordem.")
    ap.add_argument("imagens", nargs="+", help="Imagens na ordem das paginas")
    ap.add_argument("--saida", default="carrossel.pdf", help="PDF de saida")
    ap.add_argument("--tamanho", type=float, default=1080.0,
                    help="Lado da pagina quadrada (pt). Padrao 1080")
    ap.add_argument("--fundo", default="#0B1F3A", help="Cor de fundo (hex)")
    ap.add_argument("--ajuste", choices=("contain", "cover"), default="contain",
                    help="contain (caber) ou cover (preencher/cortar)")
    args = ap.parse_args()

    saida = Path(args.saida).expanduser().resolve()
    saida.parent.mkdir(parents=True, exist_ok=True)
    montar(args.imagens, saida, args.tamanho, HexColor(args.fundo), args.ajuste)


if __name__ == "__main__":
    main()
