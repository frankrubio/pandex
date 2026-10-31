"""Iniciar sesión en Canvas con un navegador de verdad, y cerrarlo enseguida.

Pandex nunca ve ni guarda tu usuario o contraseña: inicias sesión tú, en una ventana de
tu navegador (Firefox, Chrome o Edge; ver ``navegador.py``) con un perfil propio, dentro
de la carpeta de datos de Pandex.
Ese perfil recuerda la sesión, así que las siguientes veces entra solo y sin
ventanas. De ahí se sacan las cookies para hablar con la API; el navegador se
cierra apenas la sesión es válida.
"""

import time
from contextlib import contextmanager

from . import navegador as _navegador
from .cliente import CanvasError

ESPERA_SSO = 20  # segundos para que un login institucional (SSO) termine solo


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
    if "net::ERR" in texto or "neterror" in texto:
        return "No hay conexión: no pude llegar a Canvas."
    if isinstance(exc, _navegador.ErrorNavegador) and texto.startswith(("No encontré", "Falta", "No pude")):
        return texto
    return "No pude abrir el navegador para entrar a Canvas."
