"""Crea el ícono de Pandex: la cara de Rusty sobre un squircle azul.

    .venv\\Scripts\\python.exe herramientas/crear_icono.py

El dibujo vive en ``pandex/ui/dibujo.py → logo()``; este script solo lo exporta.
Cada tamaño se pinta por separado (los chicos usan la versión «mini», más grande y
sin brillo), así se lee bien desde la bandeja (16 px) hasta el Escritorio (256 px).
Guarda:
    assets/pandex.ico       todos los tamaños en un solo archivo
    assets/pandex_256.png   vista previa
    assets/logo.png         512 px, para el README y la vista social
"""

import io
import os
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


def render(lado):
    from pandex.ui import dibujo

    img = QImage(lado, lado, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    dibujo.logo(p, lado)
    p.end()
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return Image.open(io.BytesIO(bytes(buf.data()))).convert("RGBA")


def main():
    _app = QApplication(sys.argv)
    imagenes = [render(t) for t in TAMANOS]
    destino = RAIZ / "assets" / "pandex.ico"
    imagenes[-1].save(destino, format="ICO", sizes=[(t, t) for t in TAMANOS], append_images=imagenes[:-1])
    imagenes[-1].save(RAIZ / "assets" / "pandex_256.png")
    render(512).save(RAIZ / "assets" / "logo.png")
    print(f"ícono: {destino}  ({', '.join(str(t) for t in TAMANOS)} px)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
