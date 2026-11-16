"""Actualizar Pandex desde GitHub (menú → «Buscar actualizaciones…»).

Por su cuenta solo **pregunta** una vez al día si hay versión nueva (se apaga en Configuración →
Comportamiento) y lo avisa; instalar es siempre a pedido y con tu confirmación (spec 012).

Se instala la última **versión publicada** (etiqueta ``vX.Y.Z``, con el SHA-256 de su ZIP). Si el
repositorio aún no publicó ninguna, se usa la rama ``main``. Dos caminos, según cómo lo instalaste:

- **Con git** (``git clone``): trae la etiqueta y avanza con ``--ff-only`` (sin versiones
  publicadas, ``git pull --ff-only``). Si cambiaste archivos del proyecto, no fuerza nada y te lo dice.
- **Con ZIP** (*Download ZIP*): baja el ZIP, comprueba su SHA-256 y copia encima. Antes guarda lo
  que va a reemplazar en ``%LOCALAPPDATA%\\Pandex\\respaldos``.

Antes de copiar queda un punto de vuelta (``pandex/vuelta.py``) para «Volver a la versión anterior».

En los dos casos **no se tocan** tus datos: ``config.json``, ``logs/``, ``.venv/``, ``.python/`` ni las
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
# la última versión publicada (etiqueta vX.Y.Z con su ZIP y su .sha256, ver publicar.yml)
URL_PUBLICADA = f"https://api.github.com/repos/{REPO}/releases/latest"
ETIQUETA = re.compile(r"v\d+\.\d+\.\d+")

# lo tuyo: nunca se reemplaza ni se borra
PROTEGIDOS = {"config.json", "config.json.tmp", "logs", ".venv", "venv", ".python", ".git", "__pycache__"}

_SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Archivos que trajeron versiones anteriores y ya no se usan. Una actualización por ZIP
# solo agrega y reemplaza (no sabe qué se quitó), así que la versión nueva los aparta al
# arrancar (``limpiar_obsoletos``). Con git, el pull ya los quitó y esto no hace nada.
OBSOLETOS = (
    "Pandex.bat",
    "pandex/ui/dibujo.py",
    "pandex/ui/rusty.py",
    "pandex/ui/sprites.py",
    "herramientas/preparar_sprite.py",
    "herramientas/gif_a_sprite.py",
    "assets/rusty/spritesheet.png",
    "assets/panda_robot/spritesheet.png",
    "pandex/canvas/firefox.py",
)


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


def _explicar(exc):
    """El mensaje para la persona según lo que pasó de verdad (y no siempre «sin internet»).

    Con la versión 2.1 cualquier falla decía «revisa tu conexión», aunque hubiera internet:
    un antivirus que revisa HTTPS, un proxy o GitHub respondiendo con un error se veían igual.
    """
    import ssl
    import urllib.error

    causa = getattr(exc, "reason", exc)
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code in (403, 429):
            return ("GitHub me pidió esperar un momento (demasiadas consultas). "
                    "Inténtalo de nuevo en unos minutos.")
        return f"GitHub respondió con un error ({exc.code}). Inténtalo de nuevo en unos minutos."
    if isinstance(causa, ssl.SSLError) or "CERTIFICATE" in str(causa).upper():
        return ("No pude verificar la conexión segura con GitHub. Suele pasar cuando un antivirus "
                "o el wifi de la universidad revisa las conexiones HTTPS. Prueba con otra red, o "
                "actualiza a mano (README → Actualizar).")
    if isinstance(causa, TimeoutError) or "timed out" in str(causa).lower():
        return "GitHub tardó demasiado en responder. Inténtalo de nuevo."
    return ("No pude conectarme con GitHub. Revisa tu conexión a internet; si otras páginas "
            "abren bien, mira «Ver registro» para el motivo exacto.")


def _abrir(url, timeout=10, si_falta=False):
    """GET con la librería de Python (urllib): la revisión diaria no carga ``requests``
    (~17 MB que quedarían en memoria hasta cerrar Pandex). Con ``si_falta``, un 404 devuelve None."""
    import urllib.error
    import urllib.request

    from . import red

    try:  # PRI-04: solo GitHub
        red.exigir(url, red.GITHUB)
    except red.ErrorRed as exc:
        log.warning("%s", exc)
        raise ErrorActualizacion("No pude buscar la actualización: la dirección no es de GitHub.") from exc
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Pandex"}),
                                      timeout=timeout)
    except urllib.error.HTTPError as exc:
        if si_falta and exc.code == 404:
            return None
        log.warning("no pude abrir %s: %s: %s", url, type(exc).__name__, exc)
        raise ErrorActualizacion(_explicar(exc)) from exc
    except (urllib.error.URLError, OSError) as exc:
        log.warning("no pude abrir %s: %s: %s", url, type(exc).__name__, exc)  # la causa real
        raise ErrorActualizacion(_explicar(exc)) from exc


def _texto(url):
    with _abrir(url) as r:
        return r.read().decode("utf-8", errors="replace")


def _publicada():
    """La última versión publicada, o None si el repositorio aún no publicó ninguna (ACT-02)."""
    import json

    respuesta = _abrir(URL_PUBLICADA, si_falta=True)
    if respuesta is None:
        return None
    with respuesta:
        try:
            datos = json.loads(respuesta.read().decode("utf-8"))
        except ValueError as exc:
            raise ErrorActualizacion("GitHub respondió algo que no entiendo. Inténtalo de nuevo más tarde.") from exc
    etiqueta = str(datos.get("tag_name") or "")
    if not ETIQUETA.fullmatch(etiqueta):
        log.warning("la versión publicada tiene una etiqueta rara: %r", etiqueta)
        return None
    version = etiqueta[1:]
    archivos = {a.get("name"): a.get("browser_download_url") for a in datos.get("assets") or []
                if isinstance(a, dict)}
    nombre = f"pandex-{version}.zip"
    return {"remota": version, "etiqueta": etiqueta, "zip": archivos.get(nombre),
            "sha256": archivos.get(nombre + ".sha256"), "novedades": str(datos.get("body") or "")}


def buscar():
    """Consulta GitHub. Devuelve ``{"local", "remota", "hay_nueva", "novedades"}``; si hay una
    versión publicada, además ``"etiqueta"``, ``"zip"`` y ``"sha256"`` (sus direcciones)."""
    publicada = _publicada()
    if publicada is not None:
        return {"local": version_local(), "hay_nueva": es_mas_nueva(publicada["remota"], version_local()),
                **publicada}
    remota = leer_version(_texto(URL_VERSION))
    if not remota:
        raise ErrorActualizacion("No pude leer la versión publicada en GitHub.")
    novedades = ""
    if es_mas_nueva(remota, version_local()):
        try:
            novedades = novedades_de(_texto(URL_NOVEDADES), remota)
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


def aplicar(raiz=RAIZ, avisar=lambda texto: None, zip_local=None, info=None):
    """Actualiza la carpeta ``raiz``. Devuelve ``{"modo", "archivos", "respaldo", "dependencias"}``.

    ``info`` es lo que devolvió ``buscar()``: con una versión publicada, se instala esa (con git, su
    etiqueta; con ZIP, su ZIP comprobado con su SHA-256). ``zip_local`` (pruebas): usa ese ZIP.
    """
    info = info or {}
    etiqueta = info.get("etiqueta")
    if etiqueta is not None and not ETIQUETA.fullmatch(str(etiqueta)):
        raise ErrorActualizacion("La versión publicada tiene un nombre que no reconozco; no toqué nada.")
    antes = _huellas(raiz)
    if zip_local is None and modo(raiz) == "git":
        resultado = _con_git(raiz, avisar, etiqueta)
    elif zip_local is None and etiqueta:
        if not info.get("zip") or not info.get("sha256"):
            raise ErrorActualizacion("La versión publicada no trae su huella (SHA-256), así que no la instalo. "
                                     "Inténtalo más tarde.")
        resultado = _con_zip(raiz, avisar, url=info["zip"], sha256=info["sha256"])
    else:
        resultado = _con_zip(raiz, avisar, zip_local)
    resultado["dependencias"] = _huellas(raiz) != antes
    if resultado["dependencias"] and zip_local is None:
        avisar("Instalando dependencias nuevas…")
        instalar_dependencias(raiz)
    return resultado


def _huellas(raiz):
    """Las de todos los ``requirements*.txt``: si cambia el de una función opcional, también."""
    return tuple(_huella(r) for r in sorted(raiz.glob("requirements*.txt")))


def _git(raiz, *args):
    return subprocess.run(["git", "-C", str(raiz), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", creationflags=_SIN_VENTANA)


def _con_git(raiz, avisar, etiqueta=None):
    avisar("Revisando tu copia del proyecto…")
    cambios = _git(raiz, "status", "--porcelain", "--untracked-files=no")
    if cambios.returncode != 0:
        raise ErrorActualizacion(f"git no pudo leer la carpeta:\n{cambios.stderr.strip()}")
    if cambios.stdout.strip():
        archivos = ", ".join(l[3:] for l in cambios.stdout.splitlines()[:5])
        raise ErrorActualizacion(
            "Modificaste archivos del proyecto y no quiero pisarlos: "
            f"{archivos}. Guárdalos con git (commit o stash) y vuelve a intentarlo.")
    anterior = _git(raiz, "rev-parse", "HEAD").stdout.strip()
    avisar("Descargando la versión nueva con git…")
    if etiqueta:  # ACT-02: la versión publicada, no lo último de main
        r = _git(raiz, "fetch", "--no-tags", "origin", f"refs/tags/{etiqueta}:refs/tags/{etiqueta}")
        if r.returncode == 0:
            r = _git(raiz, "merge", "--ff-only", etiqueta)
    else:
        r = _git(raiz, "pull", "--ff-only", "origin", RAMA)
    if r.returncode != 0:
        raise ErrorActualizacion(f"git no pudo traer la versión nueva:\n{(r.stderr or r.stdout).strip()}")
    log.info("actualizado con git: %s", r.stdout.strip().splitlines()[-1:] or "")
    if anterior:
        from . import vuelta

        nueva = (raiz / "pandex" / "__init__.py")
        vuelta.guardar({"modo": "git", "desde": version_local(), "commit": anterior, "estado": "probando",
                        "hacia": leer_version(nueva.read_text(encoding="utf-8")) if nueva.exists() else None,
                        "fecha": datetime.now().isoformat(timespec="seconds")})
    return {"modo": "git", "archivos": None, "respaldo": None}


def _descargar_zip(destino, avisar, url=URL_ZIP):
    avisar("Descargando la versión nueva…")
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _abrir(url, timeout=30) as respuesta, open(destino, "wb") as fh:
            while trozo := respuesta.read(64 * 1024):
                fh.write(trozo)
    except OSError as exc:  # la conexión se cortó a mitad de la descarga
        raise ErrorActualizacion("La descarga se cortó. Inténtalo de nuevo.") from exc
    return destino


def _comprobar(archivo, url_sha256):
    """ACT-02: el ZIP tiene que coincidir con el SHA-256 publicado; si no, no se toca nada."""
    publicado = (_texto(url_sha256).split() or [""])[0].lower()
    if not re.fullmatch(r"[0-9a-f]{64}", publicado):
        raise ErrorActualizacion("La huella publicada (SHA-256) no se puede leer; no toqué nada. Inténtalo más tarde.")
    huella = hashlib.sha256()
    with open(archivo, "rb") as fh:
        while trozo := fh.read(1024 * 1024):
            huella.update(trozo)
    if huella.hexdigest() != publicado:
        log.warning("SHA-256 distinto: esperaba %s y bajé %s", publicado, huella.hexdigest())
        raise ErrorActualizacion("Lo descargado no coincide con la versión publicada; no toqué nada. "
                                 "Vuelve a intentar.")


def _protegido(relativa):
    return any(parte in PROTEGIDOS for parte in relativa.parts)


def _con_zip(raiz, avisar, zip_local=None, url=URL_ZIP, sha256=None):
    trabajo = DATOS / "actualizacion"
    shutil.rmtree(trabajo, ignore_errors=True)
    trabajo.mkdir(parents=True, exist_ok=True)
    try:
        archivo = Path(zip_local) if zip_local else _descargar_zip(trabajo / "pandex.zip", avisar, url)
        avisar("Revisando lo descargado…")
        if sha256:
            _comprobar(archivo, sha256)
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
        for n in range(2, 100):  # dos en el mismo segundo: cada una con su respaldo
            if not respaldo.exists():
                break
            respaldo = respaldo.with_name(f"{respaldo.name.split('_')[0]}_{n}")
        nuevos = [(n, n.relative_to(origen)) for n in sorted(origen.rglob("*"))
                  if n.is_file() and not _protegido(n.relative_to(origen))]
        from . import vuelta

        version_nueva = origen / "pandex" / "__init__.py"
        vuelta.guardar({  # ACT-03: antes de tocar nada, cómo volver
            "modo": "zip", "desde": version_local(), "estado": "probando", "respaldo": str(respaldo),
            "hacia": leer_version(version_nueva.read_text(encoding="utf-8")) if version_nueva.exists() else None,
            "agregados": [r.as_posix() for _n, r in nuevos if not (raiz / r).exists()],
            "fecha": datetime.now().isoformat(timespec="seconds")})
        copiados = 0
        for nuevo, relativa in nuevos:
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
        from .limpieza import RESPALDOS_QUE_QUEDAN, limitar

        limitar(respaldo.parent, "*", RESPALDOS_QUE_QUEDAN, salvo=vuelta.necesarios())  # RES-04
        return {"modo": "zip", "archivos": copiados, "respaldo": respaldo if respaldo.exists() else None}
    finally:
        shutil.rmtree(trabajo, ignore_errors=True)


def limpiar_obsoletos(raiz=RAIZ):
    """Mueve a ``respaldos/obsoletos-<versión>`` lo que la versión actual ya no usa.

    No borra nada: si hiciera falta, se recupera de ahí. Devuelve cuántos movió.
    """
    destino = DATOS / "respaldos" / f"obsoletos-{version_local()}"
    movidos = 0
    for relativa in OBSOLETOS:
        viejo = raiz / relativa
        if not viejo.is_file():
            continue
        try:
            (destino / relativa).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(viejo), str(destino / relativa))
            movidos += 1
            if viejo.suffix == ".py":  # su .pyc ya no sirve
                for pyc in (viejo.parent / "__pycache__").glob(f"{viejo.stem}.*.pyc"):
                    pyc.unlink(missing_ok=True)
            if not any(viejo.parent.iterdir()):
                viejo.parent.rmdir()
        except OSError as exc:
            log.warning("no pude apartar %s: %s", relativa, exc)
    if movidos:
        log.info("aparté %d archivo(s) de versiones anteriores en %s", movidos, destino)
    return movidos


def python_del_proyecto(raiz=RAIZ):
    for candidato in (raiz / ".venv" / "Scripts" / "python.exe", raiz / ".venv" / "bin" / "python"):
        if candidato.exists():
            return candidato
    return Path(sys.executable)


def instalar_dependencias(raiz=RAIZ):
    """Las de siempre y las de las funciones opcionales que ya tenías (nunca agrega otras).

    Después quita los paquetes que la versión nueva ya no pide (p. ej. Playwright o pandas):
    así actualizar también libera espacio. Devuelve la lista de paquetes quitados.
    """
    from . import extras, paquetes

    python = python_del_proyecto(raiz)
    archivos = [raiz / "requirements.txt"]
    archivos += [raiz / extras.EXTRAS[extra]["archivo"] for extra in extras.instalados_en(python)]
    try:
        paquetes.instalar(archivos, python)
    except paquetes.ErrorPaquetes as exc:
        raise ErrorActualizacion(
            "Los archivos se actualizaron, pero no pude instalar las dependencias nuevas. "
            "Ejecuta " + ("instalar.bat" if sys.platform == "win32" else "./instalar.sh") + " para terminar.") from exc
    if not paquetes.es_del_proyecto(python, raiz):
        return []  # sin .venv propio no se quita nada
    try:
        return paquetes.desinstalar(paquetes.huerfanos(archivos, python), python)
    except paquetes.ErrorPaquetes:
        return []  # lo que no se pudo quitar no impide usar la versión nueva
