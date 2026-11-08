"""Canvas con tu navegador (ADR-0001, D1): Firefox, Chrome o Edge, en Windows y en Linux.

Requisito PES-07: nunca se descarga un navegador; el driver va a DATOS/navegadores (RES-03).
"""

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from pandex.canvas import navegador, sesion


def instalados(*nombres):
    return mock.patch.object(navegador, "ruta", lambda n: f"/usr/bin/{n}" if n in nombres else None)


class Elegir(unittest.TestCase):
    def setUp(self):
        # sin navegador recordado ni perfiles de verdad: cada prueba parte de una PC nueva
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)
        for nombre, valor in (("USADO", self.tmp / "navegador_usado"),
                              ("PERFILES", {n: self.tmp / n for n in navegador.TODOS})):
            parche = mock.patch.object(navegador, nombre, valor)
            parche.start()
            self.addCleanup(parche.stop)

    def test_sigue_con_el_que_ya_usabas_aunque_tu_predeterminado_sea_otro(self):
        """Quien entraba con Chrome sigue con Chrome, aunque Edge sea el predeterminado de Windows."""
        navegador.recordar("chrome")
        with instalados("chrome", "edge"), mock.patch.object(navegador, "predeterminado", return_value="edge"):
            self.assertEqual(navegador.elegir("auto"), "chrome")

    def test_el_perfil_de_chrome_de_versiones_anteriores_cuenta_como_ya_usado(self):
        (navegador.PERFILES["chrome"] / "Default").mkdir(parents=True)
        with instalados("chrome", "edge"), mock.patch.object(navegador, "predeterminado", return_value="edge"):
            self.assertEqual(navegador.elegir("auto"), "chrome")

    def test_un_perfil_vacio_de_edge_no_cuenta(self):
        """Un intento fallido con Edge deja su perfil creado: no es una sesión."""
        (navegador.PERFILES["edge"] / "Default").mkdir(parents=True)
        with instalados("chrome", "edge"), mock.patch.object(navegador, "predeterminado", return_value="chrome"):
            self.assertEqual(navegador.elegir("auto"), "chrome")

    def test_el_recordado_que_ya_no_esta_instalado_se_ignora(self):
        navegador.recordar("firefox")
        with instalados("edge"), mock.patch.object(navegador, "predeterminado", return_value="edge"):
            self.assertEqual(navegador.elegir("auto"), "edge")

    def test_lo_que_eliges_pisa_lo_recordado(self):
        navegador.recordar("chrome")
        with instalados("chrome", "edge"):
            self.assertEqual(navegador.elegir("edge"), "edge")

    def test_recordar_ignora_nombres_raros(self):
        navegador.recordar("../x")
        self.assertIsNone(navegador.recordado())
        navegador.recordar("edge")
        self.assertEqual(navegador.recordado(), "edge")

    def test_entrar_con_exito_recuerda_el_navegador(self):
        """Lo guarda ``sesion.iniciar_sesion`` al conseguir la sesión (ver IniciarSesionConVentanaNormal)."""
        self.assertIsNone(navegador.recordado())

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

    def test_sin_driver_lo_dice_y_no_se_toma_como_perfil_viejo(self):
        """Hallazgo 1: si no se pudo descargar el driver, abrir la ventana para iniciar sesión no lo arregla."""
        webdriver = mock.MagicMock()
        webdriver.Edge.side_effect = type("NoSuchDriverException", (Exception,), {})("Unable to obtain driver")
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        with instalados("edge"), \
                mock.patch.object(navegador, "PERFILES", {n: tmp / n for n in navegador.TODOS}), \
                mock.patch.object(navegador, "NAVEGADORES", tmp / "navegadores"), \
                mock.patch.object(navegador, "_snap", return_value=None), \
                mock.patch.object(navegador, "_driver_del_sistema", return_value=None), \
                mock.patch.dict("sys.modules", {"selenium": mock.MagicMock(webdriver=webdriver),
                                                "selenium.webdriver": webdriver}), \
                mock.patch.dict(os.environ), self.assertRaises(navegador.SinInstalar) as error:
            navegador.abrir("edge", True)
        self.assertIn("internet", str(error.exception))
        self.assertEqual(sesion.mensaje_de_error(error.exception), str(error.exception))

    def test_sin_el_navegador_es_algo_por_instalar(self):
        with instalados(), self.assertRaises(navegador.SinInstalar):
            navegador.abrir("firefox", True)

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
        self.addCleanup(setattr, navegador, "USADO", navegador.USADO)
        navegador.USADO = Path(tempfile.mkdtemp()) / "navegador_usado"
        self.addCleanup(__import__("shutil").rmtree, navegador.USADO.parent, True)
        self.addCleanup(setattr, sesion, "ESPERA_SSO", sesion.ESPERA_SSO)
        sesion.ESPERA_SSO = 0.2
        self.addCleanup(setattr, sesion, "ATAJO", sesion.ATAJO)
        sesion.ATAJO = Path(tempfile.mkdtemp()) / "sesion_canvas.json"
        self.addCleanup(__import__("shutil").rmtree, sesion.ATAJO.parent, True)

    def preparar(self, *, cierra_tras, sesion_valida, hay_perfil=False, falla_primero=False,
                 ocupado_al_empezar=False, suelta_tras=0, nombre="edge", queda_ocupado=False,
                 valida_sin_ventana=None, goto_falla=None, procesos=None, suelta_tras_intento=None):
        """Chrome sin sesión guardada: ventana normal (se cierra tras N sondeos) y comprobación sin ventana.

        ``ocupado_al_empezar``: ya había una ventana con el perfil de Pandex. ``suelta_tras``: cuántas
        veces más sigue ocupado el perfil después de abrir la ventana. ``falla_primero``: True o el
        error con que falla el primer ``abrir``. ``procesos``: lo que dice ``procesos_del_perfil``.
        ``suelta_tras_intento``: cuántas consultas sigue ocupado el perfil tras el intento sin ventana."""
        abiertos, ventanas = [], []
        self.perfil = {"consultas": 0, "al_comprobar": None, "intento": False, "carpetas": [],
                       "cerrados": [], "libre_al_abrir": None, "tras_intento": 0}
        valida_sin_ventana = sesion_valida if valida_sin_ventana is None else valida_sin_ventana

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
                if goto_falla is not None:
                    raise goto_falla

            def wait_for_timeout(self, _ms):
                pass

        class Contexto:
            def __init__(self, headless):
                self.headless, self.pages = headless, [Pagina()]
                valida = valida_sin_ventana if headless and not ventanas else sesion_valida
                self.request = type("R", (), {"get": lambda *_a, **_k: type(
                    "Resp", (), {"status": 200 if valida else 401})()})()

            def cookies(self):
                return [{"name": "sesion", "value": "x", "domain": "canvas.ejemplo.edu"}]

            def close(self):
                pass

        pendientes = [falla_primero]

        def abrir(_nombre, headless):
            self.perfil["intento"] = True
            falla = pendientes.pop(0) if pendientes else False
            if isinstance(falla, Exception):
                raise falla
            if falla:
                raise navegador.ErrorNavegador("session not created: el perfil está en uso")
            if not headless:
                self.perfil["libre_al_abrir"] = not en_uso(_nombre, "sin contar")
            if ventanas:
                self.perfil["al_comprobar"] = self.perfil["consultas"]
            abiertos.append(Contexto(headless))
            return abiertos[-1]

        def en_uso(_nombre, _carpeta=None):
            if _carpeta != "sin contar":
                self.perfil["carpetas"].append(_carpeta)
            if self.perfil["cerrados"]:
                return False
            if not ventanas:
                if not self.perfil["intento"]:
                    return ocupado_al_empezar
                if suelta_tras_intento is not None:
                    if _carpeta != "sin contar":
                        self.perfil["tras_intento"] += 1
                    return self.perfil["tras_intento"] <= suelta_tras_intento
                return queda_ocupado
            self.perfil["consultas"] += 1
            return self.perfil["consultas"] <= suelta_tras

        def ventana(nombre, url):
            ventanas.append((nombre, url, Proceso()))
            return ventanas[-1][2]

        for atributo, valor in (("abrir", abrir), ("abrir_ventana_normal", ventana),
                                ("hay_sesion", lambda _n: hay_perfil), ("en_uso", en_uso),
                                ("elegir", lambda preferido="auto": nombre),
                                ("procesos_del_perfil", lambda _n, _c: procesos),
                                ("cerrar_procesos", lambda pids, forzar=False: self.perfil["cerrados"].append(pids))):
            parche = mock.patch.object(navegador, atributo, valor)
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
        self.assertEqual(navegador.recordado(), "edge", "la próxima vez sigue con el que funcionó")

    def test_si_el_intento_sin_ventana_falla_se_sigue_con_la_ventana_normal(self):
        """Un perfil viejo o en uso no debe impedir iniciar sesión: antes salía «No pude abrir el navegador»."""
        _, ventanas = self.preparar(cierra_tras=1, sesion_valida=True, hay_perfil=True, falla_primero=True)
        with mock.patch.object(sesion.time, "sleep"):
            ctx, (cookies, ua) = self.entrar()
        self.assertEqual(len(ventanas), 1)
        self.assertEqual(ua, "UA")

    def test_el_mensaje_generico_manda_al_registro(self):
        texto = sesion.mensaje_de_error(navegador.ErrorNavegador("algo raro de selenium"))
        self.assertIn("Ver registro", texto)

    def test_el_mensaje_generico_es_corto_y_sin_jerga(self):
        """SES-06 e IU-06/IU-07: el globo dice qué pasó y qué hacer; el detalle técnico va al registro."""
        texto = sesion.mensaje_de_error(navegador.ErrorNavegador(
            "Message: unknown error: cannot determine loading status\nStacktrace:\n#0 0x55d4 <unknown>"))
        for jerga in ("cannot", "Stacktrace", "Message:", "Detalle"):
            self.assertNotIn(jerga, texto)
        self.assertNotIn("Cierra las ventanas de tu navegador", texto, "tu navegador no tiene que ver")
        self.assertLessEqual(len(texto), 110)
        self.assertIn("Ver registro", texto)

    def test_espera_a_que_el_navegador_suelte_el_perfil(self):
        """SES-05: el proceso que abrió Pandex puede terminar antes que el navegador (le pasó la
        dirección a una ventana que ya estaba, o se reinició para actualizarse)."""
        abiertos, _ = self.preparar(cierra_tras=0, sesion_valida=True, suelta_tras=3)
        with mock.patch.object(sesion.time, "sleep"):
            self.entrar()
        self.assertEqual(len(abiertos), 1)
        self.assertEqual(self.perfil["al_comprobar"], 4, "comprueba recién cuando el perfil quedó libre")

    def test_si_la_ventana_de_pandex_ya_estaba_abierta_la_usa(self):
        abiertos, ventanas = self.preparar(cierra_tras=0, sesion_valida=True, hay_perfil=True,
                                           ocupado_al_empezar=True, suelta_tras=2)
        with mock.patch.object(sesion.time, "sleep"):
            ctx, (cookies, ua) = self.entrar()
        self.assertEqual(len(ventanas), 1)
        self.assertEqual(len(abiertos), 1, "con el perfil ocupado no hay intento sin ventana")
        self.assertIn("ya estaba abierta", " ".join(ctx.globos))
        self.assertEqual(ua, "UA")

    def test_si_el_intento_sin_ventana_deja_el_perfil_ocupado_avisa(self):
        """Si el navegador sin ventana no suelta el perfil, la ventana nueva le pasaría Canvas a él."""
        _, ventanas = self.preparar(cierra_tras=0, sesion_valida=True, hay_perfil=True, falla_primero=True,
                                    queda_ocupado=True)
        with mock.patch.object(sesion.time, "sleep"):
            ctx, _ = self.entrar()
        self.assertEqual(len(ventanas), 1)
        self.assertIn("ya estaba abierta", " ".join(ctx.globos))

    def test_firefox_con_su_ventana_abierta_lo_dice(self):
        self.preparar(cierra_tras=0, sesion_valida=True, ocupado_al_empezar=True, nombre="firefox")
        with self.assertRaises(sesion.CanvasError) as e:
            self.entrar()
        self.assertIn("Firefox", str(e.exception))
        self.assertIn("Ciérrala", str(e.exception))

    def test_el_intento_sin_ventana_corta_si_la_pagina_se_queda_quieta(self):
        """SES-03: el intento sin ventana y la comprobación usan el corte rápido."""
        self.preparar(cierra_tras=0, sesion_valida=True, hay_perfil=True)
        with mock.patch.object(sesion.time, "sleep"), \
                mock.patch.object(sesion, "_esperar_sesion", wraps=sesion._esperar_sesion) as esperar:
            self.entrar()
        self.assertTrue(esperar.call_args_list)
        for llamada in esperar.call_args_list:
            self.assertEqual(llamada.kwargs.get("quieto"), sesion.QUIETO)

    def test_tras_la_ventana_no_corta_a_los_6_s(self):
        """Hallazgo 4: ya iniciaste sesión; un salto lento del SSO no debe obligarte a entrar otra vez."""
        self.preparar(cierra_tras=0, sesion_valida=True)
        with mock.patch.object(sesion.time, "sleep"), \
                mock.patch.object(sesion, "_esperar_sesion", wraps=sesion._esperar_sesion) as esperar:
            self.entrar()
        self.assertEqual(len(esperar.call_args_list), 1)
        self.assertIsNone(esperar.call_args.kwargs.get("quieto"))

    def test_sin_red_no_abre_la_ventana(self):
        """Hallazgo 1: sin internet, la ventana para iniciar sesión no ayuda: se dice enseguida."""
        _, ventanas = self.preparar(cierra_tras=0, sesion_valida=False, hay_perfil=True,
                                    goto_falla=navegador.SinRed("unknown error: net::ERR_INTERNET_DISCONNECTED"))
        with mock.patch.object(sesion.time, "sleep"), self.assertRaises(navegador.SinRed) as e:
            self.entrar()
        self.assertEqual(ventanas, [])
        self.assertIn("No hay conexión", sesion.mensaje_de_error(e.exception))

    def test_si_falta_algo_por_instalar_no_abre_la_ventana(self):
        _, ventanas = self.preparar(cierra_tras=0, sesion_valida=True, hay_perfil=True,
                                    falla_primero=navegador.SinInstalar("Falta Selenium: ejecuta ./instalar.sh de nuevo."))
        with mock.patch.object(sesion.time, "sleep"), self.assertRaises(navegador.SinInstalar):
            self.entrar()
        self.assertEqual(ventanas, [])

    def test_un_error_sin_texto_no_rompe_nada(self):
        """Hallazgo 8: ``''.splitlines()[0]`` lanzaba IndexError."""
        _, ventanas = self.preparar(cierra_tras=0, sesion_valida=True, hay_perfil=True,
                                    falla_primero=navegador.ErrorNavegador(""))
        with mock.patch.object(sesion.time, "sleep"):
            _, (_, ua) = self.entrar()
        self.assertEqual(len(ventanas), 1)
        self.assertEqual(ua, "UA")

    def test_un_navegador_sin_ventana_que_quedo_abierto_se_cierra(self):
        """Hallazgo 6: Canvas no se le pasa a un navegador que no se ve; Pandex cierra el suyo y sigue."""
        _, ventanas = self.preparar(cierra_tras=0, sesion_valida=True, ocupado_al_empezar=True,
                                    procesos=[(4321, True)])
        with mock.patch.object(sesion.time, "sleep"):
            ctx, _ = self.entrar()
        self.assertEqual(self.perfil["cerrados"], [[4321]])
        self.assertEqual(len(ventanas), 1)
        self.assertNotIn("ya estaba abierta", " ".join(ctx.globos))

    def test_una_ventana_que_se_ve_no_se_cierra(self):
        self.preparar(cierra_tras=0, sesion_valida=True, ocupado_al_empezar=True, suelta_tras=1,
                      procesos=[(4321, False)])
        with mock.patch.object(sesion.time, "sleep"):
            ctx, _ = self.entrar()
        self.assertEqual(self.perfil["cerrados"], [])
        self.assertIn("ya estaba abierta", " ".join(ctx.globos))

    def test_firefox_espera_a_que_el_navegador_sin_ventana_suelte_el_perfil(self):
        """Hallazgo 12: si no espera, la ventana de Firefox falla con «perfil en uso»."""
        self.preparar(cierra_tras=0, sesion_valida=True, valida_sin_ventana=False, hay_perfil=True,
                      nombre="firefox", suelta_tras_intento=3)
        with mock.patch.object(sesion.time, "sleep"):
            self.entrar()
        self.assertTrue(self.perfil["libre_al_abrir"])

    def test_el_perfil_se_busca_una_sola_vez(self):
        """Hallazgo 11: cada consulta del candado recalculaba la carpeta del perfil (PATH y disco)."""
        self.preparar(cierra_tras=2, sesion_valida=True, suelta_tras=2)
        with mock.patch.object(sesion.time, "sleep"):
            self.entrar()
        self.assertTrue(self.perfil["carpetas"])
        self.assertNotIn(None, self.perfil["carpetas"])

    def test_si_otra_tarea_esta_entrando_lo_dice(self):
        """Pandex no cierra el navegador sin ventana de otra tarea suya que está entrando a Canvas."""
        self.preparar(cierra_tras=0, sesion_valida=True, ocupado_al_empezar=True,
                      procesos=[(4321, True)])
        with mock.patch.object(navegador, "abierto_aqui", return_value=True), \
                self.assertRaises(sesion.CanvasError) as e:
            self.entrar()
        self.assertIn("otra tarea", str(e.exception))
        self.assertEqual(self.perfil["cerrados"], [])

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



class HaySesion(unittest.TestCase):
    """SES-02: el intento sin ventana solo con el navegador con el que ya entraste a Canvas."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)
        for nombre, valor in (("USADO", self.tmp / "navegador_usado"),
                              ("PERFILES", {n: self.tmp / n for n in navegador.TODOS}),
                              ("_snap", lambda _b: None)):
            parche = mock.patch.object(navegador, nombre, valor)
            parche.start()
            self.addCleanup(parche.stop)
        parche = instalados(*navegador.TODOS)
        parche.start()
        self.addCleanup(parche.stop)

    def perfil(self, nombre):
        carpeta = navegador.PERFILES[nombre]
        if nombre == "firefox":
            carpeta.mkdir(parents=True)
            (carpeta / "cookies.sqlite").touch()
        else:
            (carpeta / "Default").mkdir(parents=True)

    def test_edge_sin_haber_entrado_nunca_no_cuenta(self):
        """El intento de la 2.5 que Google rechazó dejó el perfil de Edge: no es una sesión."""
        self.perfil("edge")
        self.perfil("chrome")  # el Chrome de las versiones 2.x
        self.assertFalse(navegador.hay_sesion("edge"))
        self.assertTrue(navegador.hay_sesion("chrome"))

    def test_el_anotado_cuenta_y_los_otros_no(self):
        self.perfil("edge")
        self.perfil("chrome")
        navegador.recordar("edge")
        self.assertTrue(navegador.hay_sesion("edge"))
        self.assertFalse(navegador.hay_sesion("chrome"))

    def test_sin_nada_anotado_basta_el_perfil(self):
        """Quien venía de la 2.5 con Firefox no tiene nada anotado."""
        self.perfil("firefox")
        self.assertTrue(navegador.hay_sesion("firefox"))

    def test_sin_perfil_no(self):
        navegador.recordar("edge")
        self.assertFalse(navegador.hay_sesion("edge"))


class EnUso(unittest.TestCase):
    """SES-05: ¿hay un navegador abierto con el perfil de Pandex? Solo se mira su candado."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)

    def test_sin_candado_esta_libre(self):
        for windows in (True, False):
            with mock.patch.object(navegador, "WINDOWS", windows):
                for nombre in navegador.TODOS:
                    self.assertFalse(navegador.en_uso(nombre, self.tmp), (windows, nombre))

    def proceso(self, *argumentos):
        """Un proceso vivo con esos argumentos (como un navegador abierto con un perfil)."""
        hijo = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", *argumentos])
        self.addCleanup(hijo.wait)
        self.addCleanup(hijo.kill)
        for _ in range(200):  # hasta que /proc muestre sus argumentos
            try:
                if argumentos[-1].encode() in Path(f"/proc/{hijo.pid}/cmdline").read_bytes():
                    break
            except OSError:
                pass
            time.sleep(0.01)
        return hijo.pid

    @unittest.skipIf(os.name == "nt", "los candados con enlace son de Linux")
    def test_linux_chromium_con_el_proceso_vivo(self):
        pid = self.proceso(f"--user-data-dir={self.tmp}")
        os.symlink(f"mi-pc-con-guiones-{pid}", self.tmp / "SingletonLock")
        with mock.patch.object(navegador, "WINDOWS", False):
            self.assertTrue(navegador.en_uso("chrome", self.tmp))
            self.assertTrue(navegador.en_uso("edge", self.tmp))

    @unittest.skipIf(os.name == "nt", "los candados con enlace son de Linux")
    def test_linux_un_numero_de_proceso_reusado_no_cuenta(self):
        """Hallazgo 5: tras reiniciar, ese número puede ser otro programa (aquí, esta prueba)."""
        os.symlink(f"mi-pc-{os.getpid()}", self.tmp / "SingletonLock")
        os.symlink(f"127.0.1.1:+{os.getpid()}", self.tmp / "lock")
        with mock.patch.object(navegador, "WINDOWS", False):
            self.assertFalse(navegador.en_uso("chrome", self.tmp))
            self.assertFalse(navegador.en_uso("firefox", self.tmp))

    @unittest.skipIf(os.name == "nt", "los candados con enlace son de Linux")
    def test_linux_otro_perfil_que_empieza_igual_no_cuenta(self):
        pid = self.proceso(f"--user-data-dir={self.tmp}-edge")
        os.symlink(f"mi-pc-{pid}", self.tmp / "SingletonLock")
        with mock.patch.object(navegador, "WINDOWS", False):
            self.assertFalse(navegador.en_uso("chrome", self.tmp))

    @unittest.skipIf(os.name == "nt", "los candados con enlace son de Linux")
    def test_linux_firefox_sin_mas(self):
        """Firefox escribe ``ip:pid`` (sin «+») cuando no puede usar fcntl (p. ej. carpetas en red)."""
        pid = self.proceso("-profile", str(self.tmp))
        os.symlink(f"127.0.1.1:{pid}", self.tmp / "lock")
        with mock.patch.object(navegador, "WINDOWS", False):
            self.assertTrue(navegador.en_uso("firefox", self.tmp))

    @unittest.skipIf(os.name == "nt", "los candados con enlace son de Linux")
    def test_linux_candado_de_un_navegador_que_ya_no_esta(self):
        os.symlink("mi-pc-999999999", self.tmp / "SingletonLock")
        with mock.patch.object(navegador, "WINDOWS", False):
            self.assertFalse(navegador.en_uso("chrome", self.tmp))

    @unittest.skipIf(os.name == "nt", "los candados con enlace son de Linux")
    def test_linux_firefox(self):
        pid = self.proceso("-profile", str(self.tmp))
        os.symlink(f"127.0.1.1:+{pid}", self.tmp / "lock")
        with mock.patch.object(navegador, "WINDOWS", False):
            self.assertTrue(navegador.en_uso("firefox", self.tmp))

    def test_windows_candado_tomado(self):
        (self.tmp / "lockfile").touch()
        (self.tmp / "parent.lock").touch()
        with mock.patch.object(navegador, "WINDOWS", True), \
                mock.patch.object(navegador.os, "open", side_effect=PermissionError(13, "en uso")):
            self.assertTrue(navegador.en_uso("edge", self.tmp))
            self.assertTrue(navegador.en_uso("firefox", self.tmp))

    def test_windows_candado_suelto(self):
        """Un candado que quedó de un navegador que se cerró mal se puede abrir: está libre."""
        (self.tmp / "lockfile").touch()
        with mock.patch.object(navegador, "WINDOWS", True):
            self.assertFalse(navegador.en_uso("chrome", self.tmp))


class ErroresPasajeros(unittest.TestCase):
    """SES-04: mientras Canvas redirige al login de la universidad, Selenium a veces falla un momento.
    Eso no es «cerraste el navegador»."""

    def pestana(self, *urls):
        driver = mock.Mock()
        type(driver).current_url = mock.PropertyMock(side_effect=list(urls))
        return navegador.Contexto(driver).pages[0]

    def test_un_error_pasajero_no_cuenta_como_cerrado(self):
        pestana = self.pestana(Exception("unknown error: cannot determine loading status"),
                               "https://canvas.ejemplo.edu/")
        with mock.patch.object(navegador.time, "sleep"):
            pestana.wait_for_timeout(500)
            pestana.wait_for_timeout(500)
        self.assertEqual(pestana.url, "https://canvas.ejemplo.edu/")

    def test_una_lectura_fallida_olvida_la_direccion(self):
        """Hallazgo 2: si guarda la anterior, los segundos sin poder leer parecen «página quieta»."""
        pestana = self.pestana("https://sso.ejemplo.edu/saml", Exception("unknown error: cannot determine loading status"))
        with mock.patch.object(navegador.time, "sleep"):
            pestana.wait_for_timeout(500)
            pestana.wait_for_timeout(500)
        self.assertIsNone(pestana.url)

    def test_el_user_agent_de_la_pagina_se_reusa(self):
        """Hallazgo 9: se lee antes de navegar y no otra vez en plena redirección."""
        driver = mock.Mock()
        driver.execute_script.return_value = "UA"
        driver.get_cookies.return_value = []
        requests = mock.Mock()
        requests.get.return_value = mock.Mock(status_code=401)
        contexto = navegador.Contexto(driver)
        _, ua = sesion._pagina(contexto)
        with mock.patch.dict("sys.modules", {"requests": requests}):
            contexto.request.get("https://canvas.ejemplo.edu/api/v1/users/self")
        self.assertEqual(ua, "UA")
        self.assertEqual(driver.execute_script.call_count, 1)

    def test_la_ventana_cerrada_si_cuenta(self):
        sin_ventana = type("NoSuchWindowException", (Exception,), {})
        pestana = self.pestana(sin_ventana("no such window: target window already closed"))
        with mock.patch.object(navegador.time, "sleep"), self.assertRaises(navegador.ErrorNavegador):
            pestana.wait_for_timeout(500)

    def test_firefox_cerrado_cuenta(self):
        pestana = self.pestana(Exception("Tried to run command without establishing a connection"))
        with mock.patch.object(navegador.time, "sleep"), self.assertRaises(navegador.ErrorNavegador):
            pestana.wait_for_timeout(500)

    def test_el_driver_caido_cuenta(self):
        pestana = self.pestana(Exception("HTTPConnectionPool(host='localhost', port=1): Max retries exceeded"))
        with mock.patch.object(navegador.time, "sleep"), self.assertRaises(navegador.ErrorNavegador):
            pestana.wait_for_timeout(500)

    def test_diez_fallos_seguidos_cuentan(self):
        pestana = self.pestana(*[Exception("unknown error: algo")] * 10)
        with mock.patch.object(navegador.time, "sleep"):
            for _ in range(9):
                pestana.wait_for_timeout(500)
            with self.assertRaises(navegador.ErrorNavegador):
                pestana.wait_for_timeout(500)

    def test_goto_solo_corta_por_la_red(self):
        driver = mock.Mock()
        pestana = navegador.Contexto(driver).pages[0]
        driver.get.side_effect = Exception("unknown error: net::ERR_ABORTED")
        pestana.goto("https://canvas.ejemplo.edu")  # la redirección siguió: se sigue preguntando
        driver.get.side_effect = Exception("unknown error: net::ERR_NAME_NOT_RESOLVED")
        with self.assertRaises(navegador.SinRed) as e:
            pestana.goto("https://canvas.ejemplo.edu")
        self.assertIn("No hay conexión", sesion.mensaje_de_error(e.exception))

    def test_las_cookies_se_reintentan(self):
        driver = mock.Mock()
        driver.get_cookies.side_effect = [Exception("unknown error: frame detached"),
                                          [{"name": "canvas_session", "value": "c", "domain": "canvas.ejemplo.edu"}]]
        with mock.patch.object(navegador.time, "sleep"):
            cookies = navegador.Contexto(driver).cookies()
        self.assertEqual(cookies[0]["name"], "canvas_session")

    def test_el_user_agent_se_lee_una_sola_vez(self):
        """Pedirlo en cada sondeo, en plena redirección, era lo que más fallaba."""
        driver = mock.Mock()
        driver.execute_script.return_value = "UA"
        driver.get_cookies.return_value = []
        requests = mock.Mock()
        requests.get.return_value = mock.Mock(status_code=401)
        contexto = navegador.Contexto(driver)
        with mock.patch.dict("sys.modules", {"requests": requests}):
            contexto.request.get("https://canvas.ejemplo.edu/api/v1/users/self")
            contexto.request.get("https://canvas.ejemplo.edu/api/v1/users/self")
        self.assertEqual(driver.execute_script.call_count, 1)


class EsperarSesion(unittest.TestCase):
    """SES-03 y SES-06: si la página se queda quieta pidiendo iniciar sesión, no se esperan los 20 s;
    el registro dice dónde se quedó (sitio y ruta, sin parámetros)."""

    class Pagina:
        def __init__(self, urls):
            self.urls, self.url = list(urls), None

        def wait_for_timeout(self, _ms):
            if self.urls:
                self.url = self.urls.pop(0)

    def contexto(self, valida_tras=None):
        self.sondeos = 0

        def get(*_a, **_k):
            self.sondeos += 1
            return mock.Mock(status=200 if valida_tras is not None and self.sondeos > valida_tras else 401)

        return mock.Mock(request=mock.Mock(get=get))

    def reloj(self):
        """Medio segundo por consulta al reloj: las pruebas no esperan de verdad."""
        import itertools

        pasos = itertools.count(0, 0.5)
        return mock.patch.object(sesion.time, "monotonic", lambda: next(pasos))

    def test_quieta_en_el_login_corta_antes(self):
        pagina = self.Pagina(["https://accounts.google.com/v3/signin/identifier?continue=SECRETO"])
        with self.reloj(), self.assertLogs("pandex.sesion", "INFO") as registro:
            dentro = sesion._esperar_sesion(self.contexto(), pagina, "https://canvas.ejemplo.edu", 20, 500,
                                            quieto=6)
        self.assertFalse(dentro)
        self.assertLess(self.sondeos, 10, "no espera los 20 s")
        texto = "\n".join(registro.output)
        self.assertIn("accounts.google.com/v3/signin/identifier", texto)
        self.assertNotIn("SECRETO", texto)

    def test_mientras_redirige_sigue_esperando(self):
        pagina = self.Pagina([f"https://sso.ejemplo.edu/paso{i}" for i in range(100)])
        with self.reloj():
            dentro = sesion._esperar_sesion(self.contexto(valida_tras=15), pagina, "https://canvas.ejemplo.edu",
                                            60, 500, quieto=6)
        self.assertTrue(dentro)

    def test_lecturas_fallidas_no_cuentan_como_quieta(self):
        pagina = self.Pagina(["https://sso.ejemplo.edu/saml"] + [None] * 8 + ["https://sso.ejemplo.edu/saml"] * 50)
        with self.reloj():
            dentro = sesion._esperar_sesion(self.contexto(valida_tras=7), pagina, "https://canvas.ejemplo.edu",
                                            60, 500, quieto=6)
        self.assertTrue(dentro)

    def test_donde_quita_los_parametros_de_la_ruta(self):
        """Hallazgo 3: los IdP de Java ponen la sesión en la ruta (``;jsessionid=``)."""
        donde = sesion._donde("https://idp.uni.edu.pe/idp/profile/SAML2/Redirect/SSO;jsessionid=1A2B3C?execution=e1s1")
        self.assertEqual(donde, "idp.uni.edu.pe/idp/profile/SAML2/Redirect/SSO")

    def test_sin_corte_rapido_espera_todo_y_dice_donde_quedo(self):
        pagina = self.Pagina(["https://canvas.ejemplo.edu/login/canvas?token=SECRETO"])
        with self.reloj(), self.assertLogs("pandex.sesion", "INFO") as registro:
            dentro = sesion._esperar_sesion(self.contexto(), pagina, "https://canvas.ejemplo.edu", 10, 500)
        self.assertFalse(dentro)
        self.assertGreater(self.sondeos, 5)
        texto = "\n".join(registro.output)
        self.assertIn("canvas.ejemplo.edu/login/canvas", texto)
        self.assertNotIn("SECRETO", texto)


class RegistroSinDatos(unittest.TestCase):
    """Hallazgo 10 y P1: lo que va al registro no lleva parámetros de direcciones (códigos del login)."""

    def test_quita_los_parametros_de_toda_direccion(self):
        texto = navegador.limpiar("Reached error page: about:certerror?e=nssFailure2&u=https%3A//canvas.x.edu/"
                                  "login/oauth2/callback%3Fcode%3DSECRETO and https://idp.x.edu/SSO;jsessionid=OTRO")
        self.assertIn("about:certerror", texto)
        self.assertIn("https://idp.x.edu/SSO", texto)
        self.assertNotIn("SECRETO", texto)
        self.assertNotIn("OTRO", texto)

    def test_un_parametro_codificado_tambien(self):
        self.assertNotIn("SECRETO", navegador.limpiar("https://canvas.x.edu/callback%3Fcode%3DSECRETO"))

    def test_los_errores_comunes_quedan_igual(self):
        for texto in ("unknown error: net::ERR_ABORTED", "Message: no such window: target window already closed"):
            self.assertEqual(navegador.limpiar(texto), texto)

    def test_primera_linea_y_registro_van_limpios(self):
        error = Exception("Message: unknown error: net::ERR_ABORTED at https://canvas.x.edu/cb?code=SECRETO\n"
                          "  (Session info: chrome=120)\nStacktrace:\n#0 0x55d4 <unknown>")
        self.assertNotIn("SECRETO", navegador.primera_linea(error))
        registro = navegador.para_registro(error)
        self.assertNotIn("SECRETO", registro)
        self.assertIn("Session info", registro)
        self.assertNotIn("Stacktrace", registro)
        self.assertNotIn("\n", registro)

    def test_goto_no_registra_los_parametros(self):
        driver = mock.Mock()
        driver.get.side_effect = Exception("unknown error: net::ERR_ABORTED at https://canvas.x.edu/cb?code=SECRETO")
        with self.assertLogs("pandex.navegador", "INFO") as registro:
            navegador.Contexto(driver).pages[0].goto("https://canvas.x.edu")
        self.assertNotIn("SECRETO", "\n".join(registro.output))


class ProcesosDelPerfil(unittest.TestCase):
    """Hallazgo 6: ¿qué navegador tiene tomado el perfil de Pandex, y se ve o no?"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)

    @unittest.skipIf(os.name == "nt", "lee /proc")
    def test_linux_solo_el_principal_de_ese_perfil(self):
        crear = EnUso.proceso.__get__(self)
        invisible = crear(f"--user-data-dir={self.tmp}", "--headless=new")
        crear("--type=renderer", f"--user-data-dir={self.tmp}")
        crear(f"--user-data-dir={self.tmp}-edge")
        with mock.patch.object(navegador, "WINDOWS", False):
            self.assertEqual(navegador.procesos_del_perfil("chrome", self.tmp), [(invisible, True)])

    @unittest.skipIf(os.name == "nt", "lee /proc")
    def test_linux_firefox_con_ventana(self):
        visible = EnUso.proceso.__get__(self)("-profile", str(self.tmp))
        with mock.patch.object(navegador, "WINDOWS", False):
            self.assertEqual(navegador.procesos_del_perfil("firefox", self.tmp), [(visible, False)])

    def test_windows_lee_la_lista_de_procesos(self):
        carpeta = r"C:\Users\Ana Pérez\pandex\datos\browser-profile-edge"
        salida = "\n".join([
            f'4321 "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" '
            f'"--user-data-dir={carpeta}" --headless=new --remote-debugging-port=0',
            f'4322 "msedge.exe" --type=renderer "--user-data-dir={carpeta}"',
            f'4400 "msedge.exe" --user-data-dir="{carpeta.upper()}" --no-first-run https://canvas.x.edu',
            f'4500 "msedge.exe" "--user-data-dir={carpeta}-viejo"',
            "4600 ",
        ])
        self.assertEqual(navegador._leer_procesos(salida, "edge", carpeta), [(4321, True), (4400, False)])

    def test_windows_con_la_marca_bom_de_powershell(self):
        carpeta = r"C:\Users\ana\pandex\datos\browser-profile"
        salida = f'\ufeff4321 chrome.exe --user-data-dir={carpeta} --headless=new'.encode("utf-8")
        with mock.patch.object(navegador, "WINDOWS", True), \
                mock.patch.object(navegador.subprocess, "run", return_value=mock.Mock(returncode=0, stdout=salida)):
            self.assertEqual(navegador.procesos_del_perfil("chrome", carpeta), [(4321, True)])

    def test_windows_si_powershell_falla_no_se_sabe(self):
        with mock.patch.object(navegador, "WINDOWS", True), \
                mock.patch.object(navegador.subprocess, "run", side_effect=OSError("no hay powershell")):
            self.assertIsNone(navegador.procesos_del_perfil("edge", self.tmp))

    def test_windows_cierra_con_taskkill_sin_abrir_consola(self):
        with mock.patch.object(navegador, "WINDOWS", True), \
                mock.patch.object(navegador.subprocess, "run") as run:
            navegador.cerrar_procesos([4321])
        comando = run.call_args.args[0]
        self.assertEqual(comando[:3], ["taskkill", "/PID", "4321"])
        self.assertIn("/T", comando)
        self.assertEqual(run.call_args.kwargs.get("creationflags"), getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def test_cuenta_los_navegadores_que_abrio_aqui(self):
        carpeta = self.tmp / "perfil"
        self.assertFalse(navegador.abierto_aqui(carpeta))
        driver = mock.Mock()
        contexto = navegador.Contexto(driver, carpeta)
        self.assertTrue(navegador.abierto_aqui(carpeta))
        contexto.close()
        contexto.close()
        self.assertFalse(navegador.abierto_aqui(carpeta))
