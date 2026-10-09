"""Dónde vive cada cosa.

Dos lugares separados a propósito:

- La carpeta del proyecto: el código, los recursos y tu ``config.json``.
- ``%LOCALAPPDATA%\\Pandex``: lo que Pandex genera y no debe ir a GitHub ni a
  OneDrive (la sesión del navegador, el historial de Canvas, temporales).
"""

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

TASKS_DIR = RAIZ / "tasks"
ASSETS_DIR = RAIZ / "assets"
ICONO = ASSETS_DIR / "pandex.ico"
CONFIG_FILE = RAIZ / "config.json"
LOGS_DIR = RAIZ / "logs"
LOG_FILE = LOGS_DIR / "pandex.log"


def _carpeta_de_datos():
    """``%LOCALAPPDATA%\\Pandex``. La variable ``PANDEX_DATOS`` la reemplaza
    (las pruebas la usan para no tocar nunca tus datos reales)."""
    propia = os.environ.get("PANDEX_DATOS")
    if propia:
        return Path(propia)
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    datos = base / "Pandex"
    legado = base / "MascotaUTEC"  # nombre que usaban las primeras versiones
    if not legado.is_dir():
        return datos
    if not datos.exists():
        try:
            legado.rename(datos)
            return datos
        except OSError:  # p. ej. el navegador tiene el perfil abierto
            return legado
    # existen las dos: manda la que tiene el historial más reciente
    return max((datos, legado), key=_ultimo_uso)


def _ultimo_uso(carpeta):
    historiales = (carpeta / "historial_canvas.json", carpeta / "registro_canvas.json")
    return max((h.stat().st_mtime for h in historiales if h.exists()), default=0)


DATOS = _carpeta_de_datos()
# los personajes que añades tú (Configuración → Apariencia → Añadir personaje)
PERSONAJES_PROPIOS = DATOS / "personajes"
