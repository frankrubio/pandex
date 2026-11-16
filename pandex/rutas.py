"""Dónde vive cada cosa.

Dos lugares separados a propósito:

- La carpeta del proyecto: el código, los recursos y tu ``config.json``.
- ``%LOCALAPPDATA%\\Pandex`` en Windows, ``~/.local/share/Pandex`` en Linux: lo que
  Pandex genera y no debe ir a GitHub ni a OneDrive (la sesión del navegador, el
  historial de Canvas, temporales).
"""

import os
import sys
from pathlib import Path

WINDOWS = sys.platform == "win32"

RAIZ = Path(__file__).resolve().parent.parent

TASKS_DIR = RAIZ / "tasks"
ASSETS_DIR = RAIZ / "assets"
ICONO = ASSETS_DIR / "pandex.ico"
CONFIG_FILE = RAIZ / "config.json"
LOGS_DIR = RAIZ / "logs"
LOG_FILE = LOGS_DIR / "pandex.log"


def _carpeta_de_datos():
    """``%LOCALAPPDATA%\\Pandex`` (Windows) o ``~/.local/share/Pandex`` (Linux). La variable
    ``PANDEX_DATOS`` la reemplaza (las pruebas la usan para no tocar nunca tus datos reales)."""
    propia = os.environ.get("PANDEX_DATOS")
    if propia:
        return Path(propia)
    if WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
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
# los drivers que baja Selenium para manejar tu navegador (no van a ~/.cache)
NAVEGADORES = DATOS / "navegadores"


def privado(ruta):
    """En Linux, solo tú puedes leerlo: carpetas 0700, archivos 0600 (spec 004, PRI-06).
    En Windows no hace nada: la carpeta de datos ya es solo tuya (``%LOCALAPPDATA%``)."""
    if WINDOWS:
        return ruta
    try:
        os.chmod(ruta, 0o700 if Path(ruta).is_dir() else 0o600)
    except OSError:  # no es tuyo o no existe: no se insiste
        pass
    return ruta


def carpeta_privada(carpeta):
    """Crea ``carpeta`` (perfil del navegador…) solo para ti. Si está dentro de la carpeta de
    datos, esa también queda privada."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    if carpeta.is_relative_to(DATOS):
        privado(DATOS)
    return privado(carpeta)
