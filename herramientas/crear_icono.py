"""Crea el ícono de app de Pandex: la cara del panda robot en pixel art.

    .venv\\Scripts\\python.exe herramientas/crear_icono.py

Toma la cabeza del sprite actual, la reduce a una cuadrícula de píxeles de verdad
(por defecto 32×32) sobre una baldosa redondeada, y la amplía sin suavizar para que
cada píxel quede nítido. Guarda:
    assets/pandex.ico       varios tamaños en un solo archivo (16 a 256)
    assets/pandex_256.png   vista previa
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parent.parent
SPRITE = RAIZ / "assets" / "panda_robot" / "spritesheet.png"

# dónde está la cabeza dentro del sprite de 346×355 (medido con una cuadrícula)
CABEZA = (52, 0, 262, 182)
# a la derecha de la mejilla asoma el mango del martillo: se limpia
MARTILLO = (252, 112, 346, 355)

GRILLA = 32                  # resolución "pixel art" de la baldosa
BALDOSA = ("#1d3b5c", "#306998")  # azul Python, de arriba hacia abajo
BORDE = "#0f2338"
TAMANOS = [16, 20, 24, 32, 40, 48, 64, 72, 96, 128, 256]


def cabeza():
    im = Image.open(SPRITE).convert("RGBA")
    ImageDraw.Draw(im).rectangle(MARTILLO, fill=(0, 0, 0, 0))
    cara = im.crop(CABEZA)
    lado = max(cara.size)
    cuadrado = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    cuadrado.alpha_composite(cara, ((lado - cara.width) // 2, (lado - cara.height) // 2))
    return cuadrado


def baldosa(grilla):
    """Cuadrado de esquinas redondeadas escalonadas, como en pixel art."""
    im = Image.new("RGBA", (grilla, grilla), (0, 0, 0, 0))
    arriba, abajo = (Image.new("RGB", (1, 1), c).getpixel((0, 0)) for c in BALDOSA)
    radio = max(2, grilla // 6)
    d = ImageDraw.Draw(im)
    for y in range(grilla):
        t = y / (grilla - 1)
        color = tuple(round(a + (b - a) * t) for a, b in zip(arriba, abajo)) + (255,)
        d.line([(0, y), (grilla - 1, y)], fill=color)
    mascara = Image.new("L", (grilla, grilla), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, grilla - 1, grilla - 1), radio, fill=255)
    im.putalpha(mascara)
    contorno = Image.new("L", (grilla, grilla), 0)
    ImageDraw.Draw(contorno).rounded_rectangle((0, 0, grilla - 1, grilla - 1), radio, outline=255)
    im.paste(Image.new("RGBA", im.size, BORDE), (0, 0), contorno)
    return im


def icono_base(grilla=GRILLA, margen=3):
    """La baldosa con la cara, a la resolución de la cuadrícula (cada px es un "píxel")."""
    fondo = baldosa(grilla)
    lado = grilla - 2 * margen
    # BOX promedia los píxeles de cada celda: conserva los colores del dibujo
    cara = cabeza().resize((lado, lado), Image.BOX)
    # alfa binario: en pixel art un píxel está o no está, sin bordes a medias
    alfa = cara.getchannel("A").point(lambda a: 255 if a >= 110 else 0)
    cara.putalpha(alfa)
    fondo.alpha_composite(cara, (margen, margen + 1))
    return fondo


def a_tamano(base, lado):
    if lado % base.width == 0:
        return base.resize((lado, lado), Image.NEAREST)  # múltiplo exacto: nítido
    if lado < base.width:
        return base.resize((lado, lado), Image.BOX)
    # tamaños intermedios: primero al múltiplo de arriba sin suavizar, luego bajar
    multiplo = base.width * -(-lado // base.width)
    return base.resize((multiplo, multiplo), Image.NEAREST).resize((lado, lado), Image.LANCZOS)


def main():
    base = icono_base()
    imagenes = [a_tamano(base, t) for t in TAMANOS]
    destino = RAIZ / "assets" / "pandex.ico"
    imagenes[-1].save(
        destino, format="ICO",
        sizes=[(t, t) for t in TAMANOS],
        append_images=imagenes[:-1],
    )
    imagenes[-1].save(RAIZ / "assets" / "pandex_256.png")
    print(f"ícono: {destino}  ({', '.join(str(t) for t in TAMANOS)} px)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
