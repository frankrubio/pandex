"""Convierte el dibujo de un personaje en todo lo que Pandex necesita.

    .venv\\Scripts\\python.exe herramientas/skins/construir.py bmo
    .venv\\Scripts\\python.exe herramientas/skins/construir.py bmo --vista vista.png

Lee ``herramientas/skins/<id>.py`` y escribe en ``assets/personajes/<id>/``:

- ``spritesheet.png``: un cuadro de 192×208 por pose, en fila.
- ``personaje.json``: nombre, qué cuadro usa cada estado, el recorte y la cabeza (logo).
- ``icono.ico``: el ícono de la app con la cara del personaje (vía ``crear_icono.py``).

``--vista`` guarda además una lámina para revisar el resultado: las poses sobre fondo
claro y oscuro, en tamaño real y ampliadas.

El módulo del personaje define::

    ID, NOMBRE, AUTOR            textos
    POSES = ["idle", ...]        un cuadro por pose, en este orden
    ESTADOS = {"idle": "idle", "trabajando": ..., "feliz": ..., "error": ...}
    CABEZA = (x, y, ancho, alto) en la cuadrícula de 48×52: lo que va en el logo
    FONDO_LOGO = ("#claro", "#oscuro")   degradado del squircle del ícono
    def dibujar(lienzo, pose): ...
"""

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
sys.path.insert(0, str(AQUI))

import pixelart  # noqa: E402

ESTADOS_PANDEX = ("idle", "trabajando", "feliz", "error")


def cargar(ident):
    ruta = AQUI / f"{ident}.py"
    if not ruta.exists():
        sys.exit(f"No existe {ruta}")
    spec = importlib.util.spec_from_file_location(f"skin_{ident}", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def dibujar_poses(modulo):
    cuadros = []
    for pose in modulo.POSES:
        lienzo = pixelart.Lienzo(contorno=getattr(modulo, "CONTORNO", pixelart.CONTORNO))
        modulo.dibujar(lienzo, pose)
        cuadros.append(lienzo.imagen())
    return cuadros


def caja_comun(cuadros):
    """El rectángulo que contiene al personaje en todas las poses (sin saltos)."""
    cajas = [c.getbbox() for c in cuadros if c.getbbox()]
    return (min(b[0] for b in cajas), min(b[1] for b in cajas),
            max(b[2] for b in cajas), max(b[3] for b in cajas))


def vista(cuadros, destino):
    w, h = cuadros[0].size
    lamina = Image.new("RGBA", (w * len(cuadros), h * 2 + h * 2), (0, 0, 0, 0))
    for i, c in enumerate(cuadros):
        for fila, fondo in enumerate(((236, 233, 226, 255), (32, 30, 28, 255))):
            caja = Image.new("RGBA", (w, h), fondo)
            caja.alpha_composite(c)
            lamina.paste(caja, (i * w, fila * h))
    # la primera pose ampliada ×2, para ver el detalle
    grande = cuadros[0].resize((w * 2, h * 2), Image.Resampling.NEAREST)
    fondo = Image.new("RGBA", grande.size, (200, 200, 200, 255))
    fondo.alpha_composite(grande)
    lamina.paste(fondo, (0, h * 2))
    lamina.save(destino)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("id")
    parser.add_argument("--vista", type=Path, help="guarda una lámina de revisión")
    parser.add_argument("--sin-icono", action="store_true", help="no regenera icono.ico")
    args = parser.parse_args()

    modulo = cargar(args.id)
    faltan = set(ESTADOS_PANDEX) - set(modulo.ESTADOS)
    if faltan:
        sys.exit(f"ESTADOS no define: {', '.join(sorted(faltan))}")
    cuadros = dibujar_poses(modulo)
    w, h = cuadros[0].size

    carpeta = RAIZ / "assets" / "personajes" / modulo.ID
    carpeta.mkdir(parents=True, exist_ok=True)
    hoja = Image.new("RGBA", (w * len(cuadros), h), (0, 0, 0, 0))
    for i, c in enumerate(cuadros):
        hoja.paste(c, (i * w, 0))
    hoja.save(carpeta / "spritesheet.png", optimize=True)

    x0, y0, x1, y1 = caja_comun(cuadros)
    cx, cy, cw, ch = (v * pixelart.ESCALA for v in modulo.CABEZA)
    datos = {
        "nombre": modulo.NOMBRE,
        "autor": modulo.AUTOR,
        "cuadro": [w, h],
        "cuadros": {estado: modulo.POSES.index(modulo.ESTADOS[estado]) for estado in ESTADOS_PANDEX},
        "recorte": [x0, y0, x1 - x0, y1 - y0],
        "cabeza": [cx, cy, cw, ch],
        "fondo_logo": list(modulo.FONDO_LOGO),
        "orden": getattr(modulo, "ORDEN", 50),
    }
    lineas = [f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}" for k, v in datos.items()]
    (carpeta / "personaje.json").write_text("{\n" + ",\n".join(lineas) + "\n}\n", encoding="utf-8")
    print(f"{modulo.NOMBRE}: {len(cuadros)} poses → {carpeta.relative_to(RAIZ)}")

    if args.vista:
        vista(cuadros, args.vista)
        print(f"vista: {args.vista}")
    if not args.sin_icono:
        subprocess.run([sys.executable, str(RAIZ / "herramientas" / "crear_icono.py"), modulo.ID], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
