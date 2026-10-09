"""Actualizar Pandex: versiones, y aplicar un ZIP sin internet ni tocar tus datos."""

import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from pandex import actualizar
from pandex.config import SPRITE_PIXEL, Config


class Versiones(unittest.TestCase):
    def test_comparar(self):
        self.assertTrue(actualizar.es_mas_nueva("2.1.0", "2.0.0"))
        self.assertTrue(actualizar.es_mas_nueva("2.10.0", "2.9.3"))
        self.assertFalse(actualizar.es_mas_nueva("2.0.0", "2.0.0"))
        self.assertFalse(actualizar.es_mas_nueva("1.9", "2.0.0"))

    def test_leer_version_y_novedades(self):
        self.assertEqual(actualizar.leer_version('"""x"""\n\n__version__ = "3.4.5"\n'), "3.4.5")
        self.assertIsNone(actualizar.leer_version("nada"))
        cambios = "# Cambios\n\n## 2.1.0 · hoy\n\n- nuevo\n\n## 2.0.0\n\n- viejo\n"
        self.assertEqual(actualizar.novedades_de(cambios, "2.1.0"), "## 2.1.0 · hoy\n\n- nuevo")


class AplicarZip(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.raiz = self.tmp / "pandex"
        (self.raiz / "pandex").mkdir(parents=True)
        (self.raiz / "tasks").mkdir()
        (self.raiz / "logs").mkdir()
        (self.raiz / "main.py").write_text("viejo", encoding="utf-8")
        (self.raiz / "pandex" / "app.py").write_text("viejo", encoding="utf-8")
        (self.raiz / "requirements.txt").write_text("a==1\n", encoding="utf-8")
        (self.raiz / "config.json").write_text('{"mio": true}', encoding="utf-8")
        (self.raiz / "logs" / "pandex.log").write_text("mi registro", encoding="utf-8")
        (self.raiz / "tasks" / "mi_tarea.py").write_text("mía", encoding="utf-8")

        self.zip = self.tmp / "main.zip"
        with zipfile.ZipFile(self.zip, "w") as z:
            z.writestr("pandex-main/main.py", "nuevo")
            z.writestr("pandex-main/pandex/app.py", "nuevo")
            z.writestr("pandex-main/pandex/nuevo.py", "nuevo")
            z.writestr("pandex-main/requirements.txt", "a==2\n")
            z.writestr("pandex-main/config.json", '{"de_fabrica": true}')
            z.writestr("pandex-main/logs/pandex.log", "otro")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_copia_lo_nuevo_y_respeta_lo_tuyo(self):
        r = actualizar.aplicar(self.raiz, zip_local=self.zip)
        self.assertEqual(r["modo"], "zip")
        self.assertEqual((self.raiz / "main.py").read_text(encoding="utf-8"), "nuevo")
        self.assertEqual((self.raiz / "pandex" / "nuevo.py").read_text(encoding="utf-8"), "nuevo")
        self.assertEqual((self.raiz / "config.json").read_text(encoding="utf-8"), '{"mio": true}')
        self.assertEqual((self.raiz / "logs" / "pandex.log").read_text(encoding="utf-8"), "mi registro")
        self.assertEqual((self.raiz / "tasks" / "mi_tarea.py").read_text(encoding="utf-8"), "mía")
        self.assertTrue(r["dependencias"], "cambió requirements.txt")
        self.assertEqual((r["respaldo"] / "main.py").read_text(encoding="utf-8"), "viejo")

    def test_un_zip_que_no_es_pandex_no_toca_nada(self):
        otro = self.tmp / "otro.zip"
        with zipfile.ZipFile(otro, "w") as z:
            z.writestr("algo/leeme.txt", "hola")
        with self.assertRaises(actualizar.ErrorActualizacion):
            actualizar.aplicar(self.raiz, zip_local=otro)
        self.assertEqual((self.raiz / "main.py").read_text(encoding="utf-8"), "viejo")

    def test_rutas_que_se_salen_se_rechazan(self):
        malo = self.tmp / "malo.zip"
        with zipfile.ZipFile(malo, "w") as z:
            z.writestr("pandex-main/../../fuera.txt", "x")
        with self.assertRaises(actualizar.ErrorActualizacion):
            actualizar.aplicar(self.raiz, zip_local=malo)
        self.assertFalse((self.tmp / "fuera.txt").exists())


class MigrarConfig(unittest.TestCase):
    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())
        self.ruta = self.carpeta / "config.json"

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def test_el_sprite_de_fabrica_deja_paso_al_personaje_nuevo(self):
        self.ruta.write_text(json.dumps({"mascota": {"nombre": "Pygu", "spritesheet": SPRITE_PIXEL,
                                                     "animacion": True}}), encoding="utf-8")
        config = Config(self.ruta)
        self.assertEqual(config.mascota["personaje"], "rusty")
        self.assertEqual(config.mascota["nombre"], "Pygu")
        self.assertNotIn("animacion", config.mascota)
        guardado = json.loads(self.ruta.read_text(encoding="utf-8"))
        self.assertEqual(guardado["version_config"], 4)
        self.assertNotIn("spritesheet", guardado["mascota"], "el de fábrica no se vuelve a guardar")

    def test_el_de_fabrica_con_otros_valores_tambien_pasa_a_rusty(self):
        viejo = {**SPRITE_PIXEL, "archivo": "assets\\panda_robot\\spritesheet.png", "frame_ancho": 192,
                 "frame_alto": 208, "animaciones": {"idle": {"frames": [[0, 0], [0, 1]], "fps": 2}}}
        self.ruta.write_text(json.dumps({"mascota": {"spritesheet": viejo, "posicion": [10, 20]},
                                         "tareas": {"x": {"activa": False}}}), encoding="utf-8")
        config = Config(self.ruta)
        self.assertEqual(config.mascota["personaje"], "rusty")
        self.assertEqual(config.mascota["posicion"], [10, 20])
        self.assertFalse(config.tarea("x")["activa"])
        self.assertNotIn("spritesheet", json.loads(self.ruta.read_text(encoding="utf-8"))["mascota"])

    def test_quien_quedo_en_el_panda_viejo_con_la_v2_pasa_a_rusty(self):
        viejo = {**SPRITE_PIXEL, "frame_ancho": 192}
        self.ruta.write_text(json.dumps({"version_config": 2, "mascota": {
            "personaje": "pixel", "spritesheet": viejo, "nombre": "Pygu"}}), encoding="utf-8")
        config = Config(self.ruta)
        self.assertEqual(config.mascota["personaje"], "rusty")
        self.assertEqual(config.mascota["nombre"], "Pygu")

    def test_un_sprite_propio_se_respeta_tambien_en_v2(self):
        propio = {**SPRITE_PIXEL, "archivo": "assets/mi_gato/sheet.png"}
        self.ruta.write_text(json.dumps({"version_config": 2, "mascota": {
            "personaje": "pixel", "spritesheet": propio}}), encoding="utf-8")
        config = Config(self.ruta)
        self.assertEqual(config.mascota["personaje"], "pixel")
        self.assertEqual(config.mascota["spritesheet"]["archivo"], "assets/mi_gato/sheet.png")

    def test_quien_eligio_el_panda_pixel_en_la_2x_pasa_a_panda_clasico(self):
        self.ruta.write_text(json.dumps({"version_config": 3, "mascota": {"personaje": "pixel"}}),
                             encoding="utf-8")
        self.assertEqual(Config(self.ruta).mascota["personaje"], "panda_clasico")

    def test_el_panda_vectorial_ya_no_existe_y_pasa_a_rusty(self):
        self.ruta.write_text(json.dumps({"version_config": 3, "mascota": {"personaje": "vectorial"}}),
                             encoding="utf-8")
        config = Config(self.ruta)
        self.assertEqual(config.mascota["personaje"], "rusty")
        self.assertEqual(config.mascota["logo"], "personaje")
        self.assertEqual(json.loads(self.ruta.read_text(encoding="utf-8"))["version_config"], 4)

    def test_un_sprite_propio_se_respeta(self):
        propio = {**SPRITE_PIXEL, "archivo": "assets/mi_gato/sheet.png"}
        self.ruta.write_text(json.dumps({"mascota": {"spritesheet": propio}}), encoding="utf-8")
        config = Config(self.ruta)
        self.assertEqual(config.mascota["personaje"], "pixel")
        self.assertEqual(config.mascota["spritesheet"]["archivo"], "assets/mi_gato/sheet.png")


if __name__ == "__main__":
    unittest.main()
