import json
import tempfile
import unittest
from pathlib import Path

from pandex import plugins, rutas


class Manifiestos(unittest.TestCase):
    def test_directorio_personal_esta_fuera_del_repositorio(self):
        raiz = rutas.RAIZ.resolve()
        self.assertFalse(raiz in rutas.PLUGINS_PERSONALES.resolve().parents)
        self.assertEqual(rutas.PLUGINS_PERSONALES, rutas.DATOS / "plugins_personales")

    def test_manifest_valido(self):
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            manifest = {
                "id": "depa",
                "nombre": "Departamento",
                "version": "1.0.0",
                "entrada": "depa.py",
                "descripcion": "Tareas del departamento",
                "permisos": ["red.departamento", "datos.tareas", "avisos.locales"],
                "licencia": "MIT",
            }
            (carpeta / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (carpeta / "depa.py").write_text("class Task:\n    id = 'depa'\n", encoding="utf-8")
            data = plugins.leer_manifest(carpeta)
        self.assertEqual(data["id"], "depa")
        self.assertIn("datos.tareas", data["permisos"])

    def test_manifest_rechaza_permisos_y_rutas_inseguras(self):
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            for entrada in ("../main.py", "/tmp/main.py"):
                (carpeta / "manifest.json").write_text(json.dumps({
                    "id": "malo",
                    "nombre": "Malo",
                    "version": "1.0.0",
                    "entrada": entrada,
                    "permisos": ["sistema.archivos"],
                    "licencia": "MIT",
                }), encoding="utf-8")
                with self.assertRaises(plugins.ErrorManifest):
                    plugins.leer_manifest(carpeta)

    def test_instalar_zip_impide_ruta_de_escape(self):
        import zipfile

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            archivo = base / "mal.zip"
            destino = base / "personal"
            with zipfile.ZipFile(archivo, "w") as zf:
                zf.writestr("../fuera.py", "x = 1")
            with self.assertRaises(plugins.ErrorPaquete):
                plugins.instalar_zip(archivo, destino)
            self.assertFalse((base / "fuera.py").exists())

    def test_plugin_personal_valido_se_carga_sin_exponer_ganchos_peligrosos(self):
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            plugin = carpeta / "depa"
            plugin.mkdir()
            (plugin / "manifest.json").write_text(json.dumps({
                "id": "depa",
                "nombre": "Departamento",
                "version": "1.0.0",
                "entrada": "depa.py",
                "licencia": "MIT",
                "permisos": ["datos.tareas", "avisos.locales"],
            }), encoding="utf-8")
            (plugin / "depa.py").write_text(
                "class Task:\n"
                "    id = 'depa'\n"
                "    nombre = 'Departamento'\n"
                "    def run(self, ctx):\n"
                "        return {'ok': True, 'resumen': 'Listo'}\n",
                encoding="utf-8",
            )
            encontradas = plugins.descubrir_personales(carpeta)
        self.assertEqual([t.id for t in encontradas], ["depa"])

    def test_instalar_zip_personal_usa_el_id_del_manifest(self):
        import zipfile

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            archivo = base / "depa.zip"
            personal = base / "personales"
            with zipfile.ZipFile(archivo, "w") as zf:
                zf.writestr("manifest.json", json.dumps({
                    "id": "depa",
                    "nombre": "Departamento",
                    "version": "1.0.0",
                    "entrada": "depa.py",
                    "licencia": "MIT",
                    "permisos": ["datos.tareas"],
                }))
                zf.writestr("depa.py", "class Task:\n    id = 'depa'\n")
            destino = plugins.instalar_personal(archivo, personal)
            self.assertEqual(destino, personal / "depa")
            self.assertTrue((destino / "manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
