"""El núcleo: configuración y descubrimiento de tareas (plug-ins)."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from pandex import tareas
from pandex.config import DEFAULTS, Config
from pandex.rutas import TASKS_DIR


class Configuracion(unittest.TestCase):
    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())
        self.ruta = self.carpeta / "config.json"

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def test_se_crea_con_valores_por_defecto(self):
        config = Config(self.ruta)
        self.assertTrue(config.nueva)
        self.assertTrue(self.ruta.exists())
        self.assertEqual(config.mascota["nombre"], "Pandex")

    def test_tus_valores_mandan_y_los_que_faltan_se_completan(self):
        self.ruta.write_text(json.dumps({"mascota": {"nombre": "Pygu"}, "tareas": {"x": {"activa": False}}}),
                             encoding="utf-8")
        config = Config(self.ruta)
        self.assertEqual(config.mascota["nombre"], "Pygu")
        self.assertEqual(config.mascota["tamano"], DEFAULTS["mascota"]["tamano"])
        self.assertFalse(config.tarea("x")["activa"])
        config.mascota["frases_click"].append("nueva")
        self.assertNotIn("nueva", DEFAULTS["mascota"]["frases_click"], "los valores por defecto no se tocan")


class Descubrir(unittest.TestCase):
    def test_las_tareas_del_proyecto(self):
        ids = {t.id for t in tareas.descubrir(TASKS_DIR)}
        self.assertEqual(ids, {"sync_canvas", "convertir_md", "ejemplo_saludo"})

    def test_un_archivo_roto_no_tumba_nada(self):
        carpeta = Path(tempfile.mkdtemp())
        try:
            (carpeta / "buena.py").write_text(
                "class Task:\n    id = 'buena'\n    def run(self, ctx):\n        return 'ok'\n", encoding="utf-8")
            (carpeta / "rota.py").write_text("esto no es python(", encoding="utf-8")
            (carpeta / "sin_task.py").write_text("x = 1\n", encoding="utf-8")
            (carpeta / "_apagada.py").write_text("class Task:\n    id = 'apagada'\n", encoding="utf-8")
            encontradas = tareas.descubrir(carpeta)
        finally:
            shutil.rmtree(carpeta, ignore_errors=True)
        self.assertEqual([t.id for t in encontradas], ["buena"])
        self.assertEqual(encontradas[0].nombre, "buena", "sin nombre, se usa el id")



class Horas(unittest.TestCase):
    def test_formato_de_12_horas(self):
        from datetime import datetime

        from pandex import horas

        self.assertEqual(horas.hora(19, 5), "7:05 p. m.")
        self.assertEqual(horas.hora(0, 30), "12:30 a. m.")
        self.assertEqual(horas.hora(12, 0), "12:00 p. m.")
        self.assertEqual(horas.hora(9, 0), "9:00 a. m.")
        momento = datetime(2026, 10, 9, 20, 17)
        self.assertEqual(horas.fecha_hora(momento), "09/10 8:17 p. m.")
        self.assertEqual(horas.fecha_larga(momento), "viernes 9 de octubre")
        self.assertEqual(horas.saludo(momento), "Buenas noches")
        self.assertEqual(horas.saludo(momento.replace(hour=8)), "Buenos días")

    def test_saludar_es_instantaneo(self):
        import time

        tarea = next(t for t in tareas.descubrir(TASKS_DIR) if t.id == "ejemplo_saludo")
        inicio = time.monotonic()
        resultado = tarea.run(None)
        self.assertLess(time.monotonic() - inicio, 0.1)
        self.assertTrue(resultado["ok"])
        self.assertRegex(resultado["resumen"], r"Son las \d{1,2}:\d{2} [ap]\. m\.")


if __name__ == "__main__":
    unittest.main()
