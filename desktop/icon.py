"""
A logo do Stonks AI: quadrado azul com a linha do gráfico subindo.

O mesmo desenho está em SVG no favicon e na barra lateral (desktop/frontend/index.html). Daqui saem
o ícone da bandeja e o desktop/assets/stonks.ico usado na janela, no executável e no instalador.

Gerar o .ico de novo depois de mudar o desenho:
    python -m desktop.icon
"""

from pathlib import Path

from PIL import Image, ImageDraw

ICON_PATH = Path(__file__).parent / "assets" / "stonks.ico"
ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]

BLUE = (31, 79, 216, 255)  # #1F4FD8, a cor --brand do tema claro
# Pontos da linha num quadrado de 32 (iguais ao path "M7 21l6-6 4 4 8-9" do SVG)
POINTS = [(7, 21), (13, 15), (17, 19), (25, 10)]
SUPERSAMPLE = 4  # desenha maior e reduz: bordas suaves mesmo em 16 px


def image(size: int = 64) -> Image.Image:
    big = size * SUPERSAMPLE
    s = big / 32
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, big - 1, big - 1), radius=7 * s, fill=BLUE)
    points = [(x * s, y * s) for x, y in POINTS]
    width = 3 * s
    draw.line(points, fill="white", width=round(width), joint="curve")
    # Pontas arredondadas, como stroke-linecap="round" no SVG
    r = width / 2
    for x, y in (points[0], points[-1]):
        draw.ellipse((x - r, y - r, x + r, y + r), fill="white")
    return img.resize((size, size), Image.LANCZOS)


def write_ico(path: Path = ICON_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Cada tamanho desenhado à parte: reduzir o de 256 deixaria a linha fina demais em 16 px
    frames = [image(n) for n in ICO_SIZES]
    frames[-1].save(path, format="ICO", sizes=[(n, n) for n in ICO_SIZES], append_images=frames[:-1])
    return path


if __name__ == "__main__":
    print(write_ico())
