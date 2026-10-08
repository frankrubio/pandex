"""Iniciar sesión en Canvas con un navegador de verdad, y cerrarlo enseguida.

Pandex nunca ve ni guarda tu usuario o contraseña: inicias sesión tú, en una
ventana de Chrome con un perfil propio (``%LOCALAPPDATA%\\Pandex\\browser-profile``).
Ese perfil recuerda la sesión, así que las siguientes veces entra solo y sin
ventanas. De ahí se sacan las cookies para hablar con la API; el navegador se
cierra apenas la sesión es válida.
"""

import time

from ..rutas import DATOS
from .cliente import CanvasError

PERFIL = DATOS / "browser-profile"
ESPERA_SSO = 20  # segundos para que un login institucional (SSO) termine solo


# Playwright se carga al usarlo, no al abrir Pandex: son ~14 MB y ~0,1 s de arranque
# que la mascota no necesita mientras no inicies sesión en Canvas.
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
    """La clase de error de Playwright, para usarla en un ``except``."""
    _cargar()
    return PlaywrightError


def _abrir_contexto(pw, headless, usar_chrome):
    PERFIL.mkdir(parents=True, exist_ok=True)
    opciones = {"user_data_dir": str(PERFIL), "headless": headless,
                "viewport": {"width": 1366, "height": 900}}
    if usar_chrome:
        try:
            return pw.chromium.launch_persistent_context(channel="chrome", **opciones)
        except PlaywrightError:
            pass  # sin Chrome instalado: el Chromium de Playwright
    return pw.chromium.launch_persistent_context(**opciones)


def _sesion_valida(contexto, base):
    try:
        return contexto.request.get(f"{base}/api/v1/users/self", timeout=15000).status == 200
    except PlaywrightError:
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


def iniciar_sesion(ctx, base, usar_chrome=True, espera_login=300, invisible_primero=True):
    """Entra a Canvas y devuelve ``(cookies, user_agent)``.

    ``ctx`` es cualquier objeto con ``log(msg, nivel)`` y ``decir(texto)``.
    Primero prueba sin ventana (si ya hay una sesión guardada); si no alcanza,
    abre el navegador para que entres tú.
    """
    _cargar()
    with sync_playwright() as pw:
        if invisible_primero and (PERFIL / "Default").exists():
            contexto = _abrir_contexto(pw, True, usar_chrome)
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
        contexto = _abrir_contexto(pw, False, usar_chrome)
        try:
            page, ua = _pagina(contexto)
            page.goto(base, wait_until="domcontentloaded", timeout=60000)
            try:
                dentro = _esperar_sesion(contexto, page, base, espera_login, 2000)
            except PlaywrightError as exc:
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
    """Una frase útil para el globo a partir de un error de Playwright."""
    if "net::ERR" in str(exc):
        return "No hay conexión: no pude llegar a Canvas."
    if "Executable doesn't exist" in str(exc):
        return ("No encontré un navegador. Instala Google Chrome o ejecuta: "
                "python -m playwright install chromium")
    return "No pude abrir el navegador para entrar a Canvas."
