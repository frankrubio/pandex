"""Menú para estudiantes (spec 005, IU-18, IU-19 e IU-20)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pandex.config import Config  # noqa: E402
from pandex.rutas import RAIZ  # noqa: E402
from pandex.tareas import descubrir  # noqa: E402


class _Tarea:
    def __init__(self, id_, nombre, **extra):
        self.id, self.nombre, self.descripcion, self.icono, self.schedule = id_, nombre, "", "tarea", None
        for clave, valor in extra.items():
            setattr(self, clave, valor)

    def run(self, ctx):
        raise ValueError("list index out of range")


class Menu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.qapp = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pandex-menu-"))

    def _app(self, programador=False):
        app = mock.MagicMock()
        app._nueva, app._dialogos = None, []
        app.ejecutor.ocupado = False
        app.tareas = descubrir()
        app.config = Config(self.tmp / "config.json", copia=None)
        if programador:
            app.config.datos["modo_programador"] = True
        return app

    def _textos(self, app):
        from pandex.app import PandexApp

        menu = PandexApp._construir_menu(app, None)
        return [a.text() for a in menu.actions() if a.text()]

    def test_canvas_va_primero(self):
        """IU-18: la función principal es la primera tarea del menú."""
        textos = self._textos(self._app())
        self.assertEqual(textos[textos.index("TAREAS") + 1], "Sincronizar Canvas")

    def test_orden_por_atributo(self):
        """IU-18: ``orden`` menor va antes; sin él, 100, y el resto por nombre de archivo."""
        carpeta = self.tmp / "tasks"
        carpeta.mkdir()
        for archivo, extra in (("a.py", ""), ("b.py", "    orden = 5\n"), ("c.py", "    orden = 'x'\n")):
            (carpeta / archivo).write_text(
                f"class Task:\n    id = '{archivo[0]}'\n{extra}    def run(self, ctx):\n        return {{}}\n",
                encoding="utf-8")
        self.assertEqual([t.id for t in descubrir(carpeta)], ["b", "a", "c"])

    def test_lo_de_programadores_se_oculta(self):
        """IU-19: «Saludar» y «Recargar tareas» no están en el menú normal."""
        textos = self._textos(self._app())
        self.assertNotIn("Saludar", textos)
        self.assertNotIn("Recargar tareas", textos)
        self.assertIn("Ver registro", textos)

    def test_modo_programador_lo_muestra(self):
        textos = self._textos(self._app(programador=True))
        self.assertIn("Saludar", textos)
        self.assertIn("Recargar tareas", textos)

    def test_la_casilla_de_programador_guarda(self):
        """IU-10/IU-19: la opción está en Configuración → Comportamiento y se guarda."""
        from pandex.ui.configuracion import DialogoConfiguracion

        config = Config(self.tmp / "config.json", copia=None)
        tareas = descubrir()
        dlg = DialogoConfiguracion(config, tareas)
        self.assertFalse(dlg.programador.isChecked())
        self.assertNotIn("ejemplo_saludo", dlg.filas)  # tampoco en la página «Tareas»
        dlg.programador.setChecked(True)
        with mock.patch("pandex.ui.configuracion.accesos.arranca_con_el_sistema", return_value=False):
            dlg._guardar()
        self.assertTrue(json.loads((self.tmp / "config.json").read_text(encoding="utf-8"))["modo_programador"])
        dlg.deleteLater()

    def test_error_inesperado_dice_que_hacer(self):
        """IU-20: nada de «Error: list index out of range» en el globo; el detalle va al registro."""
        from pandex.ejecutor import _Hilo

        hilo = _Hilo(_Tarea("x", "Mi tarea"), Config(self.tmp / "config.json", copia=None))
        resultados = []
        hilo.terminada.connect(lambda _id, r: resultados.append(r))
        with self.assertLogs("pandex.ejecutor", level="ERROR") as registro:
            hilo.run()
        resumen = resultados[0]["resumen"]
        self.assertEqual(resumen, "No pude terminar «Mi tarea». Vuelve a intentar; si se repite, "
                                  "mira «Ver registro».")
        self.assertNotIn("Error", resumen)
        self.assertIn("list index out of range", "\n".join(registro.output))

    def test_el_hijo_de_markdown_tampoco_dice_error_en_ingles(self):
        """IU-20: el proceso aparte de «Convertir a Markdown» usa el mismo mensaje."""
        entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        codigo = ("import sys, pandex.markdown.lote as lote\n"
                  "def roto(ctx): raise KeyError('boom')\n"
                  "lote.convertir = roto\n"
                  "from pandex.markdown import proceso\n"
                  "sys.exit(proceso._main())\n")
        salida = subprocess.run([sys.executable, "-c", codigo], cwd=str(RAIZ), env=entorno, input="{}",
                                capture_output=True, text=True, encoding="utf-8", timeout=60).stdout
        from pandex.markdown.proceso import MARCA

        linea = next(x for x in salida.split("\n") if x.startswith(MARCA))  # \x1e corta splitlines()
        resultado = json.loads(linea[len(MARCA):])["resultado"]
        self.assertFalse(resultado["ok"])
        self.assertTrue(resultado["resumen"].startswith("No pude terminar la conversión."))
        self.assertIn("Ver registro", resultado["resumen"])
        self.assertIn("KeyError", "\n".join(resultado["detalle"]))


if __name__ == "__main__":
    unittest.main()
