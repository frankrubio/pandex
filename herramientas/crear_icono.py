"""Crea los íconos de Pandex: la cara de cada personaje sobre un squircle de color.

    .venv\\Scripts\\python.exe herramientas/crear_icono.py          (todos)
    .venv\\Scripts\\python.exe herramientas/crear_icono.py bmo      (solo uno)

El dibujo y la exportación viven en ``pandex/ui/logo.py``. Guarda:
    assets/personajes/<id>/icono.ico   16 a 256 px en un solo archivo
y, para Rusty (el logo de Pandex):
    assets/pandex.ico       el ícono por defecto (instalar.bat y GitHub)
    assets/pandex_256.png   vista previa
    assets/logo.png         512 px, para el README y la vista social
"""

import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from PyQt6.QtWidgets import QApplication  # noqa: E402


def main():
    from pandex.ui import logo, personajes

    _app = QApplication(sys.argv)
    pedidos = sys.argv[1:] or [p.id for p in personajes.catalogo().values() if not p.propio]
    for ident in pedidos:
        if not personajes.existe(ident):
            print(f"no existe el personaje {ident}")
            return 1
        destino = logo.guardar_ico(ident)
        print(f"ícono: {destino}")
        if ident == personajes.POR_DEFECTO:
            shutil.copyfile(destino, RAIZ / "assets" / "pandex.ico")
            logo.a_pillow(logo.imagen(256, ident)).save(RAIZ / "assets" / "pandex_256.png")
            logo.a_pillow(logo.imagen(512, ident)).save(RAIZ / "assets" / "logo.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
