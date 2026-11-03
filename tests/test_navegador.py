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


class VentanaNormal(unittest.TestCase):
    """Google rechaza el inicio de sesión si Selenium controla Chrome o Edge («software de pruebas
    automatizadas»): ahí la persona entra en una ventana normal y Pandex solo comprueba después."""

    def test_solo_chrome_y_edge(self):
        self.assertEqual(set(navegador.VENTANA_NORMAL), {"chrome", "edge"})

    def test_la_ventana_normal_no_lleva_ningun_control_remoto(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        with instalados("edge"), mock.patch.object(navegador, "PERFILES", {n: tmp / n for n in navegador.TODOS}), \
                mock.patch.object(navegador, "_snap", return_value=None), \
                mock.patch.object(navegador.subprocess, "Popen") as popen:
            navegador.abrir_ventana_normal("edge", "https://canvas.ejemplo.edu")
        comando = popen.call_args.args[0]
        self.assertEqual(comando[0], "/usr/bin/edge")
        self.assertIn(f"--user-data-dir={tmp / 'edge'}", comando)
        self.assertEqual(comando[-1], "https://canvas.ejemplo.edu")
        self.assertFalse([a for a in comando if "remote-debugging" in a or "automation" in a.lower()])
        self.assertTrue((tmp / "edge").is_dir())

    def test_sin_el_navegador_dice_que_hacer(self):
        with instalados(), self.assertRaises(navegador.ErrorNavegador):
            navegador.abrir_ventana_normal("edge", "https://x")

    def test_chromium_oculta_la_marca_de_automatizacion(self):
        webdriver = mock.MagicMock()
        opciones = navegador._opciones(webdriver, "edge", "/usr/bin/edge", Path("/tmp/p"), True)
        webdriver.EdgeOptions.return_value.add_experimental_option.assert_any_call(
            "excludeSwitches", ["enable-automation"])
        self.assertIs(opciones, webdriver.EdgeOptions.return_value)
        argumentos = [c.args[0] for c in opciones.add_argument.call_args_list]
        self.assertIn("--disable-blink-features=AutomationControlled", argumentos)


class IniciarSesionConVentanaNormal(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, sesion, "ESPERA_SSO", sesion.ESPERA_SSO)
        sesion.ESPERA_SSO = 0.2
        self.addCleanup(setattr, sesion, "ATAJO", sesion.ATAJO)
        sesion.ATAJO = Path(tempfile.mkdtemp()) / "sesion_canvas.json"
        self.addCleanup(__import__("shutil").rmtree, sesion.ATAJO.parent, True)

    def preparar(self, *, cierra_tras, sesion_valida):
        """Chrome sin sesión guardada: ventana normal (se cierra tras N sondeos) y comprobación sin ventana."""
        abiertos, ventanas = [], []

        class Proceso:
            sondeos, terminado = 0, False

            def poll(self):
                self.sondeos += 1
                return 0 if cierra_tras is not None and self.sondeos > cierra_tras else None

            def terminate(self):
                self.terminado = True

        class Pagina:
            def evaluate(self, _js):
                return "UA"

            def goto(self, *_a, **_k):
                pass

            def wait_for_timeout(self, _ms):
                pass

        class Contexto:
            def __init__(self, headless):
                self.headless, self.pages = headless, [Pagina()]
                self.request = type("R", (), {"get": lambda *_a, **_k: type(
                    "Resp", (), {"status": 200 if sesion_valida else 401})()})()

            def cookies(self):
                return [{"name": "sesion", "value": "x", "domain": "canvas.ejemplo.edu"}]

            def close(self):
                pass

        def abrir(_nombre, headless):
            abiertos.append(Contexto(headless))
            return abiertos[-1]

        def ventana(nombre, url):
            ventanas.append((nombre, url, Proceso()))
            return ventanas[-1][2]

        for nombre, valor in (("abrir", abrir), ("abrir_ventana_normal", ventana), ("hay_sesion", lambda _n: False),
                              ("elegir", lambda preferido="auto": "edge")):
            parche = mock.patch.object(navegador, nombre, valor)
            parche.start()
            self.addCleanup(parche.stop)
        return abiertos, ventanas

    def entrar(self, **k):
        ctx = type("Ctx", (), {"globos": [], "log": lambda s, *a: None, "decir": lambda s, t: s.globos.append(t)})()
        return ctx, sesion.iniciar_sesion(ctx, "https://canvas.ejemplo.edu", navegador="edge", **k)

    def test_entra_en_ventana_normal_y_comprueba_sin_ventana(self):
        abiertos, ventanas = self.preparar(cierra_tras=2, sesion_valida=True)
        with mock.patch.object(sesion.time, "sleep"), mock.patch("requests.get", side_effect=AssertionError):
            ctx, (cookies, ua) = self.entrar()
        self.assertEqual(ventanas[0][:2], ("edge", "https://canvas.ejemplo.edu"))
        self.assertEqual([a.headless for a in abiertos], [True], "Selenium nunca abre la ventana del login")
        self.assertEqual(ua, "UA")
        self.assertEqual(sesion.ULTIMO["modo"], "manual")
        self.assertIn("ciérrala", ctx.globos[0])

    def test_si_cierras_sin_haber_entrado_lo_dice(self):
        self.preparar(cierra_tras=1, sesion_valida=False)
        with mock.patch.object(sesion.time, "sleep"), self.assertRaises(sesion.CanvasError) as e:
            self.entrar()
        self.assertIn("No pude confirmar tu sesión", str(e.exception))

    def test_si_no_entras_a_tiempo_cierra_la_ventana(self):
        _, ventanas = self.preparar(cierra_tras=None, sesion_valida=False)
        with mock.patch.object(sesion.time, "sleep"), self.assertRaises(sesion.CanvasError) as e:
            self.entrar(espera_login=0)
        self.assertIn("Se acabó el tiempo", str(e.exception))
        self.assertTrue(ventanas[0][2].terminado)

