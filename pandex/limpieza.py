"""Liberar espacio: lo que Pandex ya no usa, con su tamaño (ADR-0001, D4).

Dos clases de cosas:

- **De Pandex** (se limpian solas, sin preguntar): respaldos de actualizaciones (quedan los 2
  más nuevos), copias de la configuración de Canvas (quedan 3) y paquetes del ``.venv`` que
  ya no pide nadie (p. ej. Playwright o pandas tras actualizar).
- **Fuera de Pandex** (se pregunta, con casillas): cachés que dejaron versiones anteriores
  (pip, el driver de Firefox de Selenium, el Chromium de Playwright) y otra copia de Pandex
  en otra carpeta. Las cachés se vuelven a descargar solas si otro programa las necesita.

Sin Qt: la ventana está en ``pandex/ui/limpieza.py``.
"""

import fnmatch
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .log import get_logger
from .rutas import CONFIG_FILE, DATOS, RAIZ, WINDOWS

log = get_logger("pandex.limpieza")

RESPALDOS_QUE_QUEDAN = 2
COPIAS_DE_CONFIG_QUE_QUEDAN = 3
MINIMO_PARA_AVISAR = 20 * 1024 * 1024  # menos que esto no vale una ventana


@dataclass
class Elemento:
    clave: str
    nombre: str
    rutas: list = field(default_factory=list)
    tamano: int = 0
    marcado: bool = True
    nota: str = ""


def tamano(ruta):
    """Bytes de un archivo o carpeta (sin seguir enlaces). 0 si no existe."""
    ruta = Path(ruta)
    try:
        if ruta.is_symlink() or ruta.is_file():
            return ruta.lstat().st_size
    except OSError:
        return 0
    total = 0
    for base, _carpetas, archivos in os.walk(ruta):
        for nombre in archivos:
            try:
                total += os.lstat(os.path.join(base, nombre)).st_size
            except OSError:
                pass
    return total


def texto_tamano(n):
    if n < 1024 * 1024:
        return f"{max(n // 1024, 1)} KB" if n else "0 MB"
    if n < 1024 ** 3:
        return f"{n / 1024 ** 2:.0f} MB"
    return f"{n / 1024 ** 3:.1f} GB"


def _borrar(ruta):
    ruta = Path(ruta)
    if ruta.is_dir() and not ruta.is_symlink():
        shutil.rmtree(ruta)
    else:
        ruta.unlink(missing_ok=True)


# ---------- lo de Pandex: se limpia solo ----------


def sobrantes(carpeta, patron, quedan):
    """Lo que sobra en ``carpeta`` (coincide con ``patron``) dejando los ``quedan`` más nuevos."""
    carpeta = Path(carpeta)
    if not carpeta.is_dir():
        return []
    todos = [p for p in carpeta.iterdir() if fnmatch.fnmatch(p.name, patron)]
    todos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return todos[quedan:]


def limitar(carpeta, patron, quedan):
    """Borra lo que sobra (RES-04/RES-05). Devuelve los bytes liberados."""
    liberado = 0
    for viejo in sobrantes(carpeta, patron, quedan):
        peso = tamano(viejo)
        try:
            _borrar(viejo)
            liberado += peso
        except OSError as exc:
            log.warning("no pude borrar %s: %s", viejo, exc)
    return liberado


def limpiar_propio():
    """Respaldos y copias de configuración de más. Devuelve los bytes liberados."""
    return (limitar(DATOS / "respaldos", "*", RESPALDOS_QUE_QUEDAN)
            + limitar(DATOS, "config-canvas-anterior-*.json", COPIAS_DE_CONFIG_QUE_QUEDAN))


def quitar_paquetes_sobrantes(raiz=RAIZ):
    """Quita del ``.venv`` lo que ya no pide ningún requirements. Devuelve los bytes liberados."""
    from . import actualizar, extras, paquetes

    python = actualizar.python_del_proyecto(raiz)
    if not paquetes.es_del_proyecto(python, raiz):
        return 0  # sin .venv propio no se quita nada (p. ej. en las pruebas)
    archivos = [raiz / "requirements.txt"]
    archivos += [raiz / extras.EXTRAS[e]["archivo"] for e in extras.instalados_en(python)]
    sobran = paquetes.huerfanos(archivos, python)
    if not sobran:
        return 0
    venv = raiz / ".venv"
    antes = tamano(venv)
    try:
        paquetes.desinstalar(sobran, python)
    except paquetes.ErrorPaquetes:
        pass  # lo que se pudo quitar, quitado; el resto queda para la próxima
    return max(antes - tamano(venv), 0)


# ---------- lo de fuera: se pregunta ----------


def _cache_de_usuario():
    if WINDOWS:
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")


def caches_viejas():
    """Lo que dejaban las versiones anteriores a la 2.5 fuera de Pandex."""
    base = _cache_de_usuario()
    candidatos = [
        ("pip", "Copias de paquetes de Python (caché de pip)", base / ("pip/Cache" if WINDOWS else "pip"),
         "Las dejaba el instalador. Si otro programa de Python las necesita, las vuelve a descargar."),
        ("selenium", "Driver de Firefox de versiones anteriores", Path.home() / ".cache" / "selenium",
         "Ahora va en la carpeta de Pandex."),
        ("playwright", "Navegador Chromium que descargaba Pandex", base / "ms-playwright",
         "Pandex ya no lo usa: entra a Canvas con tu navegador."),
    ]
    elementos = []
    for clave, nombre, ruta, nota in candidatos:
        if ruta.exists():
            peso = tamano(ruta)
            if peso:
                elementos.append(Elemento(clave, nombre, [ruta], peso, True, nota))
    return elementos


def carpetas_protegidas(raiz=RAIZ):
    """Carpetas que nunca se borran con otra copia: tus cursos (Canvas) y los datos de Pandex."""
    import json

    carpetas = [DATOS]
    try:
        datos = json.loads((Path(raiz) / CONFIG_FILE.name).read_text(encoding="utf-8"))
        destino = datos.get("tareas", {}).get("sync_canvas", {}).get("destino")
        if destino:
            carpetas.append(Path(destino))
    except (OSError, ValueError, AttributeError):
        pass
    return carpetas


def _contiene(carpeta, otra):
    try:
        return Path(otra).resolve().is_relative_to(Path(carpeta).resolve())
    except OSError:
        return True  # ante la duda, se protege


def copias_anteriores(raiz=RAIZ, protegidas=None):
    """Otras copias de Pandex en esta PC (instalaste en otra carpeta).

    No se ofrece una copia que guarda tus cursos o los datos de Pandex.
    """
    from . import accesos

    protegidas = carpetas_protegidas(raiz) if protegidas is None else protegidas
    elementos = []
    for carpeta in accesos.instalaciones_anteriores(raiz):
        if any(_contiene(carpeta, p) for p in protegidas):
            log.info("no ofrezco borrar %s: guarda tus cursos o datos de Pandex", carpeta)
            continue
        elementos.append(Elemento(
            f"copia:{carpeta}", "Otra copia de Pandex", [carpeta], tamano(carpeta), False,
            f"{carpeta} · Tu configuración ya está en esta copia. Va a la papelera."))
    return elementos


def externos(raiz=RAIZ):
    return caches_viejas() + copias_anteriores(raiz)


def liberar(elementos, papelera=None):
    """Borra las rutas de ``elementos``. Una copia de Pandex solo se manda a la papelera
    (``papelera(ruta) -> bool``): si no se puede, queda donde está y se lista (P4: deshacer).

    Devuelve ``(bytes_liberados, [rutas que no se pudieron borrar])``.
    """
    liberado, fallidos = 0, []
    for elemento in elementos:
        quedan = []
        for ruta in elemento.rutas:
            try:
                if elemento.clave.startswith("copia:"):
                    if not (papelera and papelera(ruta)):
                        log.warning("no pude mandar %s a la papelera; no la borro", ruta)
                else:
                    _borrar(ruta)
            except OSError as exc:
                log.warning("no pude borrar %s: %s", ruta, exc)
            if Path(ruta).exists():
                quedan.append(ruta)
        if quedan:
            fallidos += quedan
        else:
            liberado += elemento.tamano
            log.info("liberado: %s (%s)", elemento.nombre, texto_tamano(elemento.tamano))
    return liberado, fallidos


def al_estrenar_version(raiz=RAIZ):
    """Lo que se hace la primera vez que abre una versión nueva: limpia lo propio y lista lo de fuera.

    Devuelve ``{"liberado": bytes, "externos": [Elemento]}``.
    """
    liberado = limpiar_propio()
    try:
        liberado += quitar_paquetes_sobrantes(raiz)
    except Exception as exc:  # nunca impide usar Pandex
        log.warning("no pude revisar los paquetes que sobran: %s", exc)
    return {"liberado": liberado, "externos": externos(raiz)}
