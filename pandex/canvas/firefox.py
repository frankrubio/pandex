"""El Firefox que ya tienes instalado, controlado con Selenium (Linux).

Playwright solo sabe manejar su propia copia de Firefox (unos 80 MB más). Selenium usa
el tuyo: solo necesita ``geckodriver`` (unos 3 MB), que se descarga solo la primera vez.

Imita las pocas piezas de Playwright que usa ``sesion.py`` (contexto, pestaña, pedidos y
cookies), así el inicio de sesión es el mismo con cualquier navegador. El perfil es propio
de Pandex: no toca tus pestañas, tu historial ni tus contraseñas.
"""

import shutil
import time
from pathlib import Path

from ..log import get_logger

log = get_logger("pandex.firefox")

INSTALAR = "sudo apt install firefox"


class ErrorFirefox(Exception):
    """Firefox no abrió, o lo cerraste."""


def instalado():
    """La ruta de Firefox, o None."""
    return shutil.which("firefox") or shutil.which("firefox-esr")


def _es_snap(binario):
    return str(Path(binario).resolve()).startswith("/snap/")


def perfil_para(perfil, binario=None):
    """El Firefox de snap (Ubuntu) no puede entrar a carpetas ocultas de tu casa: ahí el
    perfil va en ``~/snap/firefox/common``."""
    binario = binario or instalado()
    if binario and _es_snap(binario):
        return Path.home() / "snap" / "firefox" / "common" / "pandex-perfil"
    return Path(perfil)


class _Respuesta:
    def __init__(self, status):
        self.status = status


class _Pedidos:
    """``contexto.request.get(url).status`` con las cookies que tiene Firefox ahora."""

    def __init__(self, contexto):
        self._contexto = contexto

    def get(self, url, timeout=15000):
        import requests

        try:
            ua = self._contexto.driver.execute_script("return navigator.userAgent")
            frasco = {c["name"]: c["value"] for c in self._contexto.cookies()}
            r = requests.get(url, cookies=frasco, headers={"User-Agent": ua},
                             timeout=timeout / 1000, allow_redirects=False)
        except Exception as exc:  # Firefox cerrado o sin red: para quien llama, «aún no»
            raise ErrorFirefox(str(exc)) from exc
        return _Respuesta(r.status_code)


class _Pestana:
    def __init__(self, driver):
        self.driver = driver

    def evaluate(self, js):
        try:
            return self.driver.execute_script(f"return {js}")
        except Exception as exc:
            raise ErrorFirefox(str(exc)) from exc

    def goto(self, url, wait_until=None, timeout=60000):
        from selenium.common.exceptions import TimeoutException

        try:
            self.driver.set_page_load_timeout(timeout / 1000)
            self.driver.get(url)
        except TimeoutException:
            pass  # la página sigue cargando (SSO): se sigue preguntando a la API
        except Exception as exc:
            raise ErrorFirefox(str(exc)) from exc

    def wait_for_timeout(self, ms):
        try:
            self.driver.current_url  # si cerraste la ventana, esto falla
        except Exception as exc:
            raise ErrorFirefox("cerraste el navegador") from exc
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
            raise ErrorFirefox(str(exc)) from exc

    def new_page(self):
        return self.pages[0]

    def close(self):
        try:
            self.driver.quit()
        except Exception:
            pass


def abrir(perfil, headless):
    """Abre tu Firefox con el perfil de Pandex. Lanza ``ErrorFirefox`` si no puede."""
    binario = instalado()
    if binario is None:
        raise ErrorFirefox(f"No encontré Firefox. Instálalo con: {INSTALAR}")
    try:
        from selenium import webdriver
    except ImportError as exc:
        raise ErrorFirefox("Falta Selenium: ejecuta ./instalar.sh de nuevo.") from exc

    perfil = perfil_para(perfil, binario)
    perfil.mkdir(parents=True, exist_ok=True)
    opciones = webdriver.FirefoxOptions()
    opciones.binary_location = binario
    opciones.page_load_strategy = "eager"  # como «domcontentloaded»: no esperar imágenes
    opciones.add_argument("-profile")
    opciones.add_argument(str(perfil))
    if headless:
        opciones.add_argument("-headless")
    geckodriver = shutil.which("geckodriver") or ("/snap/bin/geckodriver" if _es_snap(binario) else None)
    servicio = webdriver.FirefoxService(executable_path=geckodriver) if geckodriver else webdriver.FirefoxService()
    try:
        driver = webdriver.Firefox(options=opciones, service=servicio)
    except Exception as exc:
        log.error("Firefox no abrió: %s", exc)
        raise ErrorFirefox(f"No pude abrir Firefox: {str(exc).splitlines()[0] if str(exc) else exc}") from exc
    try:
        driver.set_window_size(1366, 900)
    except Exception:
        pass
    return Contexto(driver)
