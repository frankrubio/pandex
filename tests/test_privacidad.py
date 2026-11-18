"""Privacidad (spec 004): PRI-03 registro sin secretos, PRI-04 hosts permitidos, PRI-06 permisos,
PRI-07 «Olvidar mi sesión» y PRI-08 claves documentadas."""

import json
import logging
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pandex import log as registro
from pandex import rutas
from pandex.canvas import cliente, sesion
from pandex.config import DEFAULTS
from pandex.rutas import RAIZ

SECRETO = "SECRETO123abc"


class _Respuesta:
    def __init__(self, estado=200, cuerpo=None):
        self.status_code = estado
        self.text = json.dumps(cuerpo or {})
        self.links = {}
        self.headers = {}

    def json(self):
        return json.loads(self.text)


class Registro(unittest.TestCase):
    """PRI-03: el archivo de registro nunca guarda cookies, tokens ni cabeceras de sesión."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pandex-registro-"))
        self.archivo = self.tmp / "pandex.log"
        self.logger = logging.getLogger("pandex.prueba_privacidad")
        self.logger.setLevel(logging.INFO)  # como en la app (las pruebas no configuran «pandex»)
        self.manejador = registro._manejador(self.archivo)
        self.logger.addHandler(self.manejador)

    def tearDown(self):
        self.logger.removeHandler(self.manejador)
        self.manejador.close()

    def _leido(self):
        self.manejador.flush()
        return self.archivo.read_text(encoding="utf-8")

    def test_registro_sin_secretos(self):
        cliente.Canvas("https://canvas.ejemplo.edu", [{"name": "canvas_session", "value": SECRETO,
                                                       "domain": "canvas.ejemplo.edu"}], "ua")
        self.logger.warning("la descarga falló con la cookie %s", SECRETO)
        self.logger.warning("pedido: Authorization: Bearer abc.def-123")
        self.logger.warning("Cookie: canvas_session=otro; _csrf_token=xyz")
        self.logger.warning("GET https://canvas.ejemplo.edu/files/1/download?download_frd=1&verifier=QWERTY99")
        self.logger.error("error inesperado:\n%s", f"Traceback...\nValueError: token {SECRETO} inválido")
        texto = self._leido()
        for secreto in (SECRETO, "abc.def-123", "otro", "xyz", "QWERTY99"):
            self.assertNotIn(secreto, texto)
        self.assertIn("[oculto]", texto)
        self.assertIn("download_frd=1", texto)  # lo que no es secreto se queda

    def test_lo_que_no_es_secreto_queda_igual(self):
        self.logger.info("tarea %s -> %s", "sync_canvas", "3 archivos nuevos · 2 s")
        self.assertIn("tarea sync_canvas -> 3 archivos nuevos · 2 s", self._leido())

    def test_users_self_no_se_registra(self):
        """La respuesta de /users/self (tu nombre, tu correo) no va al registro."""
        atajo = self.tmp / "sesion_canvas.json"
        atajo.write_text(json.dumps({"base": "https://canvas.ejemplo.edu", "ua": "ua",
                                     "cookies": [{"name": "c", "value": SECRETO}]}), encoding="utf-8")
        cuerpo = {"name": "Ana Pérez", "primary_email": "ana@ejemplo.edu"}
        for estado in (200, 401):
            with self.subTest(estado=estado), mock.patch.object(sesion, "ATAJO", atajo), \
                    mock.patch("requests.get", return_value=_Respuesta(estado, cuerpo)), \
                    self.assertLogs("pandex", level="DEBUG") as capturado:
                logging.getLogger("pandex").info("inicio de la prueba")
                sesion.intentar_atajo("https://canvas.ejemplo.edu")
            salida = "\n".join(capturado.output)
            self.assertNotIn("Ana", salida)
            self.assertNotIn("ana@", salida)


class Red(unittest.TestCase):
    """PRI-04: Pandex solo pide a los hosts de la lista."""

    def test_canvas_solo_pide_a_su_host(self):
        from pandex import red

        canvas = cliente.Canvas("https://canvas.ejemplo.edu", [], "ua")
        pedidos = []

        def get(_s, url, **_k):
            pedidos.append(url)
            return _Respuesta(200, [])

        with mock.patch("requests.Session.get", get):
            canvas.api("/courses")
            with self.assertRaises(cliente.CanvasError) as error:
                canvas.api("https://ejemplo.com/api/v1/courses")
        self.assertIsInstance(error.exception.__cause__, red.ErrorRed)
        self.assertEqual(pedidos, ["https://canvas.ejemplo.edu/api/v1/courses"])

    def test_actualizar_solo_pide_a_github(self):
        from pandex import actualizar, red

        with mock.patch("urllib.request.urlopen") as abrir:
            with self.assertRaises(actualizar.ErrorActualizacion) as error:
                actualizar._abrir("https://ejemplo.com/pandex.zip")
            abrir.assert_not_called()
            self.assertIsInstance(error.exception.__cause__, red.ErrorRed)
            actualizar._abrir(actualizar.URL_VERSION)
            abrir.assert_called_once()

    def test_hosts(self):
        from pandex import red

        red.exigir("https://raw.githubusercontent.com/x", red.GITHUB)
        for url in ("https://raw.githubusercontent.com.ejemplo.com/x", "http://raw.githubusercontent.com/x",
                    "https://usuario@ejemplo.com/x", "file:///etc/passwd", "no es una url"):
            with self.subTest(url=url), self.assertRaises(red.ErrorRed):
                red.exigir(url, red.GITHUB)


@unittest.skipIf(rutas.WINDOWS, "los permisos 0600/0700 son de Linux")
class Permisos(unittest.TestCase):
    """PRI-06: en Linux, solo tú puedes leer la sesión y la cuenta de OneDrive."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pandex-permisos-"))
        os.chmod(self.tmp, 0o755)

    def _modo(self, ruta):
        return stat.S_IMODE(os.stat(ruta).st_mode)

    def test_permisos_de_archivos_sensibles(self):
        carpeta = rutas.carpeta_privada(self.tmp / "browser-profile-firefox")
        self.assertEqual(self._modo(carpeta), 0o700)
        archivo = self.tmp / "rclone.conf"
        archivo.write_text("[utec]\ntoken = x\n", encoding="utf-8")
        os.chmod(archivo, 0o644)
        rutas.privado(archivo)
        self.assertEqual(self._modo(archivo), 0o600)
        atajo = self.tmp / "sesion_canvas.json"
        with mock.patch.object(sesion, "ATAJO", atajo):
            sesion.guardar_atajo("https://canvas.ejemplo.edu", [], "ua")
        self.assertEqual(self._modo(atajo), 0o600)

    def test_la_carpeta_de_datos_queda_privada(self):
        with mock.patch.object(rutas, "DATOS", self.tmp):
            rutas.carpeta_privada(self.tmp / "browser-profile")
        self.assertEqual(self._modo(self.tmp), 0o700)

    def test_el_perfil_del_navegador_se_crea_privado(self):
        from pandex.canvas import navegador

        perfil = self.tmp / "browser-profile-firefox"
        with mock.patch.object(navegador, "ruta", return_value="/usr/bin/firefox"), \
                mock.patch.object(navegador, "perfil", return_value=perfil), \
                mock.patch("subprocess.Popen"):
            navegador.abrir_ventana_normal("firefox", "https://canvas.ejemplo.edu")
        self.assertEqual(self._modo(perfil), 0o700)


class OlvidarSesion(unittest.TestCase):
    """PRI-07: borra la sesión del navegador y el atajo; no toca cursos, historial ni config."""

    def test_olvidar_sesion(self):
        from pandex.canvas import navegador

        tmp = Path(tempfile.mkdtemp(prefix="pandex-olvidar-"))
        perfiles = {n: tmp / f"browser-profile-{n}" for n in ("firefox", "chrome", "edge")}
        for carpeta in perfiles.values():
            (carpeta / "Default").mkdir(parents=True)
            (carpeta / "Default" / "Cookies").write_text("x", encoding="utf-8")
        atajo, usado = tmp / "sesion_canvas.json", tmp / "navegador_usado"
        atajo.write_text("{}", encoding="utf-8")
        usado.write_text("firefox", encoding="utf-8")
        historial = tmp / "historial_canvas.json"
        historial.write_text('{"1": "x"}', encoding="utf-8")
        with mock.patch.object(navegador, "PERFILES", perfiles), mock.patch.object(navegador, "USADO", usado), \
                mock.patch.object(navegador, "perfil", side_effect=lambda n, *_a: perfiles[n]), \
                mock.patch.object(sesion, "ATAJO", atajo):
            fallaron = sesion.olvidar()
        self.assertEqual(fallaron, [])
        self.assertFalse(any(c.exists() for c in perfiles.values()))
        self.assertFalse(atajo.exists())
        self.assertFalse(usado.exists())
        self.assertEqual(historial.read_text(encoding="utf-8"), '{"1": "x"}')

    def test_configuracion_tiene_olvidar_mi_sesion(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication, QMessageBox

        from pandex.config import Config
        from pandex.tareas import descubrir
        from pandex.ui.configuracion import DialogoConfiguracion

        self.qapp = QApplication.instance() or QApplication([])  # sin referencia, Python la libera
        tmp = Path(tempfile.mkdtemp(prefix="pandex-olvidar-ui-"))
        dlg = DialogoConfiguracion(Config(tmp / "config.json", copia=None), descubrir())
        with mock.patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No), \
                mock.patch.object(sesion, "olvidar") as olvidar:
            dlg.olvidar_sesion.click()
        olvidar.assert_not_called()  # sin confirmar no borra nada
        with mock.patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes), \
                mock.patch.object(QMessageBox, "information"), \
                mock.patch.object(sesion, "olvidar", return_value=[]) as olvidar:
            dlg.olvidar_sesion.click()
        olvidar.assert_called_once()
        dlg.deleteLater()


class ClavesDocumentadas(unittest.TestCase):
    def test_claves_de_config_documentadas(self):
        """PRI-08: cada clave de config.json aparece en docs/privacidad.md."""
        texto = (RAIZ / "docs" / "privacidad.md").read_text(encoding="utf-8")
        faltan = [c for c in DEFAULTS if f"`{c}`" not in texto]
        self.assertEqual(faltan, [], "agrega estas claves a docs/privacidad.md")


if __name__ == "__main__":
    unittest.main()
