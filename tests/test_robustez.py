"""Robustez (spec 011): Pandex no se cae ni se queda colgado."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pandex.config import DEFAULTS, Config  # noqa: E402
from pandex.rutas import RAIZ  # noqa: E402


def _correr(codigo, datos):
    """Corre ``codigo`` en un Python aparte (un error de Qt aborta el proceso entero)."""
    entorno = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "PANDEX_DATOS": str(datos),
               "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, "-c", codigo], cwd=str(RAIZ), env=entorno,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)


class ErroresInesperados(unittest.TestCase):
    """ROB-01: un error que nadie atrapó no cierra Pandex."""

    def setUp(self):
        self.datos = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.datos, ignore_errors=True)

    def test_un_error_en_la_interfaz_no_cierra_pandex(self):
        r = _correr(
            "import sys\n"
            "from PyQt6.QtCore import QTimer\n"
            "from PyQt6.QtWidgets import QApplication\n"
            "from pandex import errores\n"
            "app = QApplication(sys.argv)\n"
            "avisos = []\n"
            "errores.instalar(avisos.append)\n"
            "def falla():\n"
            "    raise RuntimeError('error de prueba en un reloj')\n"
            "QTimer.singleShot(50, falla)\n"
            "QTimer.singleShot(600, lambda: (print('SIGUE VIVO', len(avisos)), app.quit()))\n"
            "sys.exit(app.exec())\n", self.datos)
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        self.assertIn("SIGUE VIVO 1", r.stdout)

    def test_se_anota_con_su_traza_y_se_avisa(self):
        from pandex import errores

        avisos = []
        with mock.patch.object(errores, "_avisar", avisos.append), \
                self.assertLogs("pandex.errores", level="ERROR") as registro:
            try:
                raise ValueError("dato raro")
            except ValueError:
                errores.atender(*sys.exc_info())
        self.assertIn("ValueError: dato raro", "\n".join(registro.output))
        self.assertIn("test_robustez.py", "\n".join(registro.output), "la traza dice dónde fue")
        self.assertEqual(len(avisos), 1)
        self.assertIn("Ver registro", avisos[0])

    def test_un_error_que_se_repite_no_llena_el_registro_ni_de_globos(self):
        from pandex import errores

        avisos = []
        with mock.patch.object(errores, "_avisar", avisos.append), \
                mock.patch.dict(errores._VISTOS, clear=True), \
                mock.patch.object(errores, "_ultimo_aviso", 0.0), \
                self.assertLogs("pandex.errores", level="ERROR") as registro:
            for _ in range(250):
                try:
                    raise KeyError("otra vez")
                except KeyError:
                    errores.atender(*sys.exc_info())
        trazas = [l for l in registro.output if "Traceback" in l]
        self.assertEqual(len(trazas), 1, "la traza completa, solo la primera vez")
        self.assertLessEqual(len(registro.output), 4, "luego, una línea cada 10 y 100 repeticiones")
        self.assertEqual(len(avisos), 1, "un globo cada 30 s como mucho")

    def test_un_error_en_otro_hilo_tambien_se_anota(self):
        from pandex import errores

        previo_hilo, previo = threading.excepthook, sys.excepthook
        avisos = []
        try:
            errores.instalar(avisos.append)
            with mock.patch.dict(errores._VISTOS, clear=True), \
                    self.assertLogs("pandex.errores", level="ERROR") as registro:
                hilo = threading.Thread(target=lambda: 1 / 0)
                hilo.start()
                hilo.join()
            self.assertIn("ZeroDivisionError", "\n".join(registro.output))
        finally:
            threading.excepthook, sys.excepthook = previo_hilo, previo
            errores.instalar.__globals__["_avisar"] = None

    def test_ctrl_c_sigue_cerrando(self):
        from pandex import errores

        with mock.patch.object(sys, "__excepthook__") as original:
            errores.atender(KeyboardInterrupt, KeyboardInterrupt(), None)
        original.assert_called_once()


class ConfiguracionDanada(unittest.TestCase):
    """ROB-02 y ROB-03: un ``config.json`` dañado no impide abrir Pandex."""

    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())
        self.ruta = self.carpeta / "config.json"
        self.datos = self.carpeta / "datos"
        self.copia = self.datos / "config-ultima-buena.json"

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def _abrir(self):
        return Config(self.ruta, copia=self.copia)

    def _buena(self):
        self.ruta.write_text(json.dumps({"mascota": {"nombre": "Pygu"},
                                         "tareas": {"sync_canvas": {"destino": "/cursos"}}}), encoding="utf-8")
        return self._abrir()

    def test_un_archivo_bueno_deja_su_copia(self):
        config = self._buena()
        self.assertIsNone(config.recuperada)
        self.assertEqual(json.loads(self.copia.read_text(encoding="utf-8"))["mascota"]["nombre"], "Pygu")

    def test_danado_se_recupera_de_la_ultima_copia_buena(self):
        self._buena()
        for contenido in ("", '{"mascota": {"nombre": "Pan', "[]", "null", "\x00\x00\x00"):
            with self.subTest(contenido=contenido):
                self.ruta.write_text(contenido, encoding="utf-8")
                config = self._abrir()
                self.assertEqual(config.recuperada, "copia")
                self.assertEqual(config.mascota["nombre"], "Pygu")
                self.assertEqual(config.tarea("sync_canvas")["destino"], "/cursos")
                self.assertEqual(json.loads(self.ruta.read_text(encoding="utf-8"))["mascota"]["nombre"], "Pygu",
                                 "config.json vuelve a ser un archivo bueno")

    def test_danado_y_sin_copia_abre_con_los_valores_de_fabrica(self):
        self.ruta.write_text("{esto no es json", encoding="utf-8")
        config = self._abrir()
        self.assertEqual(config.recuperada, "fabrica")
        self.assertEqual(config.mascota["nombre"], DEFAULTS["mascota"]["nombre"])

    def test_el_danado_se_guarda_aparte_y_quedan_tres(self):
        self._buena()
        for n in range(5):
            self.ruta.write_text(f"dañado {n}", encoding="utf-8")
            with mock.patch("pandex.config._marca", return_value=f"20261110-12000{n}"):
                self._abrir()
        apartados = sorted(self.datos.glob("config-danado-*.json"))
        self.assertEqual(len(apartados), 3)
        self.assertEqual(apartados[-1].read_text(encoding="utf-8"), "dañado 4")

    def test_una_seccion_de_otro_tipo_no_rompe_nada(self):
        self.ruta.write_text(json.dumps({"mascota": 5, "tareas": {"sync_canvas": "x", "otra": {"a": 1}}}),
                             encoding="utf-8")
        config = self._abrir()
        self.assertEqual(config.mascota["nombre"], DEFAULTS["mascota"]["nombre"])
        self.assertEqual(config.tarea("sync_canvas"), {})
        self.assertEqual(config.tarea("otra"), {"a": 1})

    def test_tareas_de_otro_tipo(self):
        self.ruta.write_text(json.dumps({"tareas": []}), encoding="utf-8")
        self.assertEqual(self._abrir().tarea("x"), {})

    def test_guardar_fuerza_la_escritura(self):
        config = self._buena()
        with mock.patch("pandex.config.os.fsync") as fsync:
            config.guardar()
        fsync.assert_called_once()
        self.assertFalse(self.ruta.with_suffix(".json.tmp").exists())

    def test_sin_copia_configurada_tambien_abre(self):
        self.ruta.write_text("", encoding="utf-8")
        config = Config(self.ruta, copia=None)
        self.assertEqual(config.recuperada, "fabrica")


class ArranqueFallido(unittest.TestCase):
    """ROB-04: si no puede arrancar, lo anota y avisa; no muere en silencio."""

    def setUp(self):
        self.datos = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.datos, ignore_errors=True)

    def test_sin_persona_delante_lo_anota_y_sale_con_1(self):
        r = _correr(
            "import sys\n"
            "import main, pandex.app\n"
            "def roto(*a, **k):\n"
            "    raise RuntimeError('no arranco')\n"
            "pandex.app.PandexApp = roto\n"
            "main.avisar_al_que_ya_corre = lambda *a: False\n"
            "sys.argv = ['main.py', '--test']\n"
            "sys.exit(main.main())\n", self.datos)
        self.assertEqual(r.returncode, 1, r.stderr[-600:])

    def test_con_persona_delante_muestra_que_hacer(self):
        import main

        with mock.patch.object(main, "_ventana_de_error") as ventana, \
                self.assertLogs("pandex", level="ERROR") as registro:
            try:
                raise RuntimeError("no arranco")
            except RuntimeError:
                codigo = main.arranque_fallido(silencioso=False)
        self.assertEqual(codigo, 1)
        self.assertIn("RuntimeError: no arranco", "\n".join(registro.output))
        texto = ventana.call_args.args[0]
        self.assertIn("instalar", texto)
        self.assertIn("pandex.log", texto)

    def test_sin_persona_delante_no_abre_ventanas(self):
        import main

        with mock.patch.object(main, "_ventana_de_error") as ventana, self.assertLogs("pandex", level="ERROR"):
            try:
                raise RuntimeError("no arranco")
            except RuntimeError:
                main.arranque_fallido(silencioso=True)
        ventana.assert_not_called()


if __name__ == "__main__":
    unittest.main()
