"""Las piezas de pandex.canvas por separado: nombres, destinos, índice, estructura, sesión."""

import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from pandex.canvas import destinos, estructura, nombres, sesion
from pandex.canvas.estructura import Item


class Nombres(unittest.TestCase):
    def test_extension_sale_del_nombre_real(self):
        titulo = "Olcina, J., (2011). MEGACIUDADES: ESPACIOS DE RELACIÓN"
        self.assertEqual(nombres.nombre_destino(titulo, "olcina.pdf"),
                         "Olcina, J., (2011). MEGACIUDADES- ESPACIOS DE RELACIÓN.pdf")
        self.assertEqual(nombres.nombre_destino("Guia 6.pdf", "guia.pdf"), "Guia 6.pdf")
        self.assertEqual(nombres.nombre_destino("", "real.docx"), "real.docx")
        self.assertLessEqual(len(nombres.nombre_destino("x" * 400, "a.pdf")), 200)

    def test_semanas(self):
        self.assertEqual(nombres.numero_de_semana("Semana 7"), 7)
        self.assertEqual(nombres.numero_de_semana("Week 03 - Intro"), 3)
        self.assertEqual(nombres.numero_de_semana("Sem12"), 12)
        self.assertIsNone(nombres.numero_de_semana("Sílabo y anexo"))
        self.assertIsNone(nombres.numero_de_semana("Semestre 2026"))

    def test_laboratorio_como_palabra(self):
        self.assertTrue(nombres.es_laboratorio("Programación I - Laboratorio 14"))
        self.assertTrue(nombres.es_laboratorio("Teo. 1 - Lab. 11"))
        self.assertFalse(nombres.es_laboratorio("Taller colaborativo - Teoría 2"))


class Destinos(unittest.TestCase):
    def setUp(self):
        self.curso = Path(tempfile.mkdtemp()) / "Curso"
        self.curso.mkdir()

    def tearDown(self):
        shutil.rmtree(self.curso.parent, ignore_errors=True)

    def item(self, seccion, modulo="Semana 3"):
        return Item(modulo, seccion, "x.pdf", 1)

    def test_seccion_mas_especifica_gana(self):
        mapa = {"actividades": "Actividades", "actividades previas": "AP"}
        self.assertEqual(destinos.carpeta_de_seccion("Actividades Previas", mapa), "AP")
        self.assertEqual(destinos.carpeta_de_seccion("Actividades", mapa), "Actividades")
        self.assertEqual(destinos.carpeta_de_seccion("Material de clases",
                                                     {"material de clase": "Material de clase"}),
                         "Material de clase")

    def test_clasico_seccion_desconocida_no_crea_nada(self):
        d = destinos.carpeta_destino(self.curso, {}, self.item("Rarísima"), 3, {"material": "Material"})
        self.assertIsNone(d)
        self.assertEqual(list(self.curso.iterdir()), [])

    def test_clasico_con_mitad_usa_tu_seccion_solo_si_existe(self):
        regla = {"subcarpeta_fija": "Lab", "alias_subcarpeta": ["Laboratorio"]}
        mapa = {"material de clase": "Material de clase"}
        d = destinos.carpeta_destino(self.curso, regla, self.item("Material de clase"), 3, mapa)
        self.assertEqual(d, self.curso / "Sem 3" / "Lab")
        (self.curso / "Sem 4" / "Laboratorio" / "Material de clase").mkdir(parents=True)
        d = destinos.carpeta_destino(self.curso, regla, self.item("Material de clase"), 4, mapa)
        self.assertEqual(d, self.curso / "Sem 4" / "Laboratorio" / "Material de clase")

    def test_semana_existente_con_otro_nombre(self):
        (self.curso / "Semana 05").mkdir()
        d = destinos.carpeta_destino(self.curso, {"crear_secciones": True}, self.item(None), 5, {})
        self.assertEqual(d, self.curso / "Semana 05")

    def test_vista_previa_no_crea_carpetas(self):
        regla = {"crear_secciones": True, "subcarpeta_fija": "Teoría"}
        d = destinos.carpeta_destino(self.curso, regla, self.item("Lecturas"), 2, {}, "Semana {n:02d}",
                                     crear=False)
        self.assertEqual(d, self.curso / "Semana 02" / "Teoría" / "Lecturas")
        self.assertEqual(list(self.curso.iterdir()), [])

    def test_modulo_sin_semana(self):
        d = destinos.carpeta_destino(self.curso, {"crear_secciones": True},
                                     self.item(None, "Sílabo: y anexo"), None, {})
        self.assertEqual(d, self.curso / "Sílabo- y anexo")

    def test_modo_lista(self):
        regla = {"modo": "lab_comunicacion", "subcarpeta_raiz": "Material de Laboratorio"}
        d = destinos.carpeta_destino(self.curso, regla, self.item("Material de laboratorio"), 7, {})
        self.assertEqual(d, self.curso / "Material de Laboratorio" / "Sem 7")


class Indice(unittest.TestCase):
    def setUp(self):
        self.curso = Path(tempfile.mkdtemp())
        (self.curso / "Sem 1" / "Teoría").mkdir(parents=True)
        (self.curso / "Sem 1" / "Lab").mkdir(parents=True)
        (self.curso / "Sem 1" / "Teoría" / "Clase.pptx").write_bytes(b"a" * 9000)
        (self.curso / "Sem 1" / "Teoría" / "Clase.md").write_bytes(b"m" * 7000)
        (self.curso / "Sem 1" / "enlace.url").write_bytes(b"u" * 260)

    def tearDown(self):
        shutil.rmtree(self.curso, ignore_errors=True)

    def test_reglas_para_no_saltar_de_mas(self):
        indice = destinos.IndiceCurso(self.curso)
        self.assertEqual(indice.buscar("clase.pptx")[0], "mismo nombre")
        self.assertIsNone(indice.buscar("Clase.pdf"), "otra extensión es otro archivo")
        self.assertIsNotNone(indice.buscar("otro.pdf", 9000), "mismos bytes aunque cambie el nombre")
        self.assertIsNone(indice.buscar("otro.pdf", 7000), "el peso de un .md no cuenta")
        self.assertIsNone(indice.buscar("otro.url", 260), "por debajo de 4 KB el peso no cuenta")
        self.assertIsNone(indice.buscar("otro.pdf", 9000, por_tamano=False))

    def test_teoria_y_lab(self):
        teoria = {"carpeta": "C", "subcarpeta_fija": "Teoría"}
        lab = {"carpeta": "C", "subcarpeta_fija": "Lab", "alias_subcarpeta": ["Laboratorio"]}

        def ajena_para_lab(ruta):
            return destinos.mitad_de(ruta, self.curso, [teoria, lab]) is teoria

        indice = destinos.IndiceCurso(self.curso)
        self.assertIsNone(indice.buscar("Clase.pptx", 12000, True, ajena_para_lab),
                          "mismo nombre en la otra mitad y otro tamaño: es otro material")
        self.assertEqual(indice.buscar("Clase.pptx", 9000, True, ajena_para_lab)[0], "mismo nombre y tamaño")
        self.assertIsNone(indice.buscar("Clase.pptx", None, True, ajena_para_lab),
                          "sin tamaño no se arriesga a saltarlo")
        self.assertIs(destinos.mitad_de(self.curso / "Sem 3" / "Teorìa" / "x", self.curso, [teoria, lab]),
                      teoria, "«Teorìa» con tilde grave también es Teoría")
        self.assertIsNone(destinos.mitad_de(self.curso / "x.pdf", self.curso, [teoria, lab]))


class Estructura(unittest.TestCase):
    CURSOS = [
        {"id": 1, "name": "Programación I (CS6002)  -  Teoría 1  -  2026 - 2"},
        {"id": 2, "name": "Programación I (CS6002)  -  Laboratorio 14  -  2026 - 2"},
        {"id": 3, "name": "Introducción a Ciencia de Datos (DS6001)  -  Teo. 1 - Lab. 11 - 2026 - 2"},
        {"id": 4, "name": "Peer Mentoring 2026-2"},
    ]

    def test_parejas_teoria_lab(self):
        grupos = estructura.agrupar([estructura.resumir(c, []) for c in self.CURSOS])
        por_tamano = sorted(([r.curso["id"] for r in g] for g in grupos), key=len, reverse=True)
        self.assertEqual(por_tamano[0], [1, 2], "teoría primero, luego el lab")
        self.assertIn([3], por_tamano, "un curso «Teo. - Lab.» es uno solo")

    def test_nombre_corto(self):
        self.assertEqual(estructura.nombre_corto(self.CURSOS[0]["name"]), "Programación I")
        self.assertEqual(estructura.nombre_corto("Peer Mentoring 2026-2"), "Peer Mentoring 2026-2")

    def test_resumen(self):
        modulos = [{"name": "Sílabo", "items": [{"type": "File", "title": "s.pdf", "content_id": 1}]},
                   {"name": "Semana 2", "items": [{"type": "SubHeader", "title": "Material de clase"},
                                                  {"type": "File", "title": "c.pdf", "content_id": 2},
                                                  {"type": "ExternalUrl", "title": "video"}]}]
        r = estructura.resumir(self.CURSOS[0], modulos)
        self.assertEqual((r.semanas, r.otros, r.archivos), ([2], ["Sílabo"], 2))
        self.assertEqual(r.secciones, Counter({"Material de clase": 1}))

    def test_emparejar_por_id_o_por_codigo(self):
        reglas = [{"canvas_id": 3}, {"codigo": "CS6002", "tipo": "laboratorio"}]
        parejas = estructura.emparejar_cursos(self.CURSOS, reglas)
        self.assertEqual([c["id"] for _, c in parejas], [3, 2])


class Sesion(unittest.TestCase):
    """El login no debe reventar si Canvas sigue redirigiendo cuando la sesión ya vale."""

    def setUp(self):
        self.perfil_original = sesion.PERFIL
        self.sync_original = sesion.sync_playwright
        self.espera_original = sesion.ESPERA_SSO
        sesion.ESPERA_SSO = 0.3  # no esperar 20 s de verdad
        sesion.PERFIL = Path(tempfile.mkdtemp()) / "perfil"
        (sesion.PERFIL / "Default").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(sesion.PERFIL.parent, ignore_errors=True)
        sesion.PERFIL = self.perfil_original
        sesion.sync_playwright = self.sync_original
        sesion.ESPERA_SSO = self.espera_original

    def navegador(self, *valida_tras):
        """Un Playwright falso: cada contexto da sesión válida tras N esperas."""
        abiertos, plan = [], list(valida_tras)

        class Pagina:
            navegando, esperas = False, 0

            def evaluate(self, _js):
                if self.navegando:
                    raise sesion.PlaywrightError("Execution context was destroyed")
                return "Mozilla/5.0"

            def goto(self, *_a, **_k):
                self.navegando = True

            def wait_for_timeout(self, _ms):
                self.esperas += 1

        class Contexto:
            def __init__(self, headless):
                self.headless, self.cerrado, self.tras = headless, False, plan.pop(0)
                self.pages = [Pagina()]
                pagina, tras = self.pages[0], self.tras
                self.request = type("R", (), {"get": lambda _s, *_a, **_k: type(
                    "Resp", (), {"status": 200 if pagina.esperas >= tras else 401})()})()

            def cookies(self):
                return [{"name": "sesion", "value": "x"}]

            def close(self):
                self.cerrado = True

        class Playwright:
            chromium = type("C", (), {"launch_persistent_context": lambda _s, **k: (
                abiertos.append(Contexto(k["headless"])) or abiertos[-1])})()

            def __enter__(self):
                return self

            def __exit__(self, *_a):
                return False

        sesion.sync_playwright = Playwright
        return abiertos

    def ctx(self):
        return type("Ctx", (), {"globos": [], "log": lambda s, *a: None,
                                "decir": lambda s, t: s.globos.append(t)})()

    def test_sin_ventana_aunque_la_pagina_siga_navegando(self):
        abiertos = self.navegador(2)
        cookies, ua = sesion.iniciar_sesion(self.ctx(), "https://canvas.ejemplo.edu")
        self.assertEqual(ua, "Mozilla/5.0")
        self.assertTrue(abiertos[0].headless and abiertos[0].cerrado)

    def test_con_ventana_cuando_hace_falta(self):
        abiertos = self.navegador(10 ** 9, 3)
        ctx = self.ctx()
        cookies, ua = sesion.iniciar_sesion(ctx, "https://canvas.ejemplo.edu", espera_login=60)
        self.assertEqual(len(ctx.globos), 2)
        self.assertTrue(all(c.cerrado for c in abiertos))
        self.assertFalse(abiertos[1].headless)


if __name__ == "__main__":
    unittest.main()
