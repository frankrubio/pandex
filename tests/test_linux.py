"""Lo que cambia en Linux: accesos .desktop, Firefox para Canvas y el OCR con Tesseract."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pandex import accesos
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

    def test_instalar_otra_copia_no_deja_pandex_dos_veces(self):
        vieja, nueva = self.tmp / "Descargas" / "pandex", self.tmp / "Documentos" / "pandex"
        for carpeta in (vieja, nueva):
            carpeta.mkdir(parents=True)
            (carpeta / "main.py").write_text("", encoding="utf-8")
        (vieja / "config.json").write_text('{"mis": "cursos"}', encoding="utf-8")
        with mock.patch.object(accesos, "INSTALACION", self.tmp / "pandex" / "instalacion.json"), \
                mock.patch.object(accesos, "RAIZ", vieja):
            self.assertIsNone(accesos.instalar_aqui(vieja, vieja / "config.json"), "primera vez: nada que avisar")
            accesos.activar_arranque()
            self.assertIsNone(accesos.instalar_aqui(vieja, vieja / "config.json"), "reinstalar en la misma carpeta")
        with mock.patch.object(accesos, "INSTALACION", self.tmp / "pandex" / "instalacion.json"), \
                mock.patch.object(accesos, "RAIZ", nueva):
            self.assertEqual(accesos.instalar_aqui(nueva, nueva / "config.json"), vieja)
            self.assertIsNone(accesos.instalacion_anterior(nueva), "solo se avisa una vez")
        self.assertEqual((nueva / "config.json").read_text(encoding="utf-8"), '{"mis": "cursos"}')
        for acceso in (self.escritorio / "pandex.desktop", accesos.ruta_inicio()):
            texto = acceso.read_text(encoding="utf-8")
            self.assertIn(str(nueva), texto, f"{acceso.name} abre la copia nueva")
            self.assertNotIn(str(vieja), texto)

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
        raiz = Path("/home/ana/mi carpeta/pandex")
        with mock.patch.object(accesos, "RAIZ", raiz):
            self.assertIn(f"'{raiz / 'main.py'}'", accesos._entrada_desktop(None))


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
