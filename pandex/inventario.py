"""Lo que Pandex crea fuera de sus carpetas, anotado para poder quitarlo (RES-10).

Accesos directos, arranque automático, despertador y perfiles de navegador de snap. El
desinstalador usa esta lista y, por si falta (versiones anteriores no anotaban), también
las rutas conocidas. Es un JSON pequeño en la carpeta de datos.
"""

import json
from datetime import datetime
from pathlib import Path

from .log import get_logger
from .rutas import DATOS

log = get_logger("pandex.inventario")

ARCHIVO = DATOS / "inventario.json"


def todo():
    """``[{"ruta", "motivo", "fecha"}]``."""
    try:
        datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
        return [d for d in datos if isinstance(d, dict) and d.get("ruta")]
    except (OSError, ValueError):
        return []


def _guardar(lista):
    try:
        ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
        ARCHIVO.write_text(json.dumps(lista, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as exc:  # sin inventario Pandex funciona igual
        log.warning("no pude guardar el inventario: %s", exc)


def anotar(ruta, motivo):
    ruta = str(Path(ruta))
    lista = [d for d in todo() if d["ruta"] != ruta]
    lista.append({"ruta": ruta, "motivo": motivo, "fecha": f"{datetime.now():%Y-%m-%d %H:%M}"})
    _guardar(lista)


def quitar(ruta):
    ruta = str(Path(ruta))
    lista = todo()
    if any(d["ruta"] == ruta for d in lista):
        _guardar([d for d in lista if d["ruta"] != ruta])
