"""Actualizar Pandex desde GitHub, a pedido (menú → «Buscar actualizaciones…»).

Nunca se conecta solo: solo cuando lo pides. Dos caminos, según cómo lo instalaste:

- **Con git** (``git clone``): ``git pull --ff-only``. Si cambiaste archivos del
  proyecto, no fuerza nada y te lo dice.
- **Con ZIP** (*Download ZIP*): baja el ZIP de la rama ``main`` y copia encima.
  Antes guarda lo que va a reemplazar en ``%LOCALAPPDATA%\\Pandex\\respaldos``.

En los dos casos **no se tocan** tus datos: ``config.json``, ``logs/``, ``.venv/`` ni las
tareas propias que agregaste en ``tasks/``. Si cambió ``requirements.txt``, se
instalan las dependencias nuevas en el ``.venv``.
"""

import hashlib
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from . import __version__
from .log import get_logger
from .rutas import DATOS, RAIZ

log = get_logger("pandex.actualizar")

REPO = "frankrubio/pandex"
RAMA = "main"
URL_VERSION = f"https://raw.githubusercontent.com/{REPO}/{RAMA}/pandex/__init__.py"
URL_NOVEDADES = f"https://raw.githubusercontent.com/{REPO}/{RAMA}/CHANGELOG.md"
URL_ZIP = f"https://codeload.github.com/{REPO}/zip/refs/heads/{RAMA}"
URL_PAGINA = f"https://github.com/{REPO}"

# lo tuyo: nunca se reemplaza ni se borra
PROTEGIDOS = {"config.json", "config.json.tmp", "logs", ".venv", "venv", ".git", "__pycache__"}

_SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class ErrorActualizacion(Exception):
    """Algo impidió actualizar; el mensaje se le muestra a la persona tal cual."""


# ---------- versiones ----------


def version_local():
    return __version__


def partes(version):
    """``"2.1.0"`` → ``(2, 1, 0)``; lo que no es número se ignora."""
    return tuple(int(n) for n in re.findall(r"\d+", str(version))[:3]) or (0,)


def es_mas_nueva(remota, local):
    return partes(remota) > partes(local)


def leer_version(texto):
    m = re.search(r"""__version__\s*=\s*["']([^"']+)["']""", texto)
    return m.group(1) if m else None


def novedades_de(changelog, version=None):
    """La primera sección (``## …``) del CHANGELOG: lo que trae la versión nueva."""
    secciones = re.split(r"(?m)^## ", changelog)
    for seccion in secciones[1:]:
        if version is None or seccion.split("\n", 1)[0].find(version) >= 0:
            return "## " + seccion.strip()
    return ""


def _get(url, timeout=10, stream=False):
    import requests  # al usarlo: no retrasa el arranque

    try:
        r = requests.get(url, timeout=timeout, stream=stream, headers={"User-Agent": "Pandex"})
        r.raise_for_status()
        return r
    except requests.RequestException as exc:
        raise ErrorActualizacion(
            "No pude conectarme con GitHub. Revisa tu conexión a internet e inténtalo de nuevo."
        ) from exc


def buscar():
    """Consulta GitHub. Devuelve ``{"local", "remota", "hay_nueva", "novedades"}``."""
    remota = leer_version(_get(URL_VERSION).text)
    if not remota:
        raise ErrorActualizacion("No pude leer la versión publicada en GitHub.")
    novedades = ""
    if es_mas_nueva(remota, version_local()):
        try:
            novedades = novedades_de(_get(URL_NOVEDADES).text, remota)
        except ErrorActualizacion:
            pass  # sin novedades no pasa nada
    return {"local": version_local(), "remota": remota,
            "hay_nueva": es_mas_nueva(remota, version_local()), "novedades": novedades}


# ---------- aplicar ----------


def modo(raiz=RAIZ):
    """``"git"`` si es un clon con git disponible; si no, ``"zip"``."""
    return "git" if (raiz / ".git").exists() and shutil.which("git") else "zip"


def _huella(ruta):
    return hashlib.sha256(ruta.read_bytes()).hexdigest() if ruta.exists() else None


def aplicar(raiz=RAIZ, avisar=lambda texto: None, zip_local=None):
    """Actualiza la carpeta ``raiz``. Devuelve ``{"modo", "archivos", "respaldo", "dependencias"}``.

    ``zip_local`` (pruebas): usa ese ZIP en vez de descargarlo.
    """
    antes = _huella(raiz / "requirements.txt")
    if zip_local is None and modo(raiz) == "git":
        resultado = _con_git(raiz, avisar)
    else:
        resultado = _con_zip(raiz, avisar, zip_local)
    resultado["dependencias"] = _huella(raiz / "requirements.txt") != antes
    if resultado["dependencias"] and zip_local is None:
        avisar("Instalando dependencias nuevas…")
        instalar_dependencias(raiz)
    return resultado


def _git(raiz, *args):
    return subprocess.run(["git", "-C", str(raiz), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", creationflags=_SIN_VENTANA)


def _con_git(raiz, avisar):
    avisar("Revisando tu copia del proyecto…")
    cambios = _git(raiz, "status", "--porcelain", "--untracked-files=no")
    if cambios.returncode != 0:
        raise ErrorActualizacion(f"git no pudo leer la carpeta:\n{cambios.stderr.strip()}")
    if cambios.stdout.strip():
        archivos = ", ".join(l[3:] for l in cambios.stdout.splitlines()[:5])
        raise ErrorActualizacion(
            "Modificaste archivos del proyecto y no quiero pisarlos: "
            f"{archivos}. Guárdalos con git (commit o stash) y vuelve a intentarlo.")
    avisar("Descargando la versión nueva con git…")
    r = _git(raiz, "pull", "--ff-only", "origin", RAMA)
    if r.returncode != 0:
        raise ErrorActualizacion(f"git pull no pudo terminar:\n{(r.stderr or r.stdout).strip()}")
    log.info("actualizado con git: %s", r.stdout.strip().splitlines()[-1:] or "")
    return {"modo": "git", "archivos": None, "respaldo": None}


def _descargar_zip(destino, avisar):
    avisar("Descargando la versión nueva…")
    respuesta = _get(URL_ZIP, timeout=30, stream=True)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "wb") as fh:
        for trozo in respuesta.iter_content(64 * 1024):
            fh.write(trozo)
    return destino


def _protegido(relativa):
    return any(parte in PROTEGIDOS for parte in relativa.parts)


def _con_zip(raiz, avisar, zip_local=None):
    trabajo = DATOS / "actualizacion"
    shutil.rmtree(trabajo, ignore_errors=True)
    trabajo.mkdir(parents=True, exist_ok=True)
    try:
        archivo = Path(zip_local) if zip_local else _descargar_zip(trabajo / "pandex.zip", avisar)
        avisar("Revisando lo descargado…")
        try:
            with zipfile.ZipFile(archivo) as z:
                for nombre in z.namelist():  # nada de rutas que se salgan de la carpeta
                    if nombre.startswith("/") or ".." in Path(nombre).parts:
                        raise ErrorActualizacion("El archivo descargado no es válido.")
                z.extractall(trabajo / "nuevo")
        except zipfile.BadZipFile as exc:
            raise ErrorActualizacion("El archivo descargado está dañado. Inténtalo de nuevo.") from exc

        carpetas = [c for c in (trabajo / "nuevo").iterdir() if c.is_dir()]
        origen = carpetas[0] if len(carpetas) == 1 else trabajo / "nuevo"
        if not (origen / "main.py").exists() or not (origen / "pandex").is_dir():
            raise ErrorActualizacion("Lo descargado no parece ser Pandex; no toqué nada.")

        avisar("Copiando los archivos nuevos…")
        respaldo = DATOS / "respaldos" / f"{version_local()}-{datetime.now():%Y%m%d-%H%M%S}"
        copiados = 0
        for nuevo in sorted(origen.rglob("*")):
            if not nuevo.is_file():
                continue
            relativa = nuevo.relative_to(origen)
            if _protegido(relativa):
                continue
            actual = raiz / relativa
            if actual.exists():
                if actual.read_bytes() == nuevo.read_bytes():
                    continue
                guardar = respaldo / relativa
                guardar.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(actual, guardar)
            actual.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(nuevo, actual)
            copiados += 1
        log.info("actualizado desde ZIP: %d archivo(s); respaldo en %s", copiados, respaldo)
        return {"modo": "zip", "archivos": copiados, "respaldo": respaldo if respaldo.exists() else None}
    finally:
        shutil.rmtree(trabajo, ignore_errors=True)


def python_del_proyecto(raiz=RAIZ):
    for candidato in (raiz / ".venv" / "Scripts" / "python.exe", raiz / ".venv" / "bin" / "python"):
        if candidato.exists():
            return candidato
    return Path(sys.executable)


def instalar_dependencias(raiz=RAIZ):
    r = subprocess.run(
        [str(python_del_proyecto(raiz)), "-m", "pip", "install", "-r", str(raiz / "requirements.txt"),
         "--quiet", "--disable-pip-version-check"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=_SIN_VENTANA,
    )
    if r.returncode != 0:
        log.error("pip falló: %s", r.stderr)
        raise ErrorActualizacion(
            "Los archivos se actualizaron, pero no pude instalar las dependencias nuevas. "
            "Ejecuta instalar.bat para terminar.")
