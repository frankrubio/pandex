"""Adoptar una carpeta que ya tenías: emparejar, leer tu estilo, reordenar y deshacer."""

import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from pandex.canvas import adoptar
from pandex.canvas.estructura import Item
from pandex.canvas.historial import Historial
from pandex.canvas.sincronizar import Candidato

# nombres reales de una cuenta de UTEC y de las carpetas que su dueño ya tenía
CURSOS_UTEC = {
    "com": "Comunicación Integral I (HH6001)  -  Teoría 1  -  2026 - 2",
    "calc": "Fundamentos del Cálculo (CC6101)  -  Teoría 4  -  2026 - 2",
    "cd": "Introducción a Ciencia de Datos e Inteligencia Artificial (DS6001)  -  Teo. 1 - Lab. 11 - 2026 - 2",
    "disc": "Matemáticas Discretas I (CS6005)  -  Teo. 2 - Lab. 21 - 2026 - 2",
    "prog": "Programación I (CS6002)  -  Teoría 1  -  2026 - 2",
    "pi": "Proyectos Interdisciplinarios I (PI6001)  -  Teoría 1  -  2026 - 2",
    "peer": "Peer Mentoring 2026-2",
}
CARPETAS_UTEC = ["Claude outputs", "Comunicacion_Integral_I", "Fundamentos_de_Calculo",
                 "Introduccion_a_la_CD_e_IA", "Matematicas_Discretas_I", "Programacion_I",
                 "Proyectos_Interdisciplinarios_I"]


class Emparejar(unittest.TestCase):
    def test_carpetas_reales(self):
        pares = adoptar.emparejar_carpetas(CURSOS_UTEC, [Path(n) for n in CARPETAS_UTEC])
        nombres = {k: (v.name if v else None) for k, v in pares.items()}
        self.assertEqual(nombres, {
            "com": "Comunicacion_Integral_I", "calc": "Fundamentos_de_Calculo",
            "cd": "Introduccion_a_la_CD_e_IA", "disc": "Matematicas_Discretas_I",
            "prog": "Programacion_I", "pi": "Proyectos_Interdisciplinarios_I", "peer": None,
        })

    def test_una_letra_no_alcanza(self):
        self.assertEqual(adoptar.parecido("Proyectos Interdisciplinarios I", "Programacion_I"), 0)
        self.assertEqual(adoptar.parecido("Física I (FI101)", "FI101 apuntes"), 1.0, "el código manda")


class Convenciones(unittest.TestCase):
    def setUp(self):
        self.raiz = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.raiz, ignore_errors=True)

    def test_formato_de_semana(self):
        self.assertEqual(adoptar.formato_de_carpeta_semana("Sem 3"), "Sem {n}")
        self.assertEqual(adoptar.formato_de_carpeta_semana("Semana 03"), "Semana {n:02d}")
        self.assertEqual(adoptar.formato_de_carpeta_semana("S10"), "S{n}")
        self.assertIsNone(adoptar.formato_de_carpeta_semana("Syllabus"))
        self.assertIsNone(adoptar.formato_de_carpeta_semana("Tema 3"))

    def test_lee_tu_estilo(self):
        for semana, mitades in (("Sem 1", ("Teoría", "Lab")), ("Sem 2", ("Teoría", "Laboratorio")),
                                ("Sem 3", ("Teoría", "Lab"))):
            for mitad in mitades:
                (self.raiz / "Prog" / semana / mitad / "Material de clase").mkdir(parents=True)
        (self.raiz / "Calc" / "Sem 1" / "Actividades").mkdir(parents=True)
        conv = adoptar.detectar_convenciones([self.raiz / "Prog", self.raiz / "Calc"])
        self.assertEqual(conv.formato_semana, "Sem {n}")
        self.assertEqual((conv.teoria, conv.lab, conv.alias_lab), ("Teoría", "Lab", ["Laboratorio"]))
        self.assertEqual(set(conv.secciones), {"Material de clase", "Actividades"})

    def test_mapa_de_secciones(self):
        mapa = adoptar.mapa_secciones(Counter({"Material de clases": 5, "Material de clase": 2,
                                               "Lecturas": 1}), existentes=["Material de clase"])
        self.assertEqual(mapa, {"Material de clases": "Material de clase",
                                "Material de clase": "Material de clase", "Lecturas": "Lecturas"})


class Reordenar(unittest.TestCase):
    """Una carpeta desordenada: lo de Canvas se mueve; lo tuyo, jamás."""

    def setUp(self):
        self.raiz = Path(tempfile.mkdtemp())
        self.prog = self.raiz / "Programacion_I"
        sem = self.prog / "Sem 3"
        sem.mkdir(parents=True)
        (self.prog / "Sem 4" / "Lab").mkdir(parents=True)
        (sem / "Clase 4.pptx").write_bytes(b"a" * 5000)          # de Canvas, en la semana equivocada
        (sem / "Clase 4.md").write_text("<!-- Pandex: convertido -->\n\nhola", encoding="utf-8")
        (sem / "Mi resumen.docx").write_bytes(b"b" * 6000)       # tuyo: no se toca
        (sem / "Lab 4.pdf").write_bytes(b"c" * 7000)             # de Canvas, pero el destino está ocupado
        (self.prog / "Sem 4" / "Lab" / "Lab 4.pdf").write_bytes(b"z" * 10)
        (sem / "Repetida.pdf").write_bytes(b"d" * 8000)          # dos copias: no se sabe cuál mover
        (self.prog / "Repetida.pdf").write_bytes(b"d" * 8000)
        (sem / "Distinta.pdf").write_bytes(b"e" * 100)           # mismo nombre, otro contenido: es tuya

        teoria = {"carpeta": "Programacion_I", "subcarpeta_fija": "Teoría", "crear_secciones": True,
                  "alias": "Prog"}
        lab = {"carpeta": "Programacion_I", "subcarpeta_fija": "Lab", "crear_secciones": True,
               "alias": "Prog (lab)"}
        self.candidatos = [
            Candidato(teoria, {"id": 1}, "Prog", Item("Semana 4", "Material de clase", "Clase 4", 41), 4),
            Candidato(lab, {"id": 2}, "Prog (lab)", Item("Semana 4", None, "Lab 4.pdf", 42), 4),
            Candidato(teoria, {"id": 1}, "Prog", Item("Semana 5", None, "Repetida.pdf", 43), 5),
            Candidato(teoria, {"id": 1}, "Prog", Item("Semana 5", None, "Distinta.pdf", 44), 5),
            Candidato(teoria, {"id": 1}, "Prog", Item("Semana 3", None, "Nueva.pdf", 45), 3),
        ]
        self.metas = {41: {"nombre": "Clase 4.pptx", "tamano": 5000}, 42: {"nombre": "Lab 4.pdf", "tamano": 7000},
                      43: {"nombre": "Repetida.pdf", "tamano": 8000}, 44: {"nombre": "Distinta.pdf", "tamano": 999},
                      45: {"nombre": "Nueva.pdf", "tamano": 1}}
        self.historial = Historial(self.raiz / "historial.json")

    def tearDown(self):
        shutil.rmtree(self.raiz, ignore_errors=True)

    def test_plan_aplicar_y_deshacer(self):
        plan = adoptar.planificar(self.candidatos, self.metas, {"Programacion_I": self.prog}, {})
        destino = self.prog / "Sem 4" / "Teoría" / "Material de clase" / "Clase 4.pptx"
        self.assertEqual([(m.origen.name, m.destino) for m in plan.movimientos], [("Clase 4.pptx", destino)])
        self.assertEqual({motivo for _, _, motivo in plan.dudosos},
                         {"ya hay otro archivo con ese nombre donde va", "tienes 2 copias"})
        self.assertFalse(destino.parent.exists(), "planificar no toca el disco")

        hechos, saltados, diario = adoptar.aplicar(plan, self.historial)
        self.assertEqual((len(hechos), saltados), (1, []))
        self.assertEqual(destino.read_bytes(), b"a" * 5000)
        self.assertTrue((destino.parent / "Clase 4.md").exists(), "su .md de Pandex lo acompaña")
        self.assertTrue((self.prog / "Sem 3" / "Mi resumen.docx").exists(), "lo tuyo no se toca")
        self.assertTrue((self.prog / "Sem 3" / "Distinta.pdf").exists())
        self.assertEqual(self.historial.conocido(41), destino)

        devueltos, _ = adoptar.deshacer(diario)
        self.assertEqual(devueltos, 2)
        self.assertEqual((self.prog / "Sem 3" / "Clase 4.pptx").read_bytes(), b"a" * 5000)
        self.assertTrue((self.prog / "Sem 3" / "Clase 4.md").exists())
        self.assertIsNone(adoptar.ultimo_diario(), "el diario queda marcado como deshecho")

    def test_si_ya_esta_en_cualquiera_de_sus_lugares_se_queda(self):
        lugar = self.prog / "Sem 4" / "Lab"
        shutil.move(str(self.prog / "Sem 3" / "Clase 4.pptx"), str(lugar / "Clase 4.pptx"))
        mismo_en_lab = Candidato({"carpeta": "Programacion_I", "subcarpeta_fija": "Lab", "crear_secciones": True},
                                 {"id": 2}, "Prog (lab)", Item("Semana 4", None, "Clase 4", 51), 4)
        self.metas[51] = self.metas[41]
        plan = adoptar.planificar([self.candidatos[0], mismo_en_lab], self.metas,
                                  {"Programacion_I": self.prog}, {})
        self.assertEqual(plan.movimientos, [])
        self.assertEqual(len(plan.en_su_lugar), 1)


if __name__ == "__main__":
    unittest.main()
