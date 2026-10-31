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
        "peso": "unos 200 MB",
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
    from . import paquetes

    datos = EXTRAS[extra]
    log.info("instalando %s (%s)", extra, datos["archivo"])
    try:
        paquetes.instalar([raiz / datos["archivo"]], python or sys.executable)
    except paquetes.ErrorPaquetes as exc:
        raise ErrorExtra(f"No pude instalar «{datos['nombre']}». ¿Hay internet? "
                         "El detalle está en «Ver registro».") from exc
    importlib.invalidate_caches()


def quitar(extra, python=None, raiz=RAIZ):
    """Quita los paquetes que solo usaba ``extra`` (los de la base y de otros extras quedan).

    Devuelve la lista de paquetes quitados.
    """
    from . import paquetes

    python = python or sys.executable
    datos = EXTRAS[extra]
    siguen = [raiz / "requirements.txt"] + [
        raiz / EXTRAS[otro]["archivo"] for otro in instalados_en(python) if otro != extra]
    sobran = paquetes.huerfanos(siguen, python)
    try:
        quitados = paquetes.desinstalar(sobran, python)
    except paquetes.ErrorPaquetes as exc:
        raise ErrorExtra(f"No pude quitar «{datos['nombre']}» del todo. "
                         "El detalle está en «Ver registro».") from exc
    importlib.invalidate_caches()
    return quitados
