"""Lo que cambia en Linux: accesos .desktop, Firefox para Canvas y el OCR con Tesseract.

También el par en Windows de «un solo Pandex por PC», con PowerShell simulado.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pandex import accesos, despertador
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
                       mock.patch.object(despertador, "WINDOWS", False),
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

    def _dos_copias(self):
        """Una copia vieja (con tu configuración) y una nueva recién descargada."""
        vieja, nueva = self.tmp / "Descargas" / "pandex", self.tmp / "Documentos" / "pandex"
        for carpeta in (vieja, nueva):
            carpeta.mkdir(parents=True)
            (carpeta / "main.py").write_text("", encoding="utf-8")
        (vieja / "config.json").write_text('{"mis": "cursos"}', encoding="utf-8")
        return vieja, nueva

    def test_instalar_otra_copia_no_deja_pandex_dos_veces(self):
        vieja, nueva = self._dos_copias()
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

    def test_instalar_otra_copia_mueve_tambien_el_despertador(self):
        """PLA-11: el despertador del modo «a la hora» abre la copia nueva y sus horarios no cambian."""
        vieja, nueva = self._dos_copias()
        instalacion = self.tmp / "pandex" / "instalacion.json"
        unidades = self.tmp / "config" / "systemd" / "user"
        with mock.patch.object(accesos, "INSTALACION", instalacion), mock.patch.object(accesos, "RAIZ", vieja), \
                mock.patch.object(despertador, "RAIZ", vieja):
            accesos.instalar_aqui(vieja, vieja / "config.json")
            self.assertFalse((unidades / "pandex.service").exists(), "sin despertador no se crea uno")
            servicio, temporizador = despertador.unidades({"sync_canvas": "0 19 * * 1-5"})
            unidades.mkdir(parents=True)
            (unidades / "pandex.service").write_text(servicio, encoding="utf-8")
            (unidades / "pandex.timer").write_text(temporizador, encoding="utf-8")
        with mock.patch.object(accesos, "INSTALACION", instalacion), mock.patch.object(accesos, "RAIZ", nueva), \
                mock.patch.object(despertador, "RAIZ", nueva), \
                mock.patch.object(despertador, "_systemctl") as systemctl:
            accesos.instalar_aqui(nueva, nueva / "config.json")
        servicio = (unidades / "pandex.service").read_text(encoding="utf-8")
        self.assertIn(str(nueva), servicio)
        self.assertNotIn(str(vieja), servicio)
        self.assertEqual((unidades / "pandex.timer").read_text(encoding="utf-8"), temporizador)
        systemctl.assert_any_call("daemon-reload")

    def test_reconoce_una_copia_instalada_antes_de_anotar_la_carpeta(self):
        """PLA-12: sin ``instalacion.json`` (instalada con 2.4.0) se reconoce por el lanzador del menú."""
        vieja, nueva = self._dos_copias()
        instalacion = self.tmp / "pandex" / "instalacion.json"
        with mock.patch.object(accesos, "INSTALACION", instalacion), mock.patch.object(accesos, "RAIZ", vieja):
            accesos.crear_en_escritorio()  # lo que dejaba el instalador de 2.4.0
            self.assertIsNone(accesos.instalacion_anterior(vieja), "reinstalar en la misma carpeta")
        with mock.patch.object(accesos, "INSTALACION", instalacion), mock.patch.object(accesos, "RAIZ", nueva):
            self.assertEqual(accesos.instalar_aqui(nueva, nueva / "config.json"), vieja)
        self.assertEqual((nueva / "config.json").read_text(encoding="utf-8"), '{"mis": "cursos"}')

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


class UnaSolaCopiaEnWindows(unittest.TestCase):
    """PLA-11 y PLA-12 en Windows. PowerShell es simulado: lo que haría de verdad se prueba a mano."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.vieja, self.nueva = self.tmp / "Descargas" / "pandex", self.tmp / "Documentos" / "pandex"
        for carpeta in (self.vieja, self.nueva):
            carpeta.mkdir(parents=True)
            (carpeta / "main.py").write_text("", encoding="utf-8")
        (self.vieja / "config.json").write_text('{"mis": "cursos"}', encoding="utf-8")
        self.scripts = []
        for parche in (mock.patch.dict(os.environ, {"APPDATA": str(self.tmp / "AppData")}),
                       mock.patch.object(accesos, "WINDOWS", True),
                       mock.patch.object(despertador, "WINDOWS", True),
                       mock.patch.object(accesos, "DATOS", self.tmp / "datos"),
                       mock.patch.object(accesos, "INSTALACION", self.tmp / "datos" / "instalacion.json"),
                       mock.patch.object(accesos, "RAIZ", self.nueva),
                       mock.patch.object(despertador, "RAIZ", self.nueva),
                       mock.patch("subprocess.run", side_effect=self._powershell)):
            parche.start()
            self.addCleanup(parche.stop)

    def _powershell(self, args, **kwargs):
        script = args[-1]
        self.scripts.append(script)
        if "ScheduledTask" in script:
            salida = ""
        elif "Save()" in script:  # crear un acceso: devuelve dónde quedó
            salida = str(self.tmp / "Escritorio" / "Pandex.lnk")
        else:  # leer el acceso del Escritorio que dejó la copia anterior
            salida = str(self.vieja)
        return subprocess.CompletedProcess(args, 0, stdout=salida + "\n", stderr="")

    def test_reconoce_una_copia_instalada_antes_de_anotar_la_carpeta(self):
        """PLA-12: sin ``instalacion.json``, por el ``WorkingDirectory`` del acceso del Escritorio."""
        self.assertEqual(accesos.instalar_aqui(self.nueva, self.nueva / "config.json"), self.vieja)
        self.assertEqual((self.nueva / "config.json").read_text(encoding="utf-8"), '{"mis": "cursos"}')

    def test_acceso_arranque_y_despertador_abren_la_copia_nueva(self):
        """PLA-11: el arranque y la tarea «Pandex» pasan a la copia nueva; los horarios no se tocan."""
        accesos.carpeta_inicio().mkdir(parents=True)
        (accesos.carpeta_inicio() / "Pandex.lnk").write_bytes(b"")  # tenía el arranque activado
        accesos.instalar_aqui(self.nueva, self.nueva / "config.json")
        crear = [s for s in self.scripts if "Save()" in s]
        self.assertTrue(any("Startup" in s for s in crear), "el arranque se rehace")
        self.assertTrue(all(str(self.nueva / "main.py") in s for s in crear))
        despertar = [s for s in self.scripts if "ScheduledTask" in s]
        self.assertEqual(len(despertar), 1)
        self.assertIn("if (Get-ScheduledTask -TaskName 'Pandex'", despertar[0], "solo si ya estaba")
        self.assertIn("Set-ScheduledTask -TaskName 'Pandex' -Action $a", despertar[0])
        self.assertNotIn("Trigger", despertar[0], "los horarios quedan como estaban")
        self.assertIn(str(self.nueva / "main.py"), despertar[0])
        self.assertNotIn(str(self.vieja), despertar[0])


class NavegadorDeCanvas(unittest.TestCase):
    def test_auto_es_firefox_en_linux_y_chrome_en_windows(self):
        with mock.patch.object(sesion.sys, "platform", "linux"):
            self.assertEqual(sesion.elegir_navegador("auto"), "firefox")
        with mock.patch.object(sesion.sys, "platform", "win32"):
            self.assertEqual(sesion.elegir_navegador("auto"), "chrome")

    def test_se_puede_forzar(self):
        self.assertEqual(sesion.elegir_navegador("firefox"), "firefox")
        self.assertEqual(sesion.elegir_navegador("chrome"), "chrome")

    def test_firefox_usa_tu_firefox_con_el_perfil_de_pandex(self):
        from pandex.canvas import firefox

        webdriver = mock.MagicMock()
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(firefox, "instalado", return_value="/usr/bin/firefox"), \
                mock.patch.object(firefox, "_es_snap", return_value=False), \
                mock.patch.dict("sys.modules", {"selenium": mock.MagicMock(webdriver=webdriver),
                                                "selenium.webdriver": webdriver}):
            contexto = firefox.abrir(Path(tmp) / "perfil", headless=True)
            opciones = webdriver.FirefoxOptions.return_value
            argumentos = [c.args[0] for c in opciones.add_argument.call_args_list]
            self.assertEqual(opciones.binary_location, "/usr/bin/firefox")
            self.assertIn("-headless", argumentos)
            self.assertEqual(argumentos[argumentos.index("-profile") + 1], str(Path(tmp) / "perfil"))
            self.assertTrue((Path(tmp) / "perfil").is_dir())
        webdriver.Firefox.assert_called_once()
        self.assertIs(contexto.driver, webdriver.Firefox.return_value)

    def test_sin_firefox_dice_como_instalarlo(self):
        from pandex.canvas import firefox

        with mock.patch.object(firefox, "instalado", return_value=None), \
                self.assertRaises(firefox.ErrorFirefox) as error:
            firefox.abrir(Path("/tmp/no-importa"), headless=True)
        self.assertIn("apt install firefox", str(error.exception))
        self.assertIn("apt install firefox", sesion.mensaje_de_error(error.exception))

    def test_el_snap_de_firefox_guarda_el_perfil_donde_puede_entrar(self):
        from pandex.canvas import firefox

        with mock.patch.object(firefox, "_es_snap", return_value=True):
            perfil = firefox.perfil_para(Path("/x/perfil"), "/snap/bin/firefox")
        self.assertEqual(perfil.parts[-4:], ("snap", "firefox", "common", "pandex-perfil"))

    def test_iniciar_sesion_con_firefox_no_carga_playwright(self):
        from pandex.canvas import firefox

        class Contexto:
            pages = [mock.Mock(evaluate=mock.Mock(return_value="Mozilla/5.0 Firefox"))]
            request = mock.Mock(get=mock.Mock(return_value=mock.Mock(status=200)))
            cerrado = False

            def cookies(self):
                return [{"name": "canvas_session", "value": "x"}]

            def close(self):
                Contexto.cerrado = True

        ctx = mock.Mock()
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(sesion, "PERFIL_FIREFOX", Path(tmp)), \
                mock.patch.object(firefox, "_es_snap", return_value=False), \
                mock.patch.object(firefox, "abrir", return_value=Contexto()) as abrir, \
                mock.patch.object(sesion, "_cargar", side_effect=AssertionError("cargó Playwright")):
            cookies, ua = sesion.iniciar_sesion(ctx, "https://canvas.ejemplo.edu", navegador="firefox")
        self.assertEqual(cookies[0]["name"], "canvas_session")
        self.assertIn("Firefox", ua)
        self.assertTrue(Contexto.cerrado)
        abrir.assert_called_once()
        self.assertFalse(abrir.call_args.args[1], "sin sesión guardada: abre con ventana")


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
