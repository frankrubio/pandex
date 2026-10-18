"""Comprimir carpeta: el .zip trae todo, no pisa otro y los PDF se aligeran con Ghostscript."""

import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from pandex import comprimir


class Comprimir(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.curso = self.tmp / "Calculo"
        (self.curso / "Sem 1").mkdir(parents=True)
        (self.curso / "Sem 1" / "notas.md").write_text("hola " * 5000, encoding="utf-8")
        (self.curso / "foto.jpg").write_bytes(b"\xff" * 100)

    def test_zip_con_la_estructura_y_mas_liviano(self):
        r = comprimir.comprimir(self.curso)
        self.assertEqual(r["zip"], self.tmp / "Calculo.zip")
        with zipfile.ZipFile(r["zip"]) as zf:
            self.assertEqual(sorted(zf.namelist()), ["Calculo/Sem 1/notas.md", "Calculo/foto.jpg"])
            self.assertEqual(zf.getinfo("Calculo/foto.jpg").compress_type, zipfile.ZIP_STORED)
        self.assertLess(r["despues"], r["antes"])
        self.assertTrue((self.curso / "Sem 1" / "notas.md").exists(), "el original no se toca")

    def test_no_pisa_un_zip_que_ya_existe(self):
        (self.tmp / "Calculo.zip").write_bytes(b"mio")
        r = comprimir.comprimir(self.curso)
        self.assertEqual(r["zip"].name, "Calculo (2).zip")
        self.assertEqual((self.tmp / "Calculo.zip").read_bytes(), b"mio")

    def test_pdf_aligerado_solo_si_pesa_menos(self):
        (self.curso / "lectura.pdf").write_bytes(b"%PDF" + b"x" * 5000)

        def falso(origen, destino, gs=None):
            Path(destino).write_bytes(b"%PDF chico")
            return True

        with mock.patch.object(comprimir, "ghostscript", return_value="gs"), \
                mock.patch.object(comprimir, "reducir_pdf", side_effect=falso):
            r = comprimir.comprimir(self.curso, pdfs=True)
        self.assertEqual(r["pdfs"], 1)
        with zipfile.ZipFile(r["zip"]) as zf:
            self.assertEqual(zf.read("Calculo/lectura.pdf"), b"%PDF chico")
        self.assertEqual((self.curso / "lectura.pdf").stat().st_size, 5004, "el original no se toca")

    def test_sin_ghostscript_no_reduce(self):
        with mock.patch.object(comprimir.shutil, "which", return_value=None):
            self.assertFalse(comprimir.reducir_pdf(self.curso / "x.pdf", self.tmp / "y.pdf"))


if __name__ == "__main__":
    unittest.main()
