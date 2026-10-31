"""Instalar y quitar paquetes del ``.venv`` de Pandex sin dejar copias fuera de él.

Todo ``pip`` pasa por aquí, para que nada se olvide de estas dos opciones:

- ``--no-cache-dir``: pip no guarda una copia de cada paquete en ``~/.cache/pip`` (o
  ``%LOCALAPPDATA%\\pip\\Cache``). Eso eran cientos de MB fuera de Pandex.
- ``--no-compile``: no crea los ``.pyc`` de todos los archivos (unos 40 MB). Python crea
  los que hagan falta la primera vez que importa cada módulo.

``huerfanos`` dice qué paquetes ya no pide ningún ``requirements*.txt`` (ni como
dependencia): al actualizar se quitan, así una versión nueva que deja de usar algo
(p. ej. Playwright o pandas) también libera ese espacio.
"""

import json
import subprocess
import sys
from pathlib import Path

from .log import get_logger

log = get_logger("pandex.paquetes")

OPCIONES = ("--no-cache-dir", "--no-compile", "--disable-pip-version-check", "--quiet")
# nunca se quitan: sin ellos no se puede volver a instalar nada
INTOCABLES = frozenset({"pip", "setuptools", "wheel"})

_SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class ErrorPaquetes(Exception):
    """pip no pudo terminar; ``detalle`` trae su salida para el registro."""

    def __init__(self, mensaje, detalle=""):
        super().__init__(mensaje)
        self.detalle = detalle


def _pip(python, *args):
    return subprocess.run(
        [str(python or sys.executable), "-m", "pip", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=_SIN_VENTANA,
    )


def instalar(archivos, python=None):
    """``pip install -r a -r b …`` sin caché ni ``.pyc``. Lanza ``ErrorPaquetes`` si falla."""
    requisitos = [arg for archivo in archivos for arg in ("-r", str(archivo))]
    r = _pip(python, "install", *requisitos, *OPCIONES)
    if r.returncode != 0:
        log.error("pip install falló:\n%s", r.stderr[-3000:])
        raise ErrorPaquetes("pip no pudo instalar los paquetes.", r.stderr)
    return r


def desinstalar(paquetes, python=None):
    """``pip uninstall -y`` de esos paquetes (nunca pip, setuptools ni wheel)."""
    paquetes = sorted({p for p in paquetes if normalizar(p) not in INTOCABLES})
    if not paquetes:
        return []
    r = _pip(python, "uninstall", "-y", "--disable-pip-version-check", *paquetes)
    if r.returncode != 0:
        log.warning("pip uninstall no terminó bien:\n%s", r.stderr[-3000:])
        raise ErrorPaquetes("pip no pudo quitar algunos paquetes.", r.stderr)
    log.info("quité %d paquete(s) que ya no se usan: %s", len(paquetes), ", ".join(paquetes))
    return paquetes


def normalizar(nombre):
    """``Charset_Normalizer`` → ``charset-normalizer`` (como PyPI)."""
    import re

    return re.sub(r"[-_.]+", "-", nombre).lower()


# Corre dentro del Python del proyecto (puede no ser el que ejecuta Pandex): recibe las
# rutas de los requirements y devuelve en JSON los paquetes instalados que nadie pide.
_CALCULAR = r"""
import json, re, sys
from importlib import metadata
try:
    from packaging.requirements import Requirement
except ImportError:
    from pip._vendor.packaging.requirements import Requirement

def norm(n):
    return re.sub(r"[-_.]+", "-", n).lower()

def pedidos(archivo):
    for linea in open(archivo, encoding="utf-8"):
        linea = linea.split("#", 1)[0].strip()
        if linea and not linea.startswith("-"):
            yield Requirement(linea)

def aplica(req, extra=""):
    return req.marker is None or req.marker.evaluate({"extra": extra})

pendientes = [r for archivo in sys.argv[1:] for r in pedidos(archivo) if aplica(r)]
necesarios = set()
while pendientes:
    req = pendientes.pop()
    nombre = norm(req.name)
    clave = (nombre, tuple(sorted(req.extras)))
    if clave in necesarios:
        continue
    necesarios.add(clave)
    try:
        dist = metadata.distribution(req.name)
    except metadata.PackageNotFoundError:
        continue
    for texto in dist.requires or []:
        dep = Requirement(texto)
        if aplica(dep) or any(aplica(dep, e) for e in req.extras):
            pendientes.append(dep)

usados = {n for n, _ in necesarios}
instalados = {norm(d.metadata["Name"]) for d in metadata.distributions() if d.metadata["Name"]}
print(json.dumps(sorted(instalados - usados)))
"""


def es_del_proyecto(python, raiz):
    """¿``python`` es el del ``.venv`` de Pandex? Solo ahí se quitan paquetes (nunca del Python
    de tu sistema ni del de otro proyecto)."""
    try:
        return Path(python).absolute().parent.parent.resolve() == Path(raiz, ".venv").resolve()
    except (OSError, TypeError):
        return False


def huerfanos(archivos, python=None):
    """Paquetes instalados que no pide ningún ``archivos`` (requirements), ni como dependencia.

    Si algo falla al calcular, devuelve ``[]``: ante la duda, no se quita nada.
    """
    archivos = [str(a) for a in archivos if Path(a).is_file()]
    if not archivos:
        return []
    try:
        r = subprocess.run([str(python or sys.executable), "-c", _CALCULAR, *archivos],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=120, creationflags=_SIN_VENTANA)
        sobran = json.loads(r.stdout) if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        log.warning("no pude calcular los paquetes que sobran: %s", exc)
        return []
    if sobran is None:
        log.warning("no pude calcular los paquetes que sobran:\n%s", r.stderr[-2000:])
        return []
    return [p for p in sobran if p not in INTOCABLES]
