"""Crea los íconos de Pandex: la cara de cada personaje sobre un squircle de color.

    .venv\\Scripts\\python.exe herramientas/crear_icono.py          (todos)
    .venv\\Scripts\\python.exe herramientas/crear_icono.py bmo      (solo uno)

El dibujo vive en ``pandex/ui/logo.py → pintar()``; este script solo lo exporta.
Cada tamaño se pinta por separado (los chicos usan la versión «mini», más grande y
sin brillo), así se lee bien desde la bandeja (16 px) hasta el Escritorio (256 px).
Guarda:
    assets/personajes/<id>/icono.ico   todos los tamaños en un solo archivo
y, para Rusty (el logo de Pandex):
    assets/pandex.ico       el ícono por defecto (instalar.bat y GitHub)
    assets/pandex_256.png   vista previa
    assets/logo.png         512 px, para el README y la vista social
"""

import io
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from PIL import Image  # noqa: E402
from PyQt6.QtCore import QBuffer, QIODevice, Qt  # noqa: E402
from PyQt6.QtGui import QImage, QPainter  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

TAMANOS = [16, 20, 24, 32, 40, 48, 64, 72, 96, 128, 256]


def render(lado, ident):
    from pandex.ui import logo

    img = QImage(lado, lado, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    logo.pintar(p, lado, ident=ident)
    p.end()
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return Image.open(io.BytesIO(bytes(buf.data()))).convert("RGBA")


def icono(ident):
    from pandex.ui import personajes

    imagenes = [render(t, ident) for t in TAMANOS]
    destino = personajes.CARPETA / ident / "icono.ico"
    imagenes[-1].save(destino, format="ICO", sizes=[(t, t) for t in TAMANOS], append_images=imagenes[:-1])
    print(f"ícono: {destino.relative_to(RAIZ)}")
    if ident == personajes.POR_DEFECTO:
        shutil.copyfile(destino, RAIZ / "assets" / "pandex.ico")
        imagenes[-1].save(RAIZ / "assets" / "pandex_256.png")
        render(512, ident).save(RAIZ / "assets" / "logo.png")


def main():
    from pandex.ui import personajes

    _app = QApplication(sys.argv)
    pedidos = sys.argv[1:] or list(personajes.catalogo())
    for ident in pedidos:
        if not personajes.existe(ident):
            print(f"no existe el personaje {ident}")
            return 1
        icono(ident)
    return 0


if __name__ == "__main__":
    sys.exit(main())
