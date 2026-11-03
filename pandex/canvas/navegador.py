"""Tu navegador (Firefox, Chrome o Edge) controlado con Selenium, en Windows y en Linux.

Pandex no descarga navegadores: usa el que ya tienes, con un perfil propio dentro de la
carpeta de datos (no toca tus pestañas, tu historial ni tus contraseñas). Lo único que
se descarga, la primera vez, es el «driver» que deja a Selenium manejarlo (3 a 15 MB). Va
a ``DATOS/navegadores`` y se borra al desinstalar.

Por defecto se usa **tu navegador predeterminado**, si es uno de los tres. Si no, el
primero que encuentre: Edge → Chrome → Firefox en Windows (Edge siempre está), y
Firefox → Chrome → Edge en Linux. Se puede elegir en Configuración → Tareas → Sincronizar
Canvas.

Imita las pocas piezas de Playwright que usa ``sesion.py`` (contexto, pestaña, pedidos y
cookies), así el inicio de sesión es el mismo con cualquier navegador.
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from ..log import get_logger
from ..rutas import DATOS, NAVEGADORES, WINDOWS

log = get_logger("pandex.navegador")

TODOS = ("firefox", "chrome", "edge")
# Google rechaza el inicio de sesión («software de pruebas automatizadas está controlando…»)
# si Selenium controla Chrome o Edge. Ahí la persona entra en una ventana normal, sin control
# remoto, y Pandex solo comprueba después con el navegador sin ventana.
VENTANA_NORMAL = ("chrome", "edge")
NOMBRES = {"firefox": "Firefox", "chrome": "Google Chrome", "edge": "Microsoft Edge"}
ORDEN = ("edge", "chrome", "firefox") if WINDOWS else ("firefox", "chrome", "edge")

PERFILES = {
    "firefox": DATOS / "browser-profile-firefox",
    "chrome": DATOS / "browser-profile",  # el mismo que usaba Playwright: la sesión sigue
    "edge": DATOS / "browser-profile-edge",
}

INSTALAR_LINUX = {
    "firefox": "sudo apt install firefox",
    "chrome": "descárgalo de google.com/chrome",
    "edge": "descárgalo de microsoft.com/edge",
}

_LINUX = {
    "firefox": ("firefox", "firefox-esr"),
    "chrome": ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"),
    "edge": ("microsoft-edge", "microsoft-edge-stable"),
}
_WINDOWS = {
    "firefox": (r"Mozilla Firefox\firefox.exe",),
    "chrome": (r"Google\Chrome\Application\chrome.exe",),
    "edge": (r"Microsoft\Edge\Application\msedge.exe",),
}


class ErrorNavegador(Exception):
    """El navegador no abrió, o lo cerraste."""


# ---------- cuál ----------


def ruta(nombre):
    """Dónde está instalado ``nombre`` (``firefox``, ``chrome`` o ``edge``), o None."""
    if WINDOWS:
        bases = [os.environ.get(v) for v in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")]
        for base in filter(None, bases):
            for relativa in _WINDOWS[nombre]:
                candidato = Path(base) / relativa
                if candidato.is_file():
                    return str(candidato)
        return None
    for programa in _LINUX[nombre]:
        encontrado = shutil.which(programa)
        if encontrado:
            return encontrado
    return None


def instalados():
    return [n for n in TODOS if ruta(n)]


def predeterminado():
    """Tu navegador predeterminado, si es Firefox, Chrome o Edge (si no, None). Solo lee."""
    try:
        if WINDOWS:
            import winreg

            clave = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, clave) as k:
                texto = winreg.QueryValueEx(k, "ProgId")[0]
        else:
            texto = subprocess.run(["xdg-settings", "get", "default-web-browser"], capture_output=True,
                                   text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    texto = texto.lower()
    if "firefox" in texto:
        return "firefox"
    if "msedge" in texto or "microsoft-edge" in texto:
        return "edge"
    if "chrome" in texto or "chromium" in texto:
        return "chrome"
    return None


def elegir(preferido="auto"):
    """El navegador a usar. ``preferido``: ``auto`` (el tuyo) o uno de ``TODOS``.

    Lanza ``ErrorNavegador`` si el elegido (o ninguno) está instalado.
    """
    if preferido in TODOS:
        if ruta(preferido):
            return preferido
        raise ErrorNavegador(f"No encontré {NOMBRES[preferido]}. Instálalo o elige otro navegador en "
                             "Configuración → Tareas → Sincronizar Canvas.")
    tuyo = predeterminado()
    if tuyo and ruta(tuyo):
        return tuyo
    for nombre in ORDEN:
        if ruta(nombre):
            return nombre
    raise ErrorNavegador("No encontré Firefox, Chrome ni Edge. Instala uno (en Linux: "
                         f"{INSTALAR_LINUX['firefox']}) y vuelve a intentar.")


def _snap(binario):
    """``/snap/<nombre>/…`` → ``<nombre>``; si no viene de snap, None."""
    partes = Path(binario).resolve().parts
    return partes[2] if len(partes) > 2 and partes[1] == "snap" else None


def perfil(nombre, binario=None):
    """La carpeta del perfil de Pandex. Un navegador de snap (Ubuntu) no puede entrar a carpetas
    ocultas de tu casa: ahí va en ``~/snap/<navegador>/common/pandex-perfil``."""
    binario = binario or ruta(nombre)
    snap = _snap(binario) if binario and not WINDOWS else None
    if snap:
        return Path.home() / "snap" / snap / "common" / "pandex-perfil"
    return PERFILES[nombre]


def hay_sesion(nombre):
    """¿Ya se inició sesión alguna vez con este navegador? (Si no, ni intentar sin ventana.)"""
    try:
        carpeta = perfil(nombre)
    except OSError:
        return False
    return (carpeta / ("cookies.sqlite" if nombre == "firefox" else "Default")).exists()


# ---------- el contexto (lo que usa sesion.py) ----------


class _Respuesta:
    def __init__(self, status):
        self.status = status


def _del_sitio(dominio, host):
    """¿Una cookie de ``dominio`` va a ``host``? (Como el navegador: el mismo o uno padre.)"""
    if not dominio:
        return True  # sin dominio: es de la página actual
    dominio = dominio.lstrip(".").lower()
    host = (host or "").lower()
    return host == dominio or host.endswith("." + dominio)


class _Pedidos:
    """``contexto.request.get(url).status`` con las cookies del navegador que son de ese sitio.

    Solo las de ese sitio: mientras inicias sesión, la página puede estar en el login de tu
    institución (p. ej. Microsoft) y sus cookies no deben llegar a Canvas (P1).
    """

    def __init__(self, contexto):
        self._contexto = contexto

    def get(self, url, timeout=15000):
        from urllib.parse import urlsplit

        import requests

        host = urlsplit(url).hostname
        try:
            ua = self._contexto.driver.execute_script("return navigator.userAgent")
            frasco = {c["name"]: c["value"] for c in self._contexto.cookies() if _del_sitio(c.get("domain"), host)}
            r = requests.get(url, cookies=frasco, headers={"User-Agent": ua},
                             timeout=timeout / 1000, allow_redirects=False)
        except Exception as exc:  # navegador cerrado o sin red: para quien llama, «aún no»
            raise ErrorNavegador(str(exc)) from exc
        return _Respuesta(r.status_code)


class _Pestana:
    def __init__(self, driver):
        self.driver = driver

    def evaluate(self, js):
        try:
            return self.driver.execute_script(f"return {js}")
        except Exception as exc:
            raise ErrorNavegador(str(exc)) from exc

    def goto(self, url, wait_until=None, timeout=60000):
        from selenium.common.exceptions import TimeoutException

        try:
            self.driver.set_page_load_timeout(timeout / 1000)
            self.driver.get(url)
        except TimeoutException:
            pass  # la página sigue cargando (SSO): se sigue preguntando a la API
        except Exception as exc:
            raise ErrorNavegador(str(exc)) from exc

    def wait_for_timeout(self, ms):
        try:
            self.driver.current_url  # si cerraste la ventana, esto falla
        except Exception as exc:
            raise ErrorNavegador("cerraste el navegador") from exc
        time.sleep(ms / 1000)


class Contexto:
    def __init__(self, driver):
        self.driver = driver
        self.pages = [_Pestana(driver)]
        self.request = _Pedidos(self)

    def cookies(self):
        try:
            return [{"name": c["name"], "value": c["value"], "domain": c.get("domain"),
                     "path": c.get("path", "/")} for c in self.driver.get_cookies()]
        except Exception as exc:
            raise ErrorNavegador(str(exc)) from exc

    def new_page(self):
        return self.pages[0]

    def close(self):
        try:
            self.driver.quit()
        except Exception:
            pass


# ---------- abrir ----------


def _driver_del_sistema(nombre, binario):
    """Un driver que ya trae el sistema (p. ej. el de snap), para no descargar otro."""
    programa = {"firefox": "geckodriver", "chrome": "chromedriver", "edge": "msedgedriver"}[nombre]
    encontrado = shutil.which(programa)
    if encontrado:
        return encontrado
    snap = _snap(binario) if not WINDOWS else None
    if snap:
        for candidato in (f"/snap/bin/{programa}", f"/snap/bin/{snap}.{programa}"):
            if Path(candidato).exists():
                return candidato
    return None


def _opciones(webdriver, nombre, binario, carpeta, headless):
    if nombre == "firefox":
        opciones = webdriver.FirefoxOptions()
        opciones.add_argument("-profile")
        opciones.add_argument(str(carpeta))
        if headless:
            opciones.add_argument("-headless")
    else:
        opciones = webdriver.EdgeOptions() if nombre == "edge" else webdriver.ChromeOptions()
        for argumento in (f"--user-data-dir={carpeta}", "--no-first-run", "--no-default-browser-check",
                          "--window-size=1366,900", "--disable-blink-features=AutomationControlled"):
            opciones.add_argument(argumento)
        opciones.add_experimental_option("excludeSwitches", ["enable-automation"])
        if headless:
            opciones.add_argument("--headless=new")
    opciones.binary_location = binario
    opciones.page_load_strategy = "eager"  # como «domcontentloaded»: no esperar imágenes
    return opciones


def abrir_ventana_normal(nombre, url):
    """Abre ``url`` en una ventana normal de ``nombre`` con el perfil de Pandex (sin control remoto).

    Devuelve el proceso: cuando la persona cierra la ventana, termina. Lanza ``ErrorNavegador``.
    """
    binario = ruta(nombre)
    if binario is None:
        raise ErrorNavegador(f"No encontré {NOMBRES[nombre]}. Instálalo o elige otro navegador en "
                             "Configuración → Tareas → Sincronizar Canvas.")
    carpeta = perfil(nombre, binario)
    carpeta.mkdir(parents=True, exist_ok=True)
    comando = [binario, f"--user-data-dir={carpeta}", "--no-first-run", "--no-default-browser-check",
               "--disable-background-mode", "--disable-features=msStartupBoost,StartupBoost", url]
    try:
        return subprocess.Popen(comando)
    except OSError as exc:
        log.error("%s no abrió: %s", NOMBRES[nombre], exc)
        raise ErrorNavegador(f"No pude abrir {NOMBRES[nombre]}. Ciérralo si estaba abierto con Pandex y "
                             "vuelve a intentar.") from exc


def abrir(nombre, headless):
    """Abre ``nombre`` con el perfil de Pandex. Lanza ``ErrorNavegador`` si no puede."""
    binario = ruta(nombre)
    if binario is None:
        raise ErrorNavegador(f"No encontré {NOMBRES[nombre]}."
                             + ("" if WINDOWS else f" Instálalo ({INSTALAR_LINUX[nombre]}) o elige otro "
                                "en Configuración → Tareas → Sincronizar Canvas."))
    try:
        from selenium import webdriver
    except ImportError as exc:
        raise ErrorNavegador("Falta Selenium: ejecuta " + ("instalar.bat" if WINDOWS else "./instalar.sh")
                             + " de nuevo.") from exc

    # el driver que descarga Selenium va a la carpeta de Pandex (no a ~/.cache/selenium)
    NAVEGADORES.mkdir(parents=True, exist_ok=True)
    os.environ["SE_CACHE_PATH"] = str(NAVEGADORES)
    os.environ.setdefault("SE_AVOID_STATS", "true")  # Selenium Manager no manda estadísticas (P1)

    carpeta = perfil(nombre, binario)
    if not carpeta.exists() and not carpeta.is_relative_to(DATOS):
        from ..inventario import anotar

        anotar(carpeta, f"perfil de {NOMBRES[nombre]} (snap)")
    carpeta.mkdir(parents=True, exist_ok=True)
    opciones = _opciones(webdriver, nombre, binario, carpeta, headless)
    clase, servicio = {
        "firefox": (webdriver.Firefox, webdriver.FirefoxService),
        "chrome": (webdriver.Chrome, webdriver.ChromeService),
        "edge": (webdriver.Edge, webdriver.EdgeService),
    }[nombre]
    propio = _driver_del_sistema(nombre, binario)
    try:
        driver = clase(options=opciones, service=servicio(executable_path=propio) if propio else servicio())
    except Exception as exc:
        log.error("%s no abrió: %s", NOMBRES[nombre], exc)
        raise ErrorNavegador(f"No pude abrir {NOMBRES[nombre]}. Ciérralo si estaba abierto con Pandex, "
                             "revisa tu internet (la primera vez descarga un componente pequeño) y vuelve "
                             "a intentar. El detalle está en «Ver registro».") from exc
    if nombre == "firefox":
        try:
            driver.set_window_size(1366, 900)
        except Exception:
            pass
    return Contexto(driver)


if __name__ == "__main__":  # diagnóstico: python -m pandex.canvas.navegador
    print("Instalados:", ", ".join(NOMBRES[n] for n in instalados()) or "ninguno")
    print("Predeterminado:", NOMBRES.get(predeterminado() or "", "otro o desconocido"))
    try:
        print("Pandex usaría:", NOMBRES[elegir()])
    except ErrorNavegador as exc:
        print(exc)
    sys.exit(0)
