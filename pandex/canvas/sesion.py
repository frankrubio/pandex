"""Iniciar sesión en Canvas con un navegador de verdad, y cerrarlo enseguida.

Pandex nunca ve ni guarda tu usuario o contraseña: inicias sesión tú, en una
ventana de Chrome (Windows) o de Firefox (Linux) con un perfil propio, dentro de la
carpeta de datos de Pandex.
Ese perfil recuerda la sesión, así que las siguientes veces entra solo y sin
ventanas. De ahí se sacan las cookies para hablar con la API; el navegador se
cierra apenas la sesión es válida.
"""

import sys
import time
from contextlib import contextmanager

from ..rutas import DATOS
from .cliente import CanvasError

PERFIL = DATOS / "browser-profile"
PERFIL_FIREFOX = DATOS / "browser-profile-firefox"
ESPERA_SSO = 20  # segundos para que un login institucional (SSO) termine solo


# Playwright (Windows) y Selenium (Linux) se cargan al usarlos, no al abrir Pandex: la
# mascota no los necesita mientras no inicies sesión en Canvas.
PlaywrightError = None
sync_playwright = None


def _cargar():
    global PlaywrightError, sync_playwright
    if PlaywrightError is None or sync_playwright is None:
        from playwright.sync_api import Error
        from playwright.sync_api import sync_playwright as abrir

        PlaywrightError = PlaywrightError or Error
        sync_playwright = sync_playwright or abrir


def error_navegador():
    """Las clases de error del navegador (Playwright y/o Firefox), para un ``except``."""
    from .firefox import ErrorFirefox

    errores = [ErrorFirefox]
    try:
        _cargar()
        errores.append(PlaywrightError)
    except ImportError:  # en Linux no se instala Playwright
        pass
    return tuple(errores)


def elegir_navegador(navegador="auto", usar_chrome=True):
    """``"firefox"`` o ``"chrome"``. ``"auto"``: tu Firefox en Linux; en Windows, Chrome
    (o el Chromium de Playwright si no está instalado)."""
    if navegador in ("firefox", "chrome"):
        return navegador
    return "firefox" if sys.platform.startswith("linux") else "chrome"


def _perfil(navegador):
    if navegador == "firefox":
        from .firefox import perfil_para

        return perfil_para(PERFIL_FIREFOX)
    return PERFIL


def _hay_perfil(navegador):
    """¿Ya se inició sesión alguna vez con este navegador? (Si no, ni intentar sin ventana.)"""
    carpeta = _perfil(navegador)
    return (carpeta / ("cookies.sqlite" if navegador == "firefox" else "Default")).exists()


def _abrir_contexto(pw, headless, usar_chrome, navegador="chrome"):
    carpeta = _perfil(navegador)
    carpeta.mkdir(parents=True, exist_ok=True)
    opciones = {"user_data_dir": str(carpeta), "headless": headless,
                "viewport": {"width": 1366, "height": 900}}
    if usar_chrome:
        try:
            return pw.chromium.launch_persistent_context(channel="chrome", **opciones)
        except PlaywrightError:
            pass  # sin Chrome instalado: el Chromium de Playwright
    return pw.chromium.launch_persistent_context(**opciones)


@contextmanager
def _abridor(navegador, usar_chrome):
    """Da ``abrir(headless) -> contexto`` y los errores a esperar, según el navegador."""
    if navegador == "firefox":
        from . import firefox

        yield (lambda headless: firefox.abrir(_perfil("firefox"), headless)), (firefox.ErrorFirefox,)
        return
    _cargar()
    with sync_playwright() as pw:
        yield (lambda headless: _abrir_contexto(pw, headless, usar_chrome, navegador)), (PlaywrightError,)


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


def iniciar_sesion(ctx, base, usar_chrome=True, espera_login=300, invisible_primero=True,
                   navegador="auto"):
    """Entra a Canvas y devuelve ``(cookies, user_agent)``.

    ``ctx`` es cualquier objeto con ``log(msg, nivel)`` y ``decir(texto)``.
    Primero prueba sin ventana (si ya hay una sesión guardada); si no alcanza,
    abre el navegador para que entres tú.
    """
    navegador = elegir_navegador(navegador, usar_chrome)
    with _abridor(navegador, usar_chrome) as (abrir, errores):
        if invisible_primero and _hay_perfil(navegador):
            contexto = abrir(True)
            try:
                page, ua = _pagina(contexto)
                page.goto(base, wait_until="domcontentloaded", timeout=60000)
                if _esperar_sesion(contexto, page, base, ESPERA_SSO, 500):
                    ctx.log("sesión renovada sin abrir ventanas")
                    return contexto.cookies(), ua
            finally:
                contexto.close()
            ctx.log("hace falta iniciar sesión a mano", "warning")

        ctx.decir("Necesito que inicies sesión en Canvas: te abrí el navegador.")
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
            return contexto.cookies(), ua
        finally:
            try:
                contexto.close()
            except Exception:
                pass


def mensaje_de_error(exc):
    """Una frase útil para el globo a partir de un error del navegador."""
    texto = str(exc)
    if "net::ERR" in texto:
        return "No hay conexión: no pude llegar a Canvas."
    from .firefox import ErrorFirefox

    if isinstance(exc, ErrorFirefox):
        return texto if texto.startswith(("No encontré", "Falta", "No pude")) else \
            "No pude abrir Firefox para entrar a Canvas."
    if "Executable doesn't exist" in texto:
        return ("No encontré un navegador. Instala Google Chrome o ejecuta: "
                "python -m playwright install chromium")
    return "No pude abrir el navegador para entrar a Canvas."
