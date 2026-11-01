"""Spec 009: reconectar la carpeta de cursos después de renombrarla o moverla (REC-01…05)."""

import copy
import shutil
import tempfile
import unittest
from pathlib import Path

from pandex.canvas import reconectar


def reglas():
    return [
        {"canvas_id": 1, "nombre_canvas": "Programación I (CS6002) - Teoría 1", "carpeta": "Programacion_I",
         "tipo": "teoria", "subcarpeta_fija": "Teoría"},
        {"canvas_id": 2, "nombre_canvas": "Programación I (CS6002) - Laboratorio 14", "carpeta": "Programacion_I",
         "tipo": "laboratorio", "subcarpeta_fija": "Lab"},
        {"canvas_id": 3, "nombre_canvas": "Fundamentos del Cálculo", "carpeta": "Fundamentos_de_Calculo"},
        {"canvas_id": 4, "nombre_canvas": "Química General", "carpeta": "Quimica_General"},
    ]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.nueva = self.tmp / "Mis_cursos_2026"
        self.nueva.mkdir()
        self.params = {"destino": str(self.tmp / "Cursos_Canvas"), "cursos": reglas(),
                       "formato_semana": "Sem {n}", "estilo_carpetas": "guiones_bajos"}


class Adaptar(Base):
    def test_cambia_destino_y_empareja_aunque_cambien_los_nombres(self):
        (self.nueva / "Programación I").mkdir()
        (self.nueva / "Fundamentos de Cálculo").mkdir()
        (self.nueva / "Otra cosa").mkdir()
        nuevo, informe = reconectar.adaptar(self.params, self.nueva)
        self.assertEqual(nuevo["destino"], str(self.nueva))
        self.assertEqual([c["carpeta"] for c in nuevo["cursos"]],
                         ["Programación I", "Programación I", "Fundamentos de Cálculo", "Quimica_General"])
        self.assertEqual(informe.sin_pareja, ["Quimica_General"])
        self.assertEqual(dict(informe.parejas), {"Programacion_I": "Programación I",
                                                 "Fundamentos_de_Calculo": "Fundamentos de Cálculo"})

    def test_si_la_carpeta_ya_se_llama_igual_no_cambia_nada_mas(self):
        for nombre in ("Programacion_I", "Fundamentos_de_Calculo", "Quimica_General"):
            (self.nueva / nombre).mkdir()
        nuevo, informe = reconectar.adaptar(self.params, self.nueva)
        self.assertEqual(nuevo["cursos"], reglas())
        self.assertEqual(informe.sin_pareja, [])

    def test_una_carpeta_no_sirve_a_dos_cursos(self):
        (self.nueva / "Calculo").mkdir()
        params = copy.deepcopy(self.params)
        params["cursos"] = [{"canvas_id": 3, "nombre_canvas": "Cálculo Diferencial", "carpeta": "Calculo_Diferencial"},
                            {"canvas_id": 5, "nombre_canvas": "Cálculo Integral", "carpeta": "Calculo_Integral"}]
        nuevo, informe = reconectar.adaptar(params, self.nueva)
        usadas = [c["carpeta"] for c in nuevo["cursos"] if c["carpeta"] == "Calculo"]
        self.assertLessEqual(len(usadas), 1)
        self.assertEqual(len(informe.parejas) + len(informe.sin_pareja), 2)


class Estilo(Base):
    def test_lee_tu_estilo(self):
        (self.nueva / "Programación I" / "Semana 01" / "Teoría").mkdir(parents=True)
        nuevo, _ = reconectar.adaptar(self.params, self.nueva)
        self.assertEqual(nuevo["formato_semana"], "Semana {n:02d}")
        self.assertEqual(nuevo["estilo_carpetas"], "propio")

    def test_sin_estilo_que_leer_deja_el_que_tenias(self):
        (self.nueva / "Programacion_I").mkdir()
        nuevo, _ = reconectar.adaptar(self.params, self.nueva)
        self.assertEqual(nuevo["formato_semana"], "Sem {n}")
        self.assertEqual(nuevo["estilo_carpetas"], "guiones_bajos")


class Seguridad(Base):
    def test_no_modifica_lo_que_recibe_ni_toca_el_disco(self):
        (self.nueva / "Programación I" / "Sem 1").mkdir(parents=True)
        (self.nueva / "Programación I" / "Sem 1" / "x.pdf").write_bytes(b"x")
        antes = copy.deepcopy(self.params)
        arbol = sorted(p.relative_to(self.nueva) for p in self.nueva.rglob("*"))
        reconectar.adaptar(self.params, self.nueva)
        self.assertEqual(self.params, antes)
        self.assertEqual(sorted(p.relative_to(self.nueva) for p in self.nueva.rglob("*")), arbol)

    def test_carpeta_que_no_existe(self):
        with self.assertRaises(reconectar.ErrorReconectar):
            reconectar.adaptar(self.params, self.tmp / "no_existe")

    def test_un_archivo_no_es_una_carpeta(self):
        archivo = self.tmp / "a.txt"
        archivo.write_text("x")
        with self.assertRaises(reconectar.ErrorReconectar):
            reconectar.adaptar(self.params, archivo)

    def test_guarda_copia_de_la_configuracion_anterior(self):
        copia = reconectar.guardar_copia(self.params, self.tmp / "datos")
        self.assertTrue(copia.name.startswith("config-canvas-anterior-"))
        self.assertIn("Cursos_Canvas", copia.read_text(encoding="utf-8"))


class Resumen(Base):
    def test_texto_para_el_usuario(self):
        (self.nueva / "Programación I").mkdir()
        _, informe = reconectar.adaptar(self.params, self.nueva)
        texto = informe.texto()
        self.assertIn("Programacion_I → Programación I", texto)
        self.assertIn("Quimica_General", texto)


if __name__ == "__main__":
    unittest.main()
