"""Canvas con tu navegador (ADR-0001, D1): Firefox, Chrome o Edge, en Windows y en Linux.

Requisito PES-07: nunca se descarga un navegador; el driver va a DATOS/navegadores (RES-03).
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pandex.canvas import navegador, sesion


def instalados(*nombres):
    return mock.patch.object(navegador, "ruta", lambda n: f"/usr/bin/{n}" if n in nombres else None)


class Elegir(unittest.TestCase):
    def test_tu_predeterminado_primero(self):
        with instalados("firefox", "chrome", "edge"), \
                mock.patch.object(navegador, "predeterminado", return_value="chrome"):
            self.assertEqual(navegador.elegir("auto"), "chrome")

    def test_sin_predeterminado_usa_el_orden_del_sistema(self):
        with instalados("firefox", "edge"), mock.patch.object(navegador, "predeterminado", return_value=None):
            with mock.patch.object(navegador, "ORDEN", ("edge", "chrome", "firefox")):  # Windows
                self.assertEqual(navegador.elegir("auto"), "edge")
            with mock.patch.object(navegador, "ORDEN", ("firefox", "chrome", "edge")):  # Linux
                self.assertEqual(navegador.elegir("auto"), "firefox")

    def test_predeterminado_no_instalado_no_cuenta(self):
        with instalados("edge"), mock.patch.object(navegador, "predeterminado", return_value="firefox"):
            self.assertEqual(navegador.elegir("auto"), "edge")

    def test_el_que_eliges_manda(self):
        with instalados("firefox", "edge"), mock.patch.object(navegador, "predeterminado", return_value="firefox"):
            self.assertEqual(navegador.elegir("edge"), "edge")
            self.assertEqual(sesion.elegir_navegador("edge"), "edge")

    def test_elegido_que_no_esta_dice_que_hacer(self):
        with instalados("firefox"), self.assertRaises(navegador.ErrorNavegador) as error:
            navegador.elegir("chrome")
        self.assertIn("elige otro navegador", str(error.exception))
        self.assertEqual(sesion.mensaje_de_error(error.exception), str(error.exception))

    def test_ninguno(self):
        with instalados(), mock.patch.object(navegador, "predeterminado", return_value=None), \
                self.assertRaises(navegador.ErrorNavegador) as error:
            navegador.elegir("auto")
        self.assertIn("No encontré Firefox, Chrome ni Edge", str(error.exception))

    def test_lee_el_predeterminado_de_linux(self):
        for salida, esperado in (("firefox_firefox.desktop\n", "firefox"), ("google-chrome.desktop", "chrome"),
                                 ("microsoft-edge.desktop", "edge"), ("brave-browser.desktop", None)):
            with mock.patch.object(navegador, "WINDOWS", False), \
                    mock.patch.object(navegador.subprocess, "run", return_value=mock.Mock(stdout=salida)):
                self.assertEqual(navegador.predeterminado(), esperado, salida)


class Abrir(unittest.TestCase):
    def abrir(self, nombre, headless=True, propio=None):
        webdriver = mock.MagicMock()
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        with instalados(nombre), \
                mock.patch.object(navegador, "PERFILES", {n: tmp / n for n in navegador.TODOS}), \
                mock.patch.object(navegador, "NAVEGADORES", tmp / "navegadores"), \
                mock.patch.object(navegador, "_snap", return_value=None), \
                mock.patch.object(navegador, "_driver_del_sistema", return_value=propio), \
                mock.patch.dict("sys.modules", {"selenium": mock.MagicMock(webdriver=webdriver),
                                                "selenium.webdriver": webdriver}), \
                mock.patch.dict(os.environ):
            contexto = navegador.abrir(nombre, headless)
            cache = os.environ.get("SE_CACHE_PATH")
            self.estadisticas = os.environ.get("SE_AVOID_STATS")
        return webdriver, contexto, tmp, cache

    def test_firefox_con_el_perfil_de_pandex(self):
        webdriver, contexto, tmp, _ = self.abrir("firefox")
        opciones = webdriver.FirefoxOptions.return_value
        argumentos = [c.args[0] for c in opciones.add_argument.call_args_list]
        self.assertEqual(opciones.binary_location, "/usr/bin/firefox")
        self.assertIn("-headless", argumentos)
        self.assertEqual(argumentos[argumentos.index("-profile") + 1], str(tmp / "firefox"))
        self.assertIs(contexto.driver, webdriver.Firefox.return_value)

    def test_edge_y_chrome_con_su_perfil(self):
        for nombre, clase, opciones in (("edge", "Edge", "EdgeOptions"), ("chrome", "Chrome", "ChromeOptions")):
            webdriver, contexto, tmp, _ = self.abrir(nombre, headless=False)
            argumentos = [c.args[0] for c in getattr(webdriver, opciones).return_value.add_argument.call_args_list]
            self.assertIn(f"--user-data-dir={tmp / nombre}", argumentos)
            self.assertNotIn("--headless=new", argumentos)
            self.assertIs(contexto.driver, getattr(webdriver, clase).return_value)

    def test_selenium_no_manda_estadisticas(self):
        self.abrir("chrome")
        self.assertEqual(self.estadisticas, "true")

    def test_el_driver_va_a_la_carpeta_de_datos(self):
        _, _, tmp, cache = self.abrir("edge")
        self.assertEqual(cache, str(tmp / "navegadores"))
        self.assertTrue((tmp / "navegadores").is_dir())

    def test_usa_el_driver_del_sistema_si_hay(self):
        webdriver, *_ = self.abrir("firefox", propio="/snap/bin/geckodriver")
        webdriver.FirefoxService.assert_called_once_with(executable_path="/snap/bin/geckodriver")

    def test_sin_el_navegador_dice_que_hacer(self):
        with instalados(), self.assertRaises(navegador.ErrorNavegador) as error:
            navegador.abrir("firefox", True)
        self.assertIn("No encontré Firefox", str(error.exception))

    def test_el_snap_guarda_el_perfil_donde_puede_entrar(self):
        with mock.patch.object(navegador, "WINDOWS", False), \
                mock.patch.object(navegador, "_snap", return_value="firefox"):
            perfil = navegador.perfil("firefox", "/snap/bin/firefox")
        self.assertEqual(perfil.parts[-4:], ("snap", "firefox", "common", "pandex-perfil"))

    def test_chrome_reutiliza_el_perfil_que_creo_playwright(self):
        self.assertEqual(navegador.PERFILES["chrome"].name, "browser-profile")


class Pedidos(unittest.TestCase):
    """P1: a Canvas solo van las cookies de Canvas, nunca las del login (p. ej. Microsoft)."""

    def test_solo_manda_las_cookies_del_sitio(self):
        driver = mock.Mock()
        driver.execute_script.return_value = "UA"
        driver.get_cookies.return_value = [
            {"name": "canvas_session", "value": "c", "domain": "canvas.utec.edu.pe"},
            {"name": "log_session_id", "value": "x", "domain": ".utec.edu.pe"},
            {"name": "ESTSAUTH", "value": "secreto", "domain": ".login.microsoftonline.com"},
        ]
        requests = mock.Mock()
        requests.get.return_value = mock.Mock(status_code=200)
        with mock.patch.dict("sys.modules", {"requests": requests}):
            r = navegador.Contexto(driver).request.get("https://canvas.utec.edu.pe/api/v1/users/self")
        self.assertEqual(r.status, 200)
        enviadas = requests.get.call_args.kwargs["cookies"]
        self.assertEqual(enviadas, {"canvas_session": "c", "log_session_id": "x"})

    def test_dominio_parecido_no_cuenta(self):
        self.assertFalse(navegador._del_sitio("evilutec.edu.pe", "canvas.utec.edu.pe"))
        self.assertTrue(navegador._del_sitio(".canvas.utec.edu.pe", "canvas.utec.edu.pe"))
        self.assertTrue(navegador._del_sitio(None, "canvas.utec.edu.pe"))  # cookie sin dominio: de la página


class SinPlaywright(unittest.TestCase):
    def test_iniciar_sesion_no_importa_playwright(self):
        import sys

        class Contexto:
            pages = [mock.Mock(evaluate=mock.Mock(return_value="Mozilla/5.0 Firefox"))]
            request = mock.Mock(get=mock.Mock(return_value=mock.Mock(status=200)))

            def cookies(self):
                return [{"name": "canvas_session", "value": "x"}]

            def close(self):
                pass

        with mock.patch.object(navegador, "elegir", return_value="firefox"), \
                mock.patch.object(navegador, "hay_sesion", return_value=False), \
                mock.patch.object(navegador, "abrir", return_value=Contexto()) as abrir, \
                mock.patch.dict("sys.modules", {"playwright": None}):
            cookies, ua = sesion.iniciar_sesion(mock.Mock(), "https://canvas.ejemplo.edu")
        self.assertEqual(cookies[0]["name"], "canvas_session")
        self.assertFalse(abrir.call_args.args[1], "sin sesión guardada: abre con ventana")
        self.assertNotIn("playwright.sync_api", sys.modules)


if __name__ == "__main__":
    unittest.main()
