"""Convierte un GIF animado (p. ej. una mascota de Codex Pets) en un sprite sheet.

    .venv\\Scripts\\python.exe herramientas/gif_a_sprite.py rusty.gif assets/personajes/rusty/spritesheet.png

Pone cada cuadro del GIF uno al lado del otro, en una sola fila, con transparencia.
Pandex usa una imagen fija por estado: en ``config.json`` (o en ``assets/personajes/<id>/personaje.json``)
eliges qué cuadro corresponde a cada uno.
"""

import sys
from pathlib import Path

from PIL import Image, ImageSequence


def convertir(origen, destino):
    gif = Image.open(origen)
    cuadros = [c.convert("RGBA") for c in ImageSequence.Iterator(gif)]
    ancho, alto = cuadros[0].size
    hoja = Image.new("RGBA", (ancho * len(cuadros), alto), (0, 0, 0, 0))
    for i, cuadro in enumerate(cuadros):
        hoja.alpha_composite(cuadro, (i * ancho, 0))
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    hoja.save(destino, optimize=True)
    return len(cuadros), ancho, alto


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    n, ancho, alto = convertir(sys.argv[1], sys.argv[2])
    print(f"{sys.argv[2]}: {n} cuadro(s) de {ancho}×{alto}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
