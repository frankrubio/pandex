"""Lo que cambia en Linux: accesos .desktop, Firefox para Canvas y el OCR con Tesseract."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pandex import accesos
from pandex.canvas import sesion
from pandex.markdown import conversion


class AccesosLinux(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        escritorio = self.tmp / "Escritorio"
        escritorio.mkdir()
        entorno = {"XDG_DATA_HOME": str(self.tmp / "datos"), "XDG_CONFIG_HOME": str(self.tmp / "config")}
        for parche in (mock.patch.dict(os.environ, entorno),
                       mock.patch.object(accesos, "WINDOWS", False),
                       mock.patch.object(accesos, "DATOS", self.tmp / "pandex"),
                       mock.patch.object(accesos, "_carpeta_escritorio", return_value=escritorio),
                       mock.patch("subprocess.run")):
            parche.start()
            self.addCleanup(parche.stop)
        self.escritorio = escritorio

    def test_crea_el_acceso_en_el_menu_y_en_el_escritorio(self):
        ruta = accesos.crear_en_escritorio()
        self.assertEqual(ruta, self.escritorio / "pandex.desktop")
        self.assertTrue(os.access(ruta, os.X_OK))
        self.assertTrue((self.tmp / "datos" / "applications" / "pandex.desktop").exists())
        texto = ruta.read_text(encoding="utf-8")
        self.assertIn("[Desktop Entry]", texto)
        self.assertIn("main.py", texto)
        self.assertIn("Icon=", texto)
        self.assertTrue((self.tmp / "pandex" / "iconos").is_dir())  # el .ico pasó a PNG

    def test_arranque_se_activa_y_se_desactiva(self):
        self.assertFalse(accesos.arranca_con_el_sistema())
        accesos.activar_arranque()
        self.assertTrue(accesos.arranca_con_el_sistema())
        self.assertEqual(accesos.ruta_inicio().parent, self.tmp / "config" / "autostart")
        accesos.desactivar_arranque()
        self.assertFalse(accesos.arranca_con_el_sistema())

    def test_cambiar_icono_reescribe_solo_la_linea_icon(self):
        accesos.crear_en_escritorio()
        otro = accesos.ASSETS_DIR / "personajes" / "rusty" / "icono.ico"
        accesos.cambiar_icono(otro)
        texto = (self.escritorio / "pandex.desktop").read_text(encoding="utf-8")
        self.assertEqual(texto.count("Icon="), 1)
        self.assertIn("rusty.png", texto)
        self.assertIn("Exec=", texto)

    def test_ruta_con_espacios_queda_entre_comillas(self):
        with mock.patch.object(accesos, "RAIZ", Path("/home/ana/mi carpeta/pandex")):
            self.assertIn("'/home/ana/mi carpeta/pandex/main.py'", accesos._entrada_desktop(None))


class NavegadorDeCanvas(unittest.TestCase):
    def test_auto_es_firefox_en_linux_y_chrome_en_windows(self):
        with mock.patch.object(sesion.sys, "platform", "linux"):
            self.assertEqual(sesion.elegir_navegador("auto"), "firefox")
        with mock.patch.object(sesion.sys, "platform", "win32"):
            self.assertEqual(sesion.elegir_navegador("auto"), "chrome")

    def test_se_puede_forzar(self):
        self.assertEqual(sesion.elegir_navegador("firefox"), "firefox")
        self.assertEqual(sesion.elegir_navegador("chrome"), "chrome")

    def test_firefox_abre_su_perfil_con_firefox_y_no_con_chromium(self):
        pw = mock.MagicMock()
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(sesion, "PERFIL_FIREFOX", Path(tmp) / "ff"):
            sesion._cargar()
            sesion._abrir_contexto(pw, True, True, "firefox")
        pw.firefox.launch_persistent_context.assert_called_once()
        pw.chromium.launch_persistent_context.assert_not_called()
        self.assertTrue(pw.firefox.launch_persistent_context.call_args.kwargs["user_data_dir"].endswith("ff"))

    def test_firefox_sin_sesion_guardada_no_intenta_entrar_sin_ventana(self):
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            with mock.patch.object(sesion, "PERFIL_FIREFOX", carpeta):
                self.assertFalse(sesion._hay_perfil("firefox"))
                (carpeta / "cookies.sqlite").write_bytes(b"")
                self.assertTrue(sesion._hay_perfil("firefox"))

    def test_mensajes_utiles_si_falta_firefox_o_sus_librerias(self):
        with mock.patch.object(sesion.sys, "platform", "linux"):
            falta = sesion.mensaje_de_error(Exception("Executable doesn't exist at /x/firefox-1/firefox"))
            self.assertIn("playwright install firefox", falta)
            libs = sesion.mensaje_de_error(Exception("Host system is missing dependencies to run browsers"))
            self.assertIn("install-deps", libs)


class OcrConTesseract(unittest.TestCase):
    def test_sin_tesseract_avisa_como_instalarlo(self):
        with mock.patch.object(conversion.shutil, "which", return_value=None):
            ocr = conversion.OcrTesseract()
        self.assertFalse(ocr.disponible)
        self.assertIn("apt install tesseract-ocr", ocr.motivo)

    def test_usa_espanol_e_ingles_si_estan(self):
        listado = mock.Mock(stdout="List of available languages (3):\neng\nspa\nosd\n")
        with mock.patch.object(conversion.shutil, "which", return_value="/usr/bin/tesseract"), \
                mock.patch.object(conversion.subprocess, "run", return_value=listado):
            ocr = conversion.OcrTesseract()
        self.assertTrue(ocr.disponible)
        self.assertEqual(ocr.idioma, "spa+eng")

    def test_sin_esos_idiomas_no_queda_disponible(self):
        listado = mock.Mock(stdout="List of available languages (1):\nosd\n")
        with mock.patch.object(conversion.shutil, "which", return_value="/usr/bin/tesseract"), \
                mock.patch.object(conversion.subprocess, "run", return_value=listado):
            self.assertFalse(conversion.OcrTesseract().disponible)

    def test_crear_ocr_elige_segun_el_sistema(self):
        with mock.patch.object(conversion.sys, "platform", "linux"), \
                mock.patch.object(conversion.shutil, "which", return_value=None):
            self.assertIsInstance(conversion.crear_ocr(), conversion.OcrTesseract)


if __name__ == "__main__":
    unittest.main()
