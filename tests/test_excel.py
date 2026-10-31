"""Excel a Markdown sin pandas (ADR-0001, D2): misma tabla, 81 MB menos."""

import datetime as dt
import importlib.util
import io
import unittest

from pandex.markdown import excel

HAY_OPENPYXL = importlib.util.find_spec("openpyxl") is not None
HAY_MARKITDOWN = importlib.util.find_spec("markitdown") is not None


class Tabla(unittest.TestCase):
    def test_primera_fila_es_encabezado_y_recorta_bordes_vacios(self):
        md = excel.tabla([["Nombre", "Nota", None], ["Ana", 18.0, None], [None, None, None]])
        self.assertEqual(md, "| Nombre | Nota |\n| --- | --- |\n| Ana | 18 |")

    def test_celdas_especiales(self):
        md = excel.tabla([["a|b", "fecha", "ok"], ["x\ny", dt.datetime(2026, 10, 31), True]])
        self.assertIn("a\\|b", md)
        self.assertIn("| x y | 2026-10-31 | TRUE |", md)

    def test_hoja_vacia(self):
        self.assertEqual(excel.tabla([[None], []]), "")


@unittest.skipUnless(HAY_OPENPYXL, "openpyxl solo viene con «Convertir a Markdown»")
class Xlsx(unittest.TestCase):
    def libro(self):
        import openpyxl

        libro = openpyxl.Workbook()
        hoja = libro.active
        hoja.title = "Notas"
        hoja.append(["Alumno", "PC1"])
        hoja.append(["Ana", 17])
        libro.create_sheet("Vacía")
        datos = io.BytesIO()
        libro.save(datos)
        return datos.getvalue()

    def test_cada_hoja_con_su_tabla(self):
        md = excel.a_markdown(self.libro(), ".xlsx")
        self.assertIn("## Notas\n| Alumno | PC1 |\n| --- | --- |\n| Ana | 17 |", md)
        self.assertIn("## Vacía\n_(hoja vacía)_", md)

    @unittest.skipUnless(HAY_MARKITDOWN, "sin «Convertir a Markdown»")
    def test_markitdown_usa_el_conversor_sin_pandas(self):
        from pandex.markdown.conversion import crear_markitdown

        resultado = crear_markitdown().convert_stream(io.BytesIO(self.libro()), file_extension=".xlsx")
        self.assertIn("| Ana | 17 |", resultado.markdown)


class SinPandas(unittest.TestCase):
    def test_los_requisitos_no_traen_pandas(self):
        from pathlib import Path

        texto = (Path(__file__).resolve().parent.parent / "requirements-markdown.txt").read_text(encoding="utf-8")
        self.assertNotRegex(texto, r"markitdown\[[^\]]*xls", "xlsx/xls de MarkItDown instalan pandas")
        self.assertIn("openpyxl==", texto)
        self.assertIn("xlrd==", texto)


if __name__ == "__main__":
    unittest.main()
