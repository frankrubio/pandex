"""Spec 014: adaptar Pandex a nombres en inglés (ING-01…ING-06)."""

import shutil
import tempfile
import time
import unittest
from collections import Counter
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from pandex.canvas import adoptar, asistente, destinos, estructura, nombres, reconectar
from pandex.canvas.estructura import Item
from pandex.markdown.clasificador import Clasificador
from tests.apoyo import CanvasFalso, ConCarpetaTemporal, modulo

APP = QApplication.instance() or QApplication([])


class SemanasEnIngles(unittest.TestCase):
    """ING-01: semanas en inglés sin confundir Semester ni Course."""

    def setUp(self):
        self.curso = Path(tempfile.mkdtemp()) / "Course_Calculus"
        self.curso.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.curso.parent, True)
        self.addCleanup(setattr, nombres, "ESTILO_CARPETAS", nombres.ESTILO_CARPETAS)
        nombres.ESTILO_CARPETAS = "propio"

    def test_numero_de_semana_en_ingles_y_sin_falsos_positivos(self):
        casos = {
            "Week 3": 3,
            "Week 03 - Limits": 3,
            "Week_04": 4,
            "Week-5": 5,
            "Week. 6": 6,
            "Wk 7": 7,
            "Wk08": 8,
            "Wk_09 - Derivatives": 9,
            "Sem_10": 10,
            "Sem-11": 11,
            "Sem. 12": 12,
            "01_Week_2": 2,
            "Semester 1": None,
            "Semester 2026-1": None,
            "Semestre 2026": None,
            "Sem 2026": None,
            "Course 1": None,
            "Newsweek 3": None,
        }
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(nombres.numero_de_semana(texto), esperado)

    def test_formato_carpeta_semana_en_ingles(self):
        self.assertEqual(adoptar.formato_de_carpeta_semana("Week 3"), "Week {n}")
        self.assertEqual(adoptar.formato_de_carpeta_semana("Week 03"), "Week {n:02d}")
        self.assertEqual(adoptar.formato_de_carpeta_semana("Week_03"), "Week_{n:02d}")
        self.assertEqual(adoptar.formato_de_carpeta_semana("Wk 4"), "Wk {n}")
        self.assertEqual(adoptar.formato_de_carpeta_semana("Wk_04"), "Wk_{n:02d}")
        self.assertEqual(adoptar.formato_de_carpeta_semana("W05"), "W{n:02d}")
        self.assertIsNone(adoptar.formato_de_carpeta_semana("Semester 1"))
        self.assertIsNone(adoptar.formato_de_carpeta_semana("Semester_02"))
        self.assertIsNone(adoptar.formato_de_carpeta_semana("Course 1"))
        self.assertIsNone(adoptar.formato_de_carpeta_semana("Course_02"))

    def test_reutiliza_carpetas_de_semana_en_ingles(self):
        for carpeta, semana in (("Week 01", 1), ("Week_02", 2), ("Wk 3", 3), ("Wk_04", 4), ("W05", 5), ("S06", 6)):
            with self.subTest(carpeta=carpeta):
                (self.curso / carpeta).mkdir()
                d = destinos.carpeta_destino(self.curso, {"crear_secciones": True},
                                             Item(f"Week {semana}", None, "a.pdf", semana), semana, {})
                self.assertEqual(d, self.curso / carpeta)


class MitadesEnIngles(unittest.TestCase):
    """ING-02: Theory, Lecture, Laboratory y Labs como mitades equivalentes."""

    def setUp(self):
        self.curso = Path(tempfile.mkdtemp()) / "Physics_I"
        self.curso.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.curso.parent, True)
        self.addCleanup(setattr, nombres, "ESTILO_CARPETAS", nombres.ESTILO_CARPETAS)
        nombres.ESTILO_CARPETAS = "propio"

    def test_es_laboratorio_en_ingles(self):
        self.assertTrue(nombres.es_laboratorio("Physics I (PH101) - Laboratory 2 - Fall 2026"))
        self.assertTrue(nombres.es_laboratorio("Chemistry I - Labs 3"))
        self.assertTrue(nombres.es_laboratorio("CS101_Laboratory_1"))
        self.assertFalse(nombres.es_laboratorio("Physics I (PH101) - Lecture 1 - Fall 2026"))
        self.assertFalse(nombres.es_laboratorio("Data Labeling - Theory 1"))

    def test_agrupar_y_emparejar_cursos_en_ingles(self):
        cursos = [
            {"id": 1, "name": "Physics I (PH101) - Lecture 1 - Fall Semester 2026"},
            {"id": 2, "name": "Physics I (PH101) - Laboratory 2 - Fall Semester 2026"},
            {"id": 3, "name": "Chemistry I (CH101) - Theory 1 - Semester 2"},
            {"id": 4, "name": "Chemistry I (CH101) - Lab 3 - Semester 2"},
            {"id": 5, "name": "Data Science (DS101) - Lec. 1 - Lab. 11 - Fall 2026"},
        ]
        grupos = estructura.agrupar([estructura.resumir(c, []) for c in cursos])
        ids = sorted(([r.curso["id"] for r in g] for g in grupos), key=lambda x: (len(x), x))
        self.assertEqual(ids, [[5], [1, 2], [3, 4]])

        reglas = [
            {"codigo": "PH101", "tipo": "lecture"},
            {"codigo": "PH101", "tipo": "laboratory"},
            {"codigo": "CH101", "tipo": "theory"},
            {"codigo": "CH101", "tipo": "lab"},
        ]
        parejas = estructura.emparejar_cursos(cursos, reglas)
        self.assertEqual([c["id"] for _, c in parejas], [1, 2, 3, 4])
        self.assertEqual(estructura.alias_curso(reglas[1], cursos[1]), "Physics I (lab)")

    def test_reutiliza_carpetas_theory_lecture_y_laboratory(self):
        (self.curso / "Week 01" / "Lecture" / "Class Material").mkdir(parents=True)
        (self.curso / "Week 01" / "Laboratory").mkdir(parents=True)
        (self.curso / "Week 02" / "Theory").mkdir(parents=True)

        regla_teo = {"crear_secciones": True, "subcarpeta_fija": "Teoría"}
        regla_lab = {"crear_secciones": True, "subcarpeta_fija": "Lab"}
        mapa = {"material de clase": "Material de clase"}

        d_lec = destinos.carpeta_destino(self.curso, regla_teo, Item("Week 1", "Material de clase", "a.pdf", 1),
                                         1, mapa)
        d_lab = destinos.carpeta_destino(self.curso, regla_lab, Item("Week 1", None, "b.pdf", 2), 1, mapa)
        d_theo = destinos.carpeta_destino(self.curso, regla_teo, Item("Week 2", None, "c.pdf", 3), 2, mapa)

        self.assertEqual(d_lec, self.curso / "Week 01" / "Lecture" / "Class Material")
        self.assertEqual(d_lab, self.curso / "Week 01" / "Laboratory")
        self.assertEqual(d_theo, self.curso / "Week 02" / "Theory")
        self.assertEqual(sorted(p.name for p in (self.curso / "Week 01").iterdir()), ["Laboratory", "Lecture"])

        self.assertIs(destinos.mitad_de(self.curso / "Week 01" / "Lecture" / "a.pdf",
                                        self.curso, [regla_teo, regla_lab]), regla_teo)
        self.assertIs(destinos.mitad_de(self.curso / "Week 01" / "Laboratory" / "b.pdf",
                                        self.curso, [regla_teo, regla_lab]), regla_lab)


class EmparejarEnIngles(unittest.TestCase):
    """ING-03: emparejar carpetas con Course, Semester y conectores en inglés."""

    def test_empareja_carpetas_con_course_y_semester(self):
        cursos = {
            "calc": "Calculus I (MA101) - Lecture 1 - Fall Semester 2026",
            "algo": "Algorithms (CS202) - Fall Semester 2026",
            "ds": "Introduction to Data Science and AI (DS101) - Spring Term 2026",
            "phys": "Fundamentals of Physics (PH101) - Semester 2",
        }
        carpetas = [
            Path("Course_01_Calculus_I"),
            Path("Course 02 - Algorithms"),
            Path("Intro_DS_AI"),
            Path("Semester_2_Fundamentals_Physics"),
            Path("Semester_1"),
            Path("Course_05_History"),
        ]
        pares = adoptar.emparejar_carpetas(cursos, carpetas)
        nombres_pares = {k: (v.name if v else None) for k, v in pares.items()}
        self.assertEqual(nombres_pares, {
            "calc": "Course_01_Calculus_I",
            "algo": "Course 02 - Algorithms",
            "ds": "Intro_DS_AI",
            "phys": "Semester_2_Fundamentals_Physics",
        })

    def test_no_confunde_cursos_que_solo_comparten_course_semester_o_and(self):
        self.assertEqual(adoptar.parecido("Course 101 - Physics", "Course 102 - History"), 0.0)
        self.assertEqual(adoptar.parecido("Semester 1 - Biology", "Semester 1 - Literature"), 0.0)
        self.assertEqual(adoptar.parecido("Physics and Chemistry", "History and Art"), 0.0)
        self.assertEqual(adoptar.parecido("Peer Mentoring", "Semester_1"), 0.0)


class ConvencionesYSeccionesEnIngles(unittest.TestCase):
    """ING-04: detectar convenciones en inglés y emparejar secciones bilingües."""

    def setUp(self):
        self.raiz = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.raiz, True)
        self.addCleanup(setattr, nombres, "ESTILO_CARPETAS", nombres.ESTILO_CARPETAS)
        nombres.ESTILO_CARPETAS = "propio"

    def test_detecta_wk_lecture_y_laboratory_sin_confundirlos_con_secciones(self):
        for semana in ("Wk 01", "Wk 02"):
            (self.raiz / "Physics" / semana / "Lecture" / "Class Material").mkdir(parents=True)
            (self.raiz / "Physics" / semana / "Laboratory" / "Assignments").mkdir(parents=True)
        (self.raiz / "Physics" / "Wk 01" / "Theory").mkdir(parents=True)

        conv = adoptar.detectar_convenciones([self.raiz / "Physics"])
        self.assertTrue(conv.detectada)
        self.assertTrue(conv.semana_detectada)
        self.assertTrue(conv.teoria_detectada)
        self.assertTrue(conv.lab_detectada)
        self.assertEqual(conv.formato_semana, "Wk {n:02d}")
        self.assertEqual(conv.teoria, "Lecture")
        self.assertEqual(conv.alias_teoria, ["Theory"])
        self.assertEqual(conv.lab, "Laboratory")
        self.assertEqual(set(conv.secciones), {"Class Material", "Assignments"})

    def test_mapa_secciones_bilingue_y_plurales_en_ingles(self):
        mapa = adoptar.mapa_secciones(
            Counter({"Material de clase": 5, "Actividades": 3, "Tareas": 2, "Lecturas": 1, "Summaries": 2}),
            existentes=["Class Material", "Activities", "Assignments", "Readings", "Summary"],
        )
        self.assertEqual(mapa, {
            "Material de clase": "Class Material",
            "Actividades": "Activities",
            "Tareas": "Assignments",
            "Lecturas": "Readings",
            "Summaries": "Summary",
        })

    def test_reutiliza_syllabus_para_modulo_silabo_y_course_info(self):
        curso = self.raiz / "Calculus"
        (curso / "Syllabus").mkdir(parents=True)
        (curso / "Course Information").mkdir(parents=True)
        d1 = destinos.carpeta_destino(curso, {"crear_secciones": True}, Item("Sílabo", None, "s.pdf", 1), None, {})
        d2 = destinos.carpeta_destino(curso, {"crear_secciones": True},
                                      Item("Información del curso", None, "i.pdf", 2), None, {})
        self.assertEqual(d1, curso / "Syllabus")
        self.assertEqual(d2, curso / "Course Information")


class AsistenteYReconectarEnIngles(ConCarpetaTemporal):
    """ING-05: asistente en inglés (carpeta nueva) y reconectar carpeta en inglés."""

    def test_asistente_carpeta_nueva_en_ingles_usa_week_y_lecture(self):
        propios = (asistente.Canvas, asistente.QMessageBox)
        self.addCleanup(setattr, asistente, "Canvas", propios[0])
        self.addCleanup(setattr, asistente, "QMessageBox", propios[1])

        class Mensajes:
            StandardButton = asistente.QMessageBox.StandardButton
            information = warning = critical = question = classmethod(lambda cls, *a, **k: cls.StandardButton.Yes)

        asistente.Canvas = CanvasFalso
        asistente.QMessageBox = Mensajes
        CanvasFalso.reiniciar(
            cursos=[
                {"id": 1, "name": "Calculus I (MA101) - Lecture 1 - Fall Semester 2026"},
                {"id": 2, "name": "Calculus I (MA101) - Laboratory 2 - Fall Semester 2026"},
            ],
            modulos={
                1: [modulo("Week 1", ("sub", "Class Material"), ("file", "Lecture 1.pdf", 11)),
                    modulo("Week 2", ("sub", "Class Material"), ("file", "Lecture 2.pdf", 12))],
                2: [modulo("Week 1", ("file", "Lab 1.pdf", 21))],
            },
            archivos={11: ("Lecture 1.pdf", 5000), 12: ("Lecture 2.pdf", 5100), 21: ("Lab 1.pdf", 5200)},
        )

        params = {}
        w = asistente.AsistenteCanvas(params, lambda: None)
        w.show()
        w.page(asistente.BIENVENIDA).url.setText("canvas.ejemplo.edu")
        w.next()
        limite = time.monotonic() + 10
        while w.currentId() != asistente.CURSOS:
            if time.monotonic() > limite:
                self.fail("se acabó el tiempo esperando al asistente")
            APP.processEvents()
            time.sleep(0.01)

        self.assertEqual(len(w.estado.grupos), 1, "Lecture y Laboratory quedan emparejados")
        w.next()
        carpeta = w.page(asistente.CARPETA)
        carpeta.padre.setText(str(self.tmp))
        carpeta.nombre.setText("Semester 2")
        w.next()
        w.next()
        w.accept()

        raiz = self.tmp / "Semester_2"
        self.assertEqual(params["formato_semana"], "Week {n}")
        self.assertEqual([(r["canvas_id"], r.get("subcarpeta_fija")) for r in params["cursos"]],
                         [(1, "Lecture"), (2, "Lab")])
        self.assertTrue((raiz / "Calculus_I" / "Week_1" / "Lecture").is_dir())
        self.assertTrue((raiz / "Calculus_I" / "Week_1" / "Lab").is_dir())

    def test_reconectar_actualiza_mitades_semanas_y_secciones_en_ingles(self):
        nueva = self.tmp / "Semester_2"
        (nueva / "Course_Programacion_I" / "Week_01" / "Lecture" / "Class_Material").mkdir(parents=True)
        (nueva / "Course_Programacion_I" / "Week_01" / "Laboratory").mkdir(parents=True)
        params = {
            "destino": str(self.tmp / "Cursos_Canvas"),
            "formato_semana": "Sem {n}",
            "estilo_carpetas": "guiones_bajos",
            "secciones": {"material de clase": "Material de clase", "recursos": "Recursos"},
            "cursos": [
                {"canvas_id": 1, "nombre_canvas": "Programación I (CS6002) - Teoría 1",
                 "carpeta": "Programacion_I", "tipo": "teoria", "subcarpeta_fija": "Teoría"},
                {"canvas_id": 2, "nombre_canvas": "Programación I (CS6002) - Laboratorio 14",
                 "carpeta": "Programacion_I", "tipo": "laboratorio", "subcarpeta_fija": "Lab"},
            ],
        }
        nuevo, _ = reconectar.adaptar(params, nueva)
        self.assertEqual(nuevo["formato_semana"], "Week_{n:02d}")
        self.assertEqual(nuevo["estilo_carpetas"], "propio")
        self.assertEqual(nuevo["cursos"][0]["carpeta"], "Course_Programacion_I")
        self.assertEqual(nuevo["cursos"][0]["subcarpeta_fija"], "Lecture")
        self.assertEqual(nuevo["cursos"][1]["subcarpeta_fija"], "Laboratory")
        self.assertEqual(nuevo["secciones"], {"material de clase": "Class_Material", "recursos": "Recursos"})

    def test_sincronizar_sobre_carpetas_en_ingles_no_crea_duplicados(self):
        raiz = self.tmp / "Semester_2"
        curso = raiz / "Course_Calculus_I"
        (curso / "Week_01" / "Lecture" / "Class_Material").mkdir(parents=True)
        (curso / "Week_01" / "Laboratory").mkdir(parents=True)
        (curso / "Syllabus").mkdir(parents=True)

        CanvasFalso.reiniciar(
            cursos=[
                {"id": 1, "name": "Calculus I (MA101) - Lecture 1 - Fall Semester 2026"},
                {"id": 2, "name": "Calculus I (MA101) - Laboratory 2 - Fall Semester 2026"},
            ],
            modulos={
                1: [modulo("Sílabo", ("file", "Syllabus.pdf", 10)),
                    modulo("Week 1", ("sub", "Material de clase"), ("file", "Lecture 1.pdf", 11)),
                    modulo("Week 2", ("sub", "Material de clase"), ("file", "Lecture 2.pdf", 12))],
                2: [modulo("Week 1", ("file", "Lab 1.pdf", 21))],
            },
            archivos={
                10: ("Syllabus.pdf", 4500),
                11: ("Lecture 1.pdf", 5000),
                12: ("Lecture 2.pdf", 5100),
                21: ("Lab 1.pdf", 5200),
            },
        )
        params = {
            "canvas_url": "https://canvas.ejemplo.edu",
            "destino": str(raiz),
            "formato_semana": "Week_{n:02d}",
            "estilo_carpetas": "propio",
            "secciones": {"material de clase": "Class_Material"},
            "cursos": [
                {"canvas_id": 1, "carpeta": "Course_Calculus_I", "tipo": "lecture",
                 "subcarpeta_fija": "Lecture", "crear_secciones": True, "otros_modulos": True},
                {"canvas_id": 2, "carpeta": "Course_Calculus_I", "tipo": "laboratory",
                 "subcarpeta_fija": "Laboratory", "crear_secciones": True, "otros_modulos": True},
            ],
        }
        r, _ = self.sincronizar(params)
        self.assertTrue(r["ok"], r)
        self.assertTrue((curso / "Syllabus" / "Syllabus.pdf").exists())
        self.assertTrue((curso / "Week_01" / "Lecture" / "Class_Material" / "Lecture 1.pdf").exists())
        self.assertTrue((curso / "Week_01" / "Laboratory" / "Lab 1.pdf").exists())
        self.assertTrue((curso / "Week_02" / "Lecture" / "Class_Material" / "Lecture 2.pdf").exists())
        self.assertEqual(sorted(p.name for p in curso.iterdir()), ["Syllabus", "Week_01", "Week_02"])
        self.assertEqual(sorted(p.name for p in (curso / "Week_01").iterdir()), ["Laboratory", "Lecture"])


class ClasificadorEnIngles(unittest.TestCase):
    """ING-06: «Material de estudio» reconoce nombres y carpetas en inglés."""

    CASOS = {
        "Homework 2.pdf": False,
        "HW3_Limits.pdf": False,
        "Assignment_1.pdf": False,
        "Quiz 4.pdf": False,
        "Midterm_Exam.pdf": False,
        "Final Exam Review Template.docx": False,
        "Grading Rubric.pdf": False,
        "Course Schedule.pdf": False,
        "Exercises_Week_3.pdf": False,
        "Problem_Set_2.pdf": False,
        "Worksheet_4.pdf": False,
        "Theory and exercises.pdf": True,
        "Lecture_05_Derivatives.pdf": True,
        "Week3_Slides.pptx": True,
        "Study_Guide_Chapter_2.pdf": True,
        "Reading_Chapter_4.pdf": True,
        "Submissions/My_Report.pdf": False,
        "My Work/Draft.pdf": False,
        "Assignments/Document.pdf": False,
        "Assignments/Reading 1.pdf": True,
        "Course Information/Welcome.pdf": False,
        "Week 3/untitled.pdf": True,
    }

    def test_clasifica_nombres_y_carpetas_en_ingles(self):
        clasificador = Clasificador()
        for ruta, esperado in self.CASOS.items():
            with self.subTest(ruta=ruta):
                self.assertEqual(clasificador.clasificar(Path("C:/Semester_2/Calculus") / ruta)[0], esperado)


if __name__ == "__main__":
    unittest.main()
