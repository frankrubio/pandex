"""Medir el peso (spec 002, T002.1): suma lo que cuenta y nada más."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("medir_peso", RAIZ / "herramientas" / "medir_peso.py")
medir_peso = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(medir_peso)


class MedirPeso(unittest.TestCase):
    def armar(self, tmp):
        raiz, datos = tmp / "pandex", tmp / "datos"
        sitio = raiz / ".venv" / "lib" / "python3.13" / "site-packages"
        for carpeta in (sitio / "PyQt6", sitio / "pandas", raiz / ".git", datos / "personajes", tmp / "Cursos"):
            carpeta.mkdir(parents=True)
        (raiz / "main.py").write_bytes(b"x" * 100)
        (raiz / ".git" / "pack").write_bytes(b"x" * 10_000)
        (sitio / "PyQt6" / "Qt.so").write_bytes(b"x" * 1000)
        (sitio / "pandas" / "a.py").write_bytes(b"x" * 500)
        (datos / "historial.json").write_bytes(b"x" * 10)
        (datos / "personajes" / "mio.png").write_bytes(b"x" * 7000)
        (tmp / "Cursos" / "clase.pdf").write_bytes(b"x" * 99_999)
        return raiz, datos

    def test_suma_proyecto_venv_y_datos_sin_personajes_ni_cursos_ni_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz, datos = self.armar(Path(tmp))
            r = medir_peso.medir(raiz, datos)
        self.assertEqual((r["proyecto_sin_venv"], r["venv"], r["datos"], r["total"]), (100, 1500, 10, 1610))
        self.assertEqual(r["paquetes"], {"PyQt6": 1000, "pandas": 500})

    def test_limite_y_base_fallan_con_codigo_1(self):
        grande = {"total": 700 * 1024 ** 2, "venv": 0, "proyecto_sin_venv": 0, "datos": 0, "paquetes": {}}
        con_extra = {**grande, "total": 1, "paquetes": {"pandas": 1}}
        with mock.patch.object(medir_peso, "medir", return_value=grande), mock.patch("builtins.print"):
            self.assertEqual(medir_peso.main(["--limite", "600"]), 1)
            self.assertEqual(medir_peso.main(["--limite", "800"]), 0)
        with mock.patch.object(medir_peso, "medir", return_value=con_extra), mock.patch("builtins.print"):
            self.assertEqual(medir_peso.main(["--base"]), 1)


if __name__ == "__main__":
    unittest.main()
