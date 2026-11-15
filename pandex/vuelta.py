"""Volver a la versión anterior después de actualizar (spec 012, ACT-03 a ACT-05).

``actualizar.aplicar()`` guarda un **punto de vuelta** en ``DATOS/actualizacion.json`` antes de
copiar la versión nueva. Con él, «Volver a la versión anterior» devuelve lo reemplazado, aparta
(no borra) lo agregado y, con git, hace ``git reset --keep`` (no pisa cambios tuyos).

Si la versión nueva no llega a abrir, ``main.py`` llama a ``si_no_abrio()``: vuelve sola y la
versión anterior lo dice al abrir. Por eso este módulo solo usa la biblioteca estándar y ``rutas``:
tiene que funcionar aunque la versión nueva venga rota.
"""

import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path, PurePosixPath

from .rutas import DATOS, RAIZ

ARCHIVO = DATOS / "actualizacion.json"
RESPALDOS = DATOS / "respaldos"

# estados del punto: "probando" (recién actualizado, aún no abrió), "ok" (abrió bien),
# "devuelta" (no abrió y se volvió sola; falta avisar)
_SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class ErrorVuelta(Exception):
    """No se pudo volver; el mensaje se le muestra a la persona tal cual."""


def leer():
    try:
        punto = json.loads(ARCHIVO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return punto if isinstance(punto, dict) and punto.get("modo") in ("zip", "git") else None


def guardar(punto):
    ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
    temporal = ARCHIVO.with_name(ARCHIVO.name + ".tmp")
    with open(temporal, "w", encoding="utf-8") as fh:
        json.dump(punto, fh, ensure_ascii=False, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(temporal, ARCHIVO)


def _olvidar():
    try:
        ARCHIVO.unlink(missing_ok=True)
    except OSError:
        pass


def hay_punto():
    """¿Se puede volver a la versión anterior?"""
    punto = leer()
    return punto is not None and punto.get("estado") in ("probando", "ok")


def arranco():
    """La versión nueva abrió bien: un fallo de aquí en adelante ya no es motivo para volver."""
    punto = leer()
    if punto and punto.get("estado") == "probando":
        punto["estado"] = "ok"
        guardar(punto)


def _relativa(texto):
    """Una ruta del punto, solo si queda dentro de la carpeta de Pandex."""
    ruta = PurePosixPath(str(texto))
    if ruta.is_absolute() or ".." in ruta.parts or not ruta.parts:
        raise ErrorVuelta("El punto de vuelta está dañado; no toqué nada.")
    return Path(*ruta.parts)


def _mover(origen, destino):
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(origen), str(destino))


def _volver_zip(punto, raiz):
    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    deshecho = RESPALDOS / f"deshecho-{punto.get('hacia') or 'nueva'}-{marca}"
    agregados = [_relativa(r) for r in punto.get("agregados", [])]
    respaldo = Path(punto["respaldo"]) if punto.get("respaldo") else None
    for relativa in agregados:  # lo que trajo la nueva: se aparta, no se borra
        actual = raiz / relativa
        if actual.is_file():
            _mover(actual, deshecho / relativa)
    if respaldo is not None and respaldo.is_dir():
        for guardado in sorted(respaldo.rglob("*")):
            if not guardado.is_file():
                continue
            relativa = guardado.relative_to(respaldo)
            actual = raiz / relativa
            if actual.is_file():
                _mover(actual, deshecho / relativa)
            actual.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(guardado, actual)
    obsoletos = RESPALDOS / f"obsoletos-{punto.get('hacia')}"
    if punto.get("hacia") and obsoletos.is_dir():  # lo que la nueva apartó y la anterior usa
        for apartado in sorted(obsoletos.rglob("*")):
            if apartado.is_file() and not (raiz / apartado.relative_to(obsoletos)).exists():
                _mover(apartado, raiz / apartado.relative_to(obsoletos))


def _volver_git(punto, raiz):
    commit = str(punto.get("commit") or "")
    if not commit or not all(c in "0123456789abcdef" for c in commit.lower()):
        raise ErrorVuelta("El punto de vuelta está dañado; no toqué nada.")
    r = subprocess.run(["git", "-C", str(raiz), "reset", "--keep", commit], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", creationflags=_SIN_VENTANA)
    if r.returncode != 0:
        raise ErrorVuelta("Cambiaste archivos del proyecto y no quiero pisarlos. Guárdalos con git "
                          "(commit o stash) y vuelve a intentarlo.")


def volver(raiz=RAIZ):
    """Vuelve a la versión anterior. Devuelve el punto usado. Lanza ``ErrorVuelta``."""
    punto = leer()
    if punto is None:
        raise ErrorVuelta("No hay una versión anterior a la que volver.")
    try:
        (_volver_git if punto["modo"] == "git" else _volver_zip)(punto, Path(raiz))
    except OSError as exc:
        raise ErrorVuelta("No pude devolver todos los archivos. Cierra lo que use la carpeta de Pandex "
                          "y vuelve a intentarlo.") from exc
    _olvidar()
    return punto


def si_no_abrio(raiz=RAIZ):
    """Lo llama ``main.py`` si Pandex no pudo arrancar: si fue justo después de actualizar,
    vuelve a la versión anterior y devuelve True."""
    punto = leer()
    if not punto or punto.get("estado") != "probando":
        return False
    volver(raiz)
    guardar({**punto, "estado": "devuelta"})
    return True


def aviso_pendiente():
    """El mensaje para la persona tras volver sola, una sola vez; si no hay, None."""
    punto = leer()
    if not punto or punto.get("estado") != "devuelta":
        return None
    _olvidar()
    return f"La versión {punto.get('hacia') or 'nueva'} no abrió; volví a la {punto.get('desde')}."
