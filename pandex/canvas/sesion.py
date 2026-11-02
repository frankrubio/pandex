"""Iniciar sesión en Canvas con un navegador de verdad, y cerrarlo enseguida.

Pandex nunca ve ni guarda tu usuario o contraseña: inicias sesión tú, en una ventana de
tu navegador (Firefox, Chrome o Edge; ver ``navegador.py``) con un perfil propio, dentro
de la carpeta de datos de Pandex.
Ese perfil recuerda la sesión, así que las siguientes veces entra solo y sin
ventanas. De ahí se sacan las cookies para hablar con la API; el navegador se
cierra apenas la sesión es válida.
"""

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

from ..log import get_logger
from ..rutas import DATOS
from . import navegador as _navegador
from .cliente import CanvasError

log = get_logger("pandex.sesion")

ESPERA_SSO = 20  # segundos para que un login institucional (SSO) termine solo

# Atajo de sesión (spec 001, T001.3): las cookies de Canvas de la última vez que entraste.
# Mientras Canvas las acepte, no hace falta abrir el navegador (~4 s menos). Son las mismas
# que ya guarda el perfil del navegador, en la misma carpeta de datos y solo para tu usuario.
# Nunca van al registro; se borran si Canvas las rechaza y al desinstalar.
ATAJO = DATOS / "sesion_canvas.json"
ULTIMO = {"modo": None, "espera_manual": 0.0}  # cómo entró la última vez, para el registro de fases


def error_navegador():
    """Las clases de error del navegador, para un ``except``."""
    return (_navegador.ErrorNavegador,)


def elegir_navegador(navegador="auto", usar_chrome=True):
    """``"firefox"``, ``"chrome"`` o ``"edge"``. ``"auto"``: tu navegador predeterminado.

    ``usar_chrome`` queda por compatibilidad con configuraciones viejas (no hace nada).
    """
    return _navegador.elegir(navegador)


def _hay_perfil(navegador):
    return _navegador.hay_sesion(navegador)


@contextmanager
def _abridor(navegador, usar_chrome=True):
    """Da ``abrir(headless) -> contexto`` y los errores a esperar."""
    yield (lambda headless: _navegador.abrir(navegador, headless)), error_navegador()


def _sesion_valida(contexto, base):
    try:
        return contexto.request.get(f"{base}/api/v1/users/self", timeout=15000).status == 200
    except Exception:  # navegador ocupado redirigiendo o sin red: para nosotros, «todavía no»
        return False


def _esperar_sesion(contexto, page, base, segundos, paso_ms):
    """Pregunta a la API si ya estás dentro mientras la página hace sus redirecciones.

    Mirar la URL una sola vez no sirve: si el SSO va a medio camino, parece que
    la sesión caducó cuando en realidad está entrando.
    """
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if _sesion_valida(contexto, base):
            return True
        page.wait_for_timeout(paso_ms)  # si cerraste la ventana, esto lanza error
    return False


def _pagina(contexto):
    """La pestaña y su user agent, leído ANTES de navegar.

    Leerlo al final fallaba («Execution context was destroyed») si Canvas seguía
    redirigiendo al panel justo cuando la sesión ya era válida.
    """
    page = contexto.pages[0] if contexto.pages else contexto.new_page()
    return page, page.evaluate("navigator.userAgent")


def guardar_atajo(base, cookies, user_agent):
    """Guarda solo las cookies del sitio de Canvas (no las del login de tu institución)."""
    from urllib.parse import urlsplit

    host = urlsplit(base).hostname
    propias = [{"name": c["name"], "value": c["value"], "domain": c.get("domain"), "path": c.get("path", "/")}
               for c in cookies if _navegador._del_sitio(c.get("domain"), host)]
    try:
        ATAJO.parent.mkdir(parents=True, exist_ok=True)
        temporal = ATAJO.with_name(ATAJO.name + ".tmp")
        fd = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"base": base.rstrip("/"), "ua": user_agent, "cookies": propias}, fh)
        os.replace(temporal, ATAJO)
        log.info("sesión guardada para la próxima vez (%d cookies)", len(propias))
    except OSError as exc:  # sin atajo Pandex funciona igual, solo un poco más lento
        log.warning("no pude guardar la sesión: %s", exc)


def olvidar_atajo():
    try:
        ATAJO.unlink(missing_ok=True)
    except OSError as exc:
        log.warning("no pude borrar la sesión guardada: %s", exc)


def intentar_atajo(base):
    """``(cookies, user_agent)`` si la sesión guardada sigue valiendo; si no, None.

    Una sola pregunta a ``/api/v1/users/self`` (~0,3 s). Si Canvas la rechaza, se borra. Si no
    hay red, se conserva (el problema no es la sesión).
    """
    try:
        datos = json.loads(Path(ATAJO).read_text(encoding="utf-8"))
        guardado, cookies, ua = datos["base"], datos["cookies"], datos["ua"]
    except FileNotFoundError:
        return None
    except (OSError, ValueError, KeyError, TypeError):
        olvidar_atajo()
        return None
    if guardado != base.rstrip("/") or not cookies:
        olvidar_atajo()
        return None
    import requests

    try:
        r = requests.get(f"{guardado}/api/v1/users/self", cookies={c["name"]: c["value"] for c in cookies},
                         headers={"User-Agent": ua}, timeout=8, allow_redirects=False)
    except requests.RequestException as exc:
        log.info("no pude probar la sesión guardada: %s", exc.__class__.__name__)
        return None
    if r.status_code != 200:
        log.info("la sesión guardada ya no vale (Canvas respondió %s)", r.status_code)
        olvidar_atajo()
        return None
    return cookies, ua


def iniciar_sesion(ctx, base, usar_chrome=True, espera_login=300, invisible_primero=True,
                   navegador="auto"):
    """Entra a Canvas y devuelve ``(cookies, user_agent)``.

    ``ctx`` es cualquier objeto con ``log(msg, nivel)`` y ``decir(texto)``.
    Primero prueba la sesión guardada (sin navegador); luego el navegador sin ventana con tu
    perfil; si no alcanza, abre la ventana para que entres tú. ``ULTIMO`` dice cuál de las tres.
    """
    ULTIMO.update(modo=None, espera_manual=0.0)
    entrada = intentar_atajo(base)
    if entrada:
        ULTIMO["modo"] = "atajo"
        ctx.log("sesión guardada válida: no abrí el navegador")
        return entrada
    navegador = elegir_navegador(navegador, usar_chrome)
    with _abridor(navegador, usar_chrome) as (abrir, errores):
        if invisible_primero and _hay_perfil(navegador):
            contexto = abrir(True)
            try:
                page, ua = _pagina(contexto)
                page.goto(base, wait_until="domcontentloaded", timeout=60000)
                if _esperar_sesion(contexto, page, base, ESPERA_SSO, 500):
                    ctx.log("sesión renovada sin abrir ventanas")
                    ULTIMO["modo"] = "navegador"
                    cookies = contexto.cookies()
                    guardar_atajo(base, cookies, ua)
                    return cookies, ua
            finally:
                contexto.close()
            ctx.log("hace falta iniciar sesión a mano", "warning")

        ctx.decir("Necesito que inicies sesión en Canvas: te abrí el navegador.")
        espera = time.monotonic()
        contexto = abrir(False)
        try:
            page, ua = _pagina(contexto)
            page.goto(base, wait_until="domcontentloaded", timeout=60000)
            try:
                dentro = _esperar_sesion(contexto, page, base, espera_login, 2000)
            except errores as exc:
                raise CanvasError("Cerraste el navegador antes de terminar de iniciar sesión.") from exc
            if not dentro:
                raise CanvasError("Se acabó el tiempo para iniciar sesión en Canvas.")
            ctx.log("sesión iniciada a mano, queda guardada en el perfil")
            ctx.decir("¡Listo, ya entré! Cierro el navegador y sigo yo.")
            ULTIMO.update(modo="manual", espera_manual=time.monotonic() - espera)
            cookies = contexto.cookies()
            guardar_atajo(base, cookies, ua)
            return cookies, ua
        finally:
            try:
                contexto.close()
            except Exception:
                pass


def mensaje_de_error(exc):
    """Una frase útil para el globo a partir de un error del navegador."""
    texto = str(exc)
    if "net::ERR" in texto or "neterror" in texto:
        return "No hay conexión: no pude llegar a Canvas."
    if isinstance(exc, _navegador.ErrorNavegador) and texto.startswith(("No encontré", "Falta", "No pude")):
        return texto
    return "No pude abrir el navegador para entrar a Canvas."
