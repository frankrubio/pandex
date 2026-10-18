"""Funciones opcionales: solo se instalan si las quieres.

«Convertir a Markdown» trae su conversor y el OCR (unos 280 MB). Si no lo usas, Pandex no
lo instala, no lo muestra en el menú y queda más liviano. Se puede añadir después desde
Configuración → Tareas, con un clic.

Una tarea dice qué necesita con ``requiere = "markdown"`` (ver ``tasks/convertir_md.py``).
"""

import importlib.util
import subprocess
import sys

from .log import get_logger
from .rutas import RAIZ

log = get_logger("pandex.extras")

EXTRAS = {
    "markdown": {
        "nombre": "Convertir a Markdown",
        "archivo": "requirements-markdown.txt",
        "modulos": ("markitdown", "pypdfium2"),
        "peso": "unos 280 MB",
    },
}


class ErrorExtra(Exception):
    pass


def instalado(extra):
    """¿Están sus librerías en este Python? (Sin importarlas: es instantáneo.)"""
    if not extra:
        return True
    datos = EXTRAS.get(extra)
    if datos is None:
        return True
    importlib.invalidate_caches()
    return all(importlib.util.find_spec(m) is not None for m in datos["modulos"])


def disponible(tarea):
    return instalado(getattr(tarea, "requiere", None))


def instalados_en(python):
    """Los extras que tiene otro Python (el del proyecto, al actualizar)."""
    salida = []
    for extra, datos in EXTRAS.items():
        codigo = ("import importlib.util, sys; sys.exit(0 if all(importlib.util.find_spec(m) "
                  f"for m in {datos['modulos']!r}) else 1)")
        try:
            if subprocess.run([str(python), "-c", codigo], capture_output=True, timeout=60).returncode == 0:
                salida.append(extra)
        except (OSError, subprocess.SubprocessError):
            pass
    return salida


def instalar(extra, python=None, raiz=RAIZ):
    """``pip install -r <su archivo>`` en el Python de Pandex. Tarda unos minutos."""
    datos = EXTRAS[extra]
    python = python or sys.executable
    log.info("instalando %s (%s)", extra, datos["archivo"])
    r = subprocess.run(
        [str(python), "-m", "pip", "install", "-r", str(raiz / datos["archivo"]),
         "--quiet", "--disable-pip-version-check"],
        capture_output=True, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if r.returncode != 0:
        log.error("pip falló instalando %s:\n%s", extra, r.stderr[-3000:])
        raise ErrorExtra(f"No pude instalar «{datos['nombre']}». ¿Hay internet? El detalle está en «Ver registro».")
    importlib.invalidate_caches()
