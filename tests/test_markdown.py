"""Convertir a Markdown: el clasificador, los nombres de los .md y una conversión real."""

import shutil
import tempfile
import unittest
from pathlib import Path

from pandex.markdown import archivos, conversion, lote
from pandex.markdown.clasificador import Clasificador
from tests.apoyo import CtxFalso


class Clasificar(unittest.TestCase):
    CASOS = {
        "AP3_Sem4.pdf": False,                                 # actividad previa
        "TAREA ESPECIAL (TA6).pdf": False,
        "EA2 Evaluación en aula.pdf": False,
        "Preguía de ejercicios 3.pdf": False,
        "Ejercicios_Conjuntos_3.pdf": False,                   # lista de ejercicios
        "Plantilla carta de presentación.docx": False,
        "index.html": False,                                   # formato
        "Teoría y ejercicios de límites.pdf": True,
        "Trigonometry_Toolkit.pdf": True,                      # resumen tipo NotebookLM
        "Sem9_Clase Funciones Exponenciales.pdf": True,
        "Resumen Funciones exponenciales.pdf": True,
        "Trabajos/Mi informe.pdf": False,                      # trabajo propio
        "Actividades/Lectura 1.pdf": True,                     # el nombre manda sobre la carpeta
        "Actividades/Documento.pdf": False,
        "Sem 3/algo sin pistas.pdf": True,
    }

    def test_reglas_de_fabrica(self):
        clasificador = Clasificador()
        for ruta, esperado in self.CASOS.items():
            with self.subTest(ruta=ruta):
                self.assertEqual(clasificador.clasificar(Path("C:/curso") / ruta)[0], esperado)

    def test_tus_palabras_mandan(self):
        clasificador = Clasificador({"incluir_palabras": ["ejercicios"], "excluir_palabras": ["borrador"]})
        self.assertTrue(clasificador.clasificar(Path("Ejercicios_Conjuntos_3.pdf"))[0])
        self.assertFalse(clasificador.clasificar(Path("Clase 2 borrador.pdf"))[0])


class Archivos(unittest.TestCase):
    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def test_nombres_repetidos_se_distinguen(self):
        for nombre in ("Clase 3.pptx", "Clase 3.pdf", "Clase 4.pdf"):
            (self.carpeta / nombre).write_bytes(b"x")
        self.assertEqual(archivos.ruta_md(self.carpeta / "Clase 3.pptx").name, "Clase 3 (pptx).md")
        self.assertEqual(archivos.ruta_md(self.carpeta / "Clase 4.pdf").name, "Clase 4.md")

    def test_codificacion_por_reglas(self):
        self.assertEqual(conversion.detectar_codificacion(b"\xef\xbb\xbfhola"), "utf-8-sig")
        self.assertEqual(conversion.detectar_codificacion("ñandú".encode("utf-8")), "utf-8")
        self.assertEqual(conversion.detectar_codificacion("Año;Niño\n".encode("cp1252")), "cp1252")


class Conversion(unittest.TestCase):
    """Una conversión de verdad con MarkItDown (un CSV: rápido y sin OCR)."""

    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())
        (self.carpeta / "notas.csv").write_text("curso,nota\nCálculo,18\n", encoding="utf-8")
        (self.carpeta / "propio.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        (self.carpeta / "propio.md").write_text("mis apuntes", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def convertir(self, forzar=False):
        entrada = {"carpeta": str(self.carpeta), "filtro": "todos", "forzar": forzar}
        return lote.convertir(CtxFalso({"ocr_local": False}, entrada))

    def test_convierte_salta_y_protege(self):
        r = self.convertir()
        md = self.carpeta / "notas.md"
        self.assertTrue(archivos.generado_por_pandex(md))
        self.assertIn("Cálculo", md.read_text(encoding="utf-8"))
        self.assertTrue(r["ok"])

        r = self.convertir()
        self.assertIn("ya estaban", r["resumen"])

        r = self.convertir(forzar=True)
        self.assertEqual((self.carpeta / "propio.md").read_text(encoding="utf-8"), "mis apuntes",
                         "un .md escrito por ti nunca se pisa")
        self.assertIn(".md tuyos que no se pisaron", r["informe"])


    def test_en_un_proceso_aparte_da_lo_mismo_y_no_carga_el_conversor_aqui(self):
        import subprocess
        import sys

        from pandex.markdown import proceso

        entrada = {"carpeta": self.carpeta, "filtro": "todos", "forzar": False}
        ctx = CtxFalso({"ocr_local": False}, entrada)
        avances = []
        ctx.progreso = lambda n, t: avances.append((n, t))
        r = proceso.convertir_aparte(ctx)
        self.assertTrue(r["ok"], r)
        self.assertIn("Cálculo", (self.carpeta / "notas.md").read_text(encoding="utf-8"))
        self.assertEqual(r["carpeta"], str(self.carpeta))
        self.assertTrue(avances, "el avance llega desde el proceso hijo")
        # comprobado en un intérprete limpio: convertir aparte no carga MarkItDown en el padre
        codigo = ("import sys, json; from pandex.markdown import proceso; "
                  "print(json.dumps('markitdown' in sys.modules))")
        salida = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True)
        self.assertEqual(salida.stdout.strip(), "false")

if __name__ == "__main__":
    unittest.main()
