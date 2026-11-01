"""Mide el peso de Pandex según la spec 002 y avisa si se pasa del límite (PES-01/02/03).

Peso = la carpeta del proyecto (con ``.venv``) + la carpeta de datos sin ``personajes/``
añadidos por ti. No cuenta: el Python del sistema, tu navegador ni tu carpeta de cursos.

    python herramientas/medir_peso.py                 # total y los 15 paquetes más pesados
    python herramientas/medir_peso.py --limite 600    # sale con código 1 si se pasa
    python herramientas/medir_peso.py --base          # además falla si hay paquetes de extras
    python herramientas/medir_peso.py --json          # para la CI
"""

import argparse
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# paquetes que solo trae una función opcional: con --base no puede haber ninguno
DE_EXTRAS = ("markitdown", "magika", "onnxruntime", "pypdfium2", "pdfminer", "mammoth", "pptx", "openpyxl",
             "xlrd", "pandas")


def tamano(ruta, excluir=()):
    total = 0
    for base, carpetas, archivos in os.walk(ruta):
        carpetas[:] = [c for c in carpetas if Path(base, c) not in excluir]
        for nombre in archivos:
            try:
                total += os.lstat(os.path.join(base, nombre)).st_size
            except OSError:
                pass
    return total


def site_packages(venv):
    candidatos = list(venv.glob("lib/python3*/site-packages")) + [venv / "Lib" / "site-packages"]
    return next((c for c in candidatos if c.is_dir()), None)


def medir(raiz=RAIZ, datos=None):
    from pandex.rutas import DATOS

    datos = Path(datos or DATOS)
    venv = raiz / ".venv"
    resultado = {
        "proyecto_sin_venv": tamano(raiz, excluir={venv, raiz / ".git"}),
        "venv": tamano(venv) if venv.is_dir() else 0,
        "datos": tamano(datos, excluir={datos / "personajes"}) if datos.is_dir() else 0,
        "paquetes": {},
    }
    sitio = site_packages(venv) if venv.is_dir() else None
    if sitio:
        for hijo in sitio.iterdir():
            if hijo.is_dir() and not hijo.name.endswith((".dist-info", "__pycache__")):
                resultado["paquetes"][hijo.name] = tamano(hijo)
    resultado["total"] = resultado["proyecto_sin_venv"] + resultado["venv"] + resultado["datos"]
    return resultado


def mb(n):
    return round(n / 1024 ** 2)


def main(argumentos=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--limite", type=int, help="MB máximos; si se pasa, sale con código 1")
    p.add_argument("--base", action="store_true", help="falla si hay paquetes de funciones opcionales")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argumentos)

    r = medir()
    extras = sorted(n for n in r["paquetes"] if n.lower().split(".")[0] in DE_EXTRAS)
    if a.json:
        print(json.dumps({**r, "extras_instalados": extras}, indent=1))
    else:
        print(f"Pandex pesa {mb(r['total'])} MB: .venv {mb(r['venv'])} MB, proyecto {mb(r['proyecto_sin_venv'])} MB, "
              f"datos {mb(r['datos'])} MB")
        for nombre, peso in sorted(r["paquetes"].items(), key=lambda x: -x[1])[:15]:
            print(f"  {mb(peso):>4} MB  {nombre}")
    fallo = False
    if a.base and extras:
        print(f"PES-03: sin funciones opcionales no debería estar: {', '.join(extras)}", file=sys.stderr)
        fallo = True
    if a.limite and mb(r["total"]) > a.limite:
        print(f"PES-01/02: {mb(r['total'])} MB pasa el límite de {a.limite} MB", file=sys.stderr)
        fallo = True
    return 1 if fallo else 0


if __name__ == "__main__":
    sys.exit(main())
