"""Instalar y quitar paquetes del ``.venv`` de Pandex sin dejar copias fuera de él.

Todo ``pip`` pasa por aquí, para que nada se olvide de estas dos opciones:

- ``--no-cache-dir``: pip no guarda una copia de cada paquete en ``~/.cache/pip`` (o
  ``%LOCALAPPDATA%\\pip\\Cache``). Eso eran cientos de MB fuera de Pandex.
- ``--no-compile``: no crea los ``.pyc`` de todos los archivos (unos 40 MB). Python crea
  los que hagan falta la primera vez que importa cada módulo.

``huerfanos`` dice qué paquetes ya no pide ningún ``requirements*.txt`` (ni como
dependencia): al actualizar se quitan, así una versión nueva que deja de usar algo
(p. ej. Playwright o pandas) también libera ese espacio.

Un requisito con el comentario ``# pandex: sin-dependencias`` se instala con ``--no-deps`` y sus
dependencias no cuentan como pedidas: así MarkItDown no trae Magika, onnxruntime ni numpy (unos
150 MB que Pandex no usa). Lo que sí usa va en el mismo archivo, en su propia línea (spec 002, PES-10).

Los instaladores lo llaman así: ``python -m pandex.paquetes requirements-markdown.txt``.
"""

import json
import shlex
import subprocess
import sys
from pathlib import Path

from .log import get_logger

log = get_logger("pandex.paquetes")

OPCIONES = ("--no-cache-dir", "--no-compile", "--disable-pip-version-check", "--quiet")
SIN_DEPENDENCIAS = "pandex: sin-dependencias"  # comentario que marca un requisito a instalar con --no-deps
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


def _sin_comentario(linea):
    """``(requisito, comentario)``: como pip, el comentario empieza en un «#» al inicio o tras un espacio."""
    import re

    partes = re.split(r"(?:^|\s)#", linea, maxsplit=1)
    return partes[0].strip(), (partes[1] if len(partes) > 1 else "")


def _separar(archivo):
    """``(requisitos, sin_dependencias)`` de un requirements; los primeros listos para pip."""
    normales, sueltos = [], []
    for linea in Path(archivo).read_text(encoding="utf-8").splitlines():
        requisito, comentario = _sin_comentario(linea)
        if not requisito:
            continue
        if SIN_DEPENDENCIAS in comentario:
            sueltos.append(requisito)
        else:
            normales += shlex.split(requisito) if requisito.startswith("-") else [requisito]
    return normales, sueltos


def instalar(archivos, python=None):
    """``pip install -r a -r b …`` sin caché ni ``.pyc``. Lanza ``ErrorPaquetes`` si falla.

    Lo marcado con ``# pandex: sin-dependencias`` va en un segundo ``pip install --no-deps``.
    """
    requisitos, sin_dependencias = [], []
    for archivo in archivos:
        normales, sueltos = _separar(archivo)
        if sueltos:
            requisitos += normales
            sin_dependencias += sueltos
        else:
            requisitos += ["-r", str(archivo)]
    r = None
    for argumentos in (requisitos, ["--no-deps", *sin_dependencias] if sin_dependencias else []):
        if not argumentos:
            continue
        r = _pip(python, "install", *argumentos, *OPCIONES)
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
        partes = re.split(r"(?:^|\s)#", linea, maxsplit=1)
        requisito, comentario = partes[0].strip(), (partes[1] if len(partes) > 1 else "")
        if requisito and not requisito.startswith("-"):
            yield Requirement(requisito), "pandex: sin-dependencias" not in comentario

def aplica(req, extra=""):
    return req.marker is None or req.marker.evaluate({"extra": extra})

pendientes = [(r, seguir) for archivo in sys.argv[1:] for r, seguir in pedidos(archivo) if aplica(r)]
necesarios = set()
while pendientes:
    req, seguir = pendientes.pop()
    nombre = norm(req.name)
    clave = (nombre, tuple(sorted(req.extras)))
    if clave in necesarios:
        continue
    necesarios.add(clave)
    if not seguir:
        continue  # instalado con --no-deps: lo que pide no cuenta
    try:
        dist = metadata.distribution(req.name)
    except metadata.PackageNotFoundError:
        continue
    for texto in dist.requires or []:
        dep = Requirement(texto)
        if aplica(dep) or any(aplica(dep, e) for e in req.extras):
            pendientes.append((dep, True))

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


def main(argumentos=None):
    """``python -m pandex.paquetes requirements-x.txt …``: instala como Pandex (lo usan los instaladores)."""
    archivos = list(sys.argv[1:] if argumentos is None else argumentos)
    try:
        instalar(archivos)
    except ErrorPaquetes as exc:
        print(exc.detalle[-3000:] or exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
