"""Spec 001: sincronizar rápido (REN-02, REN-07, REN-08, REN-09). Sin internet ni navegador."""

import contextlib
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pandex.canvas import navegador, sesion, sincronizar
from tests.apoyo import CanvasFalso, ConCarpetaTemporal, modulo

BASE = "https://canvas.ejemplo.edu"
SECRETO = "VALOR-SECRETO-123"


def cookies():
    return [
        {"name": "canvas_session", "value": SECRETO, "domain": "canvas.ejemplo.edu", "path": "/"},
        {"name": "log_session_id", "value": "x", "domain": ".ejemplo.edu", "path": "/"},
        {"name": "ESTSAUTH", "value": "de-microsoft", "domain": ".login.microsoftonline.com", "path": "/"},
    ]


class Atajo(unittest.TestCase):
    """T001.3: la sesión guardada evita abrir el navegador mientras Canvas la acepte."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(setattr, sesion, "ATAJO", sesion.ATAJO)
        sesion.ATAJO = self.tmp / "sesion_canvas.json"
        sesion.ULTIMO.update(modo=None, espera_manual=0.0)

    def respuesta(self, estado):
        return mock.patch("requests.get", return_value=mock.Mock(status_code=estado))

    def test_solo_guarda_las_cookies_de_canvas(self):
        sesion.guardar_atajo(BASE, cookies(), "UA")
        texto = sesion.ATAJO.read_text(encoding="utf-8")
        self.assertIn("canvas_session", texto)
        self.assertNotIn("microsoftonline", texto)
        self.assertNotIn("de-microsoft", texto)

    @unittest.skipIf(sys.platform == "win32", "los permisos 0600 son de Linux")
    def test_permisos_solo_para_tu_usuario(self):
        sesion.guardar_atajo(BASE, cookies(), "UA")
        self.assertEqual(os.stat(sesion.ATAJO).st_mode & 0o777, 0o600)

    def test_atajo_valido_no_abre_navegador(self):
        sesion.guardar_atajo(BASE, cookies(), "UA")
        with self.respuesta(200), mock.patch.object(sesion, "_abridor", side_effect=AssertionError("abrió")):
            galletas, ua = sesion.iniciar_sesion(mock.Mock(), BASE)
        self.assertEqual(ua, "UA")
        self.assertEqual([c["name"] for c in galletas], ["canvas_session", "log_session_id"])
        self.assertEqual(sesion.ULTIMO["modo"], "atajo")

    def test_atajo_vencido_se_borra(self):
        sesion.guardar_atajo(BASE, cookies(), "UA")
        with self.respuesta(401):
            self.assertIsNone(sesion.intentar_atajo(BASE))
        self.assertFalse(sesion.ATAJO.exists())

    def test_redireccion_al_login_tambien_cuenta_como_vencido(self):
        sesion.guardar_atajo(BASE, cookies(), "UA")
        with self.respuesta(302):
            self.assertIsNone(sesion.intentar_atajo(BASE))
        self.assertFalse(sesion.ATAJO.exists())

    def test_sin_red_no_borra_la_sesion(self):
        import requests

        sesion.guardar_atajo(BASE, cookies(), "UA")
        with mock.patch("requests.get", side_effect=requests.ConnectionError("sin red")):
            self.assertIsNone(sesion.intentar_atajo(BASE))
        self.assertTrue(sesion.ATAJO.exists())

    def test_de_otro_canvas_no_sirve(self):
        sesion.guardar_atajo("https://otro.edu", cookies(), "UA")
        with self.respuesta(200) as get:
            self.assertIsNone(sesion.intentar_atajo(BASE))
        get.assert_not_called()
        self.assertFalse(sesion.ATAJO.exists())

    def test_archivo_roto_se_ignora(self):
        sesion.ATAJO.write_text("{no es json", encoding="utf-8")
        self.assertIsNone(sesion.intentar_atajo(BASE))
        self.assertFalse(sesion.ATAJO.exists())

    def test_olvidar(self):
        sesion.guardar_atajo(BASE, cookies(), "UA")
        sesion.olvidar_atajo()
        sesion.olvidar_atajo()  # dos veces no falla
        self.assertFalse(sesion.ATAJO.exists())

    def test_el_registro_no_ve_el_valor_de_ninguna_cookie(self):
        """REN-09 / P1."""
        with self.assertLogs("pandex", level="DEBUG") as registro, self.respuesta(200):
            sesion.guardar_atajo(BASE, cookies(), "UA")
            sesion.intentar_atajo(BASE)
            with self.respuesta(401):
                sesion.intentar_atajo(BASE)
        self.assertTrue(registro.output)
        self.assertNotIn(SECRETO, "\n".join(registro.output))

    def test_tras_entrar_con_el_navegador_se_guarda_para_la_proxima(self):
        class Pagina:
            def evaluate(self, _js):
                return "UA-nav"

            def goto(self, *_a, **_k):
                pass

            def wait_for_timeout(self, _ms):
                pass

        class Contexto:
            pages = [Pagina()]
            request = type("R", (), {"get": lambda *_a, **_k: type("Resp", (), {"status": 200})()})()

            def cookies(self):
                return cookies()

            def close(self):
                pass

        @contextlib.contextmanager
        def abridor(_nombre, _usar_chrome=True):
            yield (lambda _headless: Contexto()), (navegador.ErrorNavegador,)

        with mock.patch.object(sesion, "_abridor", abridor), mock.patch.object(sesion, "_hay_perfil", lambda _n: True), \
                mock.patch.object(sesion, "elegir_navegador", lambda *_a, **_k: "chrome"), self.respuesta(401):
            sesion.iniciar_sesion(mock.Mock(), BASE)
        self.assertEqual(sesion.ULTIMO["modo"], "navegador")
        datos = sesion.ATAJO.read_text(encoding="utf-8")
        self.assertIn("UA-nav", datos)
        self.assertNotIn("microsoftonline", datos)


class Registro(ConCarpetaTemporal):
    """T001.1: cada fase dice cuánto tardó y cuántos pedidos hizo."""

    def setUp(self):
        super().setUp()
        raiz = self.tmp / "Cursos"
        raiz.mkdir()
        CanvasFalso.reiniciar(
            cursos=[{"id": 1, "name": "Física I (FI101)"}],
            modulos={1: [modulo("Semana 1", ("sub", "Material de clase"), ("file", "Clase 1.pdf", 11))]},
            archivos={11: ("Clase 1.pdf", 5000)},
        )
        self.params = {"canvas_url": BASE, "destino": str(raiz), "estilo_carpetas": "guiones_bajos",
                       "secciones": {"Material de clase": "Material de clase"},
                       "cursos": [{"canvas_id": 1, "carpeta": "Fisica_I", "alias": "Física",
                                   "crear_secciones": True}]}

    def linea(self, resultado, inicio):
        return next(x for x in resultado["detalle"] if x.startswith(inicio))

    def test_registro_con_pedidos(self):
        r, _ = self.sincronizar(self.params)
        pedidos = self.linea(r, "pedidos:")
        for fase in ("módulos", "consultas", "descargas"):
            self.assertRegex(pedidos, rf"{fase} \d+")
        self.assertRegex(self.linea(r, "pedidos:"), r"módulos [1-9]")

    def test_la_segunda_vez_no_pide_nada_conocido(self):
        self.sincronizar(self.params)
        r, _ = self.sincronizar(self.params)
        self.assertRegex(self.linea(r, "pedidos:"), r"consultas 0")
        self.assertRegex(self.linea(r, "pedidos:"), r"descargas 0")

    def test_fase_login_manual_aparte(self):
        def entrar(*_a, **_k):
            sesion.ULTIMO.update(modo="manual", espera_manual=30.0)
            return [], "ua"

        with mock.patch.object(sincronizar.sesion, "iniciar_sesion", entrar):
            r, _ = self.sincronizar(self.params)
        fases = self.linea(r, "fases:")
        self.assertIn("inicio de sesión manual 30.0s", fases)
        self.assertRegex(fases, r"sesión 0\.\d")  # la espera de la persona no cuenta como «sesión»

    def test_el_modo_de_sesion_queda_en_el_registro(self):
        def entrar(*_a, **_k):
            sesion.ULTIMO.update(modo="atajo", espera_manual=0.0)
            return [], "ua"

        with mock.patch.object(sincronizar.sesion, "iniciar_sesion", entrar):
            r, _ = self.sincronizar(self.params)
        self.assertIn("sesión: atajo", self.linea(r, "fases:"))


class Hilos(unittest.TestCase):
    """T001.4: tantos hilos como cursos, entre 6 y 10."""

    def test_hilos_api(self):
        self.assertEqual([sincronizar.hilos_api(n) for n in (0, 3, 6, 9, 10, 25)], [6, 6, 6, 9, 10, 10])


if __name__ == "__main__":
    unittest.main()
