"""Spec 015: descargas completas (Programación I), archivos repetidos por semana (AP),
material adicional y enlaces de Google Drive con cuenta institucional (DES-01…DES-06)."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PyQt6.QtWidgets import QApplication

from pandex.canvas import asistente, cliente, destinos, estructura, sesion
from pandex.config import Config
from pandex.markdown.clasificador import Clasificador
from pandex.ui.configuracion import DialogoConfiguracion
from tests.apoyo import CanvasFalso, ConCarpetaTemporal, modulo

APP = QApplication.instance() or QApplication([])


class DescargasCompletas(ConCarpetaTemporal):
    """DES-01: módulos con >10 ítems, secciones con decimales, cursos combinados y páginas/tareas."""

    def test_modulo_truncado_pide_items_url(self):
        c = cliente.Canvas("https://canvas.ejemplo.edu", [], "ua")
        diez = [{"type": "File", "title": f"a{i}.pdf", "content_id": i} for i in range(1, 11)]
        quince = [{"type": "File", "title": f"a{i}.pdf", "content_id": i} for i in range(1, 16)]
        respuestas = {
            "/courses/1/modules": [
                {"id": 10, "name": "Semana 1", "items_count": 15, "items": diez,
                 "items_url": "https://canvas.ejemplo.edu/api/v1/courses/1/modules/10/items"}
            ],
            "https://canvas.ejemplo.edu/api/v1/courses/1/modules/10/items": quince,
        }
        pedidos = []

        def api_falsa(ruta, _params=None):
            pedidos.append(ruta)
            return respuestas[ruta]

        with mock.patch.object(c, "api", side_effect=api_falsa):
            mods = c.modulos(1)
        self.assertEqual(len(mods[0]["items"]), 15, "pide items_url cuando items viene truncado")
        self.assertEqual(len(pedidos), 2)

    def test_parejas_y_emparejar_con_secciones_decimales_y_combinadas(self):
        cursos = [
            {"id": 1, "name": "Programación I (CS6002) - Teoría 1 - 2026 - 2"},
            {"id": 2, "name": "Programación I (CS6002) - Laboratorio 1.01 - 2026 - 2"},
            {"id": 3, "name": "Matemáticas Discretas I (CS6005) - Teo. 2 - Lab. 2.01 - 2026 - 2"},
        ]
        grupos = estructura.agrupar([estructura.resumir(c, []) for c in cursos])
        ids = sorted(([r.curso["id"] for r in g] for g in grupos), key=lambda x: (len(x), x))
        self.assertEqual(ids, [[3], [1, 2]], "Laboratorio 1.01 se empareja con Teoría 1")

        # Un curso combinado «Teo. 2 - Lab. 2.01» también coincide con una regla manual de teoría
        reglas = [{"codigo": "CS6005", "tipo": "teoria", "carpeta": "Discretas"}]
        parejas = estructura.emparejar_cursos(cursos, reglas)
        self.assertEqual([c["id"] for _, c in parejas], [3])

    def test_extrae_archivos_de_paginas_tareas_y_enlaces_externos(self):
        raiz = self.tmp / "Cursos"
        raiz.mkdir()
        CanvasFalso.reiniciar(
            cursos=[{"id": 1, "name": "Programación I (CS6002) - Teoría 1"}],
            modulos={
                1: [{
                    "name": "Semana 3",
                    "items": [
                        {"type": "SubHeader", "title": "Material de clase"},
                        {"type": "Page", "title": "Material de la semana", "page_url": "material-sem-3"},
                        {"type": "Assignment", "title": "Laboratorio 3", "content_id": 701},
                        {"type": "ExternalUrl", "title": "Recursión",
                         "external_url": "https://canvas.ejemplo.edu/courses/1/files/303/download"},
                    ],
                }]
            },
            archivos={
                301: ("Clase_3.pdf", 5000),
                302: ("Enunciado_Lab3.pdf", 6000),
                303: ("Recursion.py", 4500),
            },
        )
        CanvasFalso.paginas = {
            (1, "material-sem-3"): '<p><a href="https://canvas.ejemplo.edu/courses/1/files/301">Clase 3</a></p>',
        }
        CanvasFalso.tareas = {
            (1, 701): '<p><a href="/courses/1/files/302/download">Enunciado Lab 3</a></p>',
        }
        params = {
            "canvas_url": "https://canvas.ejemplo.edu",
            "destino": str(raiz),
            "estilo_carpetas": "guiones_bajos",
            "cursos": [{"canvas_id": 1, "carpeta": "Programacion_I", "crear_secciones": True}],
        }
        r, _ = self.sincronizar(params)
        self.assertTrue(r["ok"], r)
        sem3 = raiz / "Programacion_I" / "Sem_3" / "Material_de_clase"
        self.assertTrue((sem3 / "Clase 3.pdf").exists())
        self.assertTrue((sem3 / "Enunciado Lab 3.pdf").exists())
        self.assertTrue((sem3 / "Recursión.py").exists())


class NombresGenericosPorSemana(ConCarpetaTemporal):
    """DES-02: archivos con el mismo nombre genérico en distintas semanas o en la misma carpeta."""

    def test_archivos_con_mismo_nombre_y_distinto_tamano_en_distintas_semanas_se_bajan_todos(self):
        raiz = self.tmp / "Cursos"
        sem1_teo = raiz / "Programacion_I" / "Sem_1" / "Teoria" / "Material_de_clase"
        sem1_teo.mkdir(parents=True)
        # Ya tenías Ejercicios.pdf en Sem 1 antes de usar Pandex (no está en el historial)
        (sem1_teo / "Ejercicios.pdf").write_bytes(b"a" * 5000)

        CanvasFalso.reiniciar(
            cursos=[{"id": 1, "name": "Programación I (CS6002) - Teoría 1"}],
            modulos={
                1: [
                    modulo("Semana 1", ("sub", "Material de clase"),
                           ("file", "Ejercicios.pdf", 101), ("file", "Guia.pdf", 102)),
                    modulo("Semana 2", ("sub", "Material de clase"),
                           ("file", "Ejercicios.pdf", 201), ("file", "Guia.pdf", 202)),
                    modulo("Semana 3", ("sub", "Material de clase"),
                           ("file", "Ejercicios.pdf", 301)),
                ]
            },
            archivos={
                101: ("Ejercicios.pdf", 5000),
                102: ("Guia.pdf", 6000),
                201: ("Ejercicios.pdf", 8500),
                202: ("Guia.pdf", 9200),
                301: ("Ejercicios.pdf", 7100),
            },
        )
        params = {
            "canvas_url": "https://canvas.ejemplo.edu",
            "destino": str(raiz),
            "estilo_carpetas": "guiones_bajos",
            "cursos": [{"canvas_id": 1, "carpeta": "Programacion_I", "subcarpeta_fija": "Teoría",
                        "crear_secciones": True}],
        }
        r, _ = self.sincronizar(params)
        self.assertTrue(r["ok"], r)
        prog = raiz / "Programacion_I"
        self.assertEqual((prog / "Sem_1" / "Teoria" / "Material_de_clase" / "Ejercicios.pdf").stat().st_size, 5000)
        self.assertEqual((prog / "Sem_1" / "Teoria" / "Material_de_clase" / "Guia.pdf").stat().st_size, 6000)
        self.assertEqual((prog / "Sem_2" / "Teoria" / "Material_de_clase" / "Ejercicios.pdf").stat().st_size, 8500)
        self.assertEqual((prog / "Sem_2" / "Teoria" / "Material_de_clase" / "Guia.pdf").stat().st_size, 9200)
        self.assertEqual((prog / "Sem_3" / "Teoria" / "Material_de_clase" / "Ejercicios.pdf").stat().st_size, 7100)

    def test_dos_archivos_distintos_con_mismo_nombre_en_la_misma_carpeta_en_una_corrida(self):
        raiz = self.tmp / "Cursos"
        raiz.mkdir()
        CanvasFalso.reiniciar(
            cursos=[{"id": 1, "name": "Programación I (CS6002) - Teoría 1"}],
            modulos={
                1: [modulo("Semana 1", ("sub", "Material de clase"),
                           ("file", "Codigo.py", 111), ("file", "Codigo.py", 112))]
            },
            archivos={111: ("Codigo.py", 4500), 112: ("Codigo.py", 6200)},
        )
        params = {
            "canvas_url": "https://canvas.ejemplo.edu",
            "destino": str(raiz),
            "estilo_carpetas": "guiones_bajos",
            "cursos": [{"canvas_id": 1, "carpeta": "Programacion_I", "crear_secciones": True}],
        }
        r, _ = self.sincronizar(params)
        self.assertTrue(r["ok"], r)
        carpeta = raiz / "Programacion_I" / "Sem_1" / "Material_de_clase"
        self.assertEqual((carpeta / "Codigo.py").stat().st_size, 4500)
        self.assertEqual((carpeta / "Codigo (v2).py").stat().st_size, 6200)


class ArchivosRepetidosPorSemana(ConCarpetaTemporal):
    """DES-03: elegir si descargar archivos idénticos repetidos cada semana (p. ej. AP en Cálculo)."""

    def setUp(self):
        super().setUp()
        self.raiz = self.tmp / "Cursos"
        self.raiz.mkdir()
        # En Semana 1 y Semana 2 es el mismo file_id (401); en Semana 3 el docente volvió a subir el
        # mismo PDF con otro file_id (403) pero idéntico nombre y tamaño (7000 bytes).
        CanvasFalso.reiniciar(
            cursos=[{"id": 3, "name": "Fundamentos del Cálculo (CC6101) - Teoría 4"}],
            modulos={
                3: [
                    modulo("Semana 1", ("sub", "Actividades"), ("file", "AP.pdf", 401)),
                    modulo("Semana 2", ("sub", "Actividades"), ("file", "AP.pdf", 401)),
                    modulo("Semana 3", ("sub", "Actividades"), ("file", "AP.pdf", 403)),
                ]
            },
            archivos={401: ("AP.pdf", 7000), 403: ("AP.pdf", 7000)},
        )
        self.params = {
            "canvas_url": "https://canvas.ejemplo.edu",
            "destino": str(self.raiz),
            "estilo_carpetas": "guiones_bajos",
            "cursos": [{"canvas_id": 3, "carpeta": "Fundamentos_de_Calculo", "crear_secciones": True}],
        }

    def test_repetidos_solo_una_vez_por_defecto(self):
        r, _ = self.sincronizar(self.params)
        self.assertTrue(r["ok"], r)
        calc = self.raiz / "Fundamentos_de_Calculo"
        self.assertTrue((calc / "Sem_1" / "Actividades" / "AP.pdf").exists())
        self.assertFalse((calc / "Sem_2" / "Actividades" / "AP.pdf").exists())
        self.assertFalse((calc / "Sem_3" / "Actividades" / "AP.pdf").exists())

    def test_repetidos_cada_semana_descarga_en_todas_las_semanas(self):
        self.params["repetidos_cada_semana"] = True
        r, _ = self.sincronizar(self.params)
        self.assertTrue(r["ok"], r)
        calc = self.raiz / "Fundamentos_de_Calculo"
        for sem in ("Sem_1", "Sem_2", "Sem_3"):
            with self.subTest(semana=sem):
                self.assertEqual((calc / sem / "Actividades" / "AP.pdf").stat().st_size, 7000)

        # En la siguiente corrida ya están todos en su semana: 0 consultas y 0 descargas
        r2, _ = self.sincronizar(self.params)
        self.assertTrue(r2["resumen"].startswith("✓ Todo al día"), r2["resumen"])
        self.assertEqual(CanvasFalso.llamadas["descargar"], 0)
        self.assertEqual(CanvasFalso.llamadas["archivo"], 0)

    def test_elegir_repetidos_en_asistente_y_configuracion(self):
        # 1. En el asistente (PaginaDescarga)
        estado = asistente.Estado({})
        pagina = asistente.PaginaDescarga(estado)
        pagina.initializePage()
        indice_siempre = pagina.repetidos.findData(True)
        self.assertGreaterEqual(indice_siempre, 0)
        pagina.repetidos.setCurrentIndex(indice_siempre)
        self.assertTrue(pagina.validatePage())
        self.assertTrue(estado.repetidos_cada_semana)

        # 2. En Configuración -> Tareas -> Sincronizar Canvas
        cfg = Config(self.tmp / "config.json", copia=None)
        tarea_fake = type("T", (), {"id": "sync_canvas", "nombre": "Sincronizar Canvas", "descripcion": "",
                                    "schedule": None, "programable": True})()
        dlg = DialogoConfiguracion(cfg, [tarea_fake])
        self.assertFalse(dlg.repetidos_canvas.currentData())
        dlg.repetidos_canvas.setCurrentIndex(dlg.repetidos_canvas.findData(True))
        dlg._guardar()
        self.assertTrue(cfg.tarea("sync_canvas")["repetidos_cada_semana"])


class MaterialAdicional(ConCarpetaTemporal):
    """DES-04: descargar material adicional en modo clásico y del asistente, y clasificarlo en Markdown."""

    def test_descarga_subencabezado_y_modulo_material_adicional_en_modo_clasico(self):
        raiz = self.tmp / "Ciclo"
        raiz.mkdir()
        CanvasFalso.reiniciar(
            cursos=[
                {"id": 1, "name": "Programación I (CS6002) - Teoría 1"},
                {"id": 3, "name": "Fundamentos del Cálculo (CC6101) - Teoría 4"},
            ],
            modulos={
                1: [
                    modulo("Material adicional", ("file", "Referencia_Python.pdf", 501)),
                    modulo("Semana 6", ("sub", "Material adicional"), ("file", "CheatSheet.pdf", 502),
                           ("sub", "Material complementario"), ("file", "Ejemplos_Extra.pdf", 503)),
                ],
                3: [
                    modulo("Semana 6", ("file", "Guia_Suelta.pdf", 601),
                           ("sub", "Material adicional"), ("file", "Formulario.pdf", 602)),
                ],
            },
            archivos={
                501: ("Referencia_Python.pdf", 5000),
                502: ("CheatSheet.pdf", 5200),
                503: ("Ejemplos_Extra.pdf", 5400),
                601: ("Guia_Suelta.pdf", 5600),
                602: ("Formulario.pdf", 5800),
            },
        )
        # Configuración clásica: secciones solo nombra material de clase y actividades, y no trae
        # crear_secciones ni otros_modulos
        params = {
            "canvas_url": "https://canvas.ejemplo.edu",
            "destino": str(raiz),
            "estilo_carpetas": "guiones_bajos",
            "secciones": {"material de clase": "Material de clase", "actividades": "Actividades"},
            "cursos": [
                {"codigo": "CS6002", "tipo": "teoria", "carpeta": "Programacion_I",
                 "subcarpeta_fija": "Teoría", "alias": "Programación"},
                {"codigo": "CC6101", "carpeta": "Calculo", "alias": "Cálculo"},
            ],
        }
        r, _ = self.sincronizar(params)
        self.assertTrue(r["ok"], r)
        prog = raiz / "Programacion_I"
        calc = raiz / "Calculo"
        self.assertTrue((prog / "Material_adicional" / "Referencia_Python.pdf").exists())
        self.assertTrue((prog / "Sem_6" / "Teoria" / "Material_adicional" / "CheatSheet.pdf").exists())
        self.assertTrue((prog / "Sem_6" / "Teoria" / "Material_adicional" / "Ejemplos_Extra.pdf").exists())
        self.assertTrue((calc / "Sem_6" / "Guia_Suelta.pdf").exists())
        self.assertTrue((calc / "Sem_6" / "Material_adicional" / "Formulario.pdf").exists())

    def test_clasificador_reconoce_material_adicional(self):
        clasificador = Clasificador()
        self.assertTrue(clasificador.clasificar(Path("C:/Curso/Sem 3/Material adicional/Extra.pdf"))[0])
        self.assertTrue(clasificador.clasificar(Path("C:/Curso/Material_complementario_2.pdf"))[0])
        self.assertTrue(clasificador.clasificar(Path("C:/Curso/Supplementary_Material.pdf"))[0])


class GoogleDriveDescarga(ConCarpetaTemporal):
    """DES-05: descargar archivos y documentos de Google Drive enlazados en módulos y páginas."""

    def test_descarga_enlaces_de_drive_y_docs_en_modulos_y_paginas(self):
        from pandex.canvas import drive

        raiz = self.tmp / "Cursos"
        raiz.mkdir()
        CanvasFalso.reiniciar(
            cursos=[{"id": 1, "name": "Programación I (CS6002) - Teoría 1"}],
            modulos={
                1: [{
                    "name": "Semana 4",
                    "items": [
                        {"type": "SubHeader", "title": "Material de clase"},
                        {"type": "ExternalUrl", "title": "Guia Drive",
                         "external_url": "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrSt/view?usp=sharing"},
                        {"type": "ExternalUrl", "title": "Apuntes Doc",
                         "external_url": "https://docs.google.com/document/d/2DocId1234567890/edit"},
                        {"type": "ExternalUrl", "title": "Diapositivas.pptx",
                         "external_url": "https://docs.google.com/presentation/d/3SlideId123456789/edit"},
                        {"type": "ExternalUrl", "title": "Datos Lab",
                         "external_url": "https://docs.google.com/spreadsheets/d/4SheetId123456789/edit"},
                        {"type": "Page", "title": "Material adicional", "page_url": "drive-extra"},
                    ],
                }]
            },
            archivos={},
        )
        CanvasFalso.paginas = {
            (1, "drive-extra"): (
                '<a href="https://drive.google.com/open?id=5GrandeId123456789">Archivo Grande</a>'
            ),
        }

        def respuesta_drive(url, **_k):
            resp = mock.MagicMock()
            resp.status_code = 200
            resp.url = url
            if "1AbCdEfGhIjKlMnOpQrSt" in url:
                cuerpo = b"%PDF-1.4 guia" * 500
                resp.headers = {
                    "Content-Type": "application/pdf",
                    "Content-Disposition": 'attachment; filename="Guia_real.pdf"',
                }
            elif "2DocId1234567890" in url:
                cuerpo = b"%PDF-1.4 doc" * 500
                resp.headers = {
                    "Content-Type": "application/pdf",
                    "Content-Disposition": "attachment; filename*=UTF-8''Apuntes%20Doc.pdf",
                }
            elif "3SlideId123456789" in url:
                cuerpo = b"PK\x03\x04 pptx" * 500
                resp.headers = {
                    "Content-Type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    "Content-Disposition": 'attachment; filename="Slides.pptx"',
                }
            elif "4SheetId123456789" in url:
                cuerpo = b"PK\x03\x04 xlsx" * 500
                resp.headers = {
                    "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "Content-Disposition": 'attachment; filename="Datos.xlsx"',
                }
            elif "5GrandeId123456789" in url and "confirm=" not in url:
                # Primera respuesta de Drive para archivos grandes: página HTML de confirmación
                cuerpo = (
                    b'<html><body><form id="download-form" '
                    b'action="https://drive.usercontent.google.com/download" method="get">'
                    b'<input type="hidden" name="id" value="5GrandeId123456789">'
                    b'<input type="hidden" name="confirm" value="t">'
                    b'<input type="hidden" name="uuid" value="uuid-123">'
                    b'</form></body></html>'
                )
                resp.headers = {"Content-Type": "text/html; charset=utf-8"}
            else:
                cuerpo = b"PK\x03\x04 zip grande" * 600
                resp.headers = {
                    "Content-Type": "application/zip",
                    "Content-Disposition": 'attachment; filename="proyecto.zip"',
                }
            resp.iter_content = lambda _n=65536: [cuerpo]
            resp.text = cuerpo.decode("utf-8", "replace")
            resp.__enter__.return_value = resp
            return resp

        params = {
            "canvas_url": "https://canvas.ejemplo.edu",
            "destino": str(raiz),
            "estilo_carpetas": "guiones_bajos",
            "cursos": [{"canvas_id": 1, "carpeta": "Programacion_I", "crear_secciones": True}],
        }
        with mock.patch.object(drive, "_http_get", side_effect=respuesta_drive):
            r, _ = self.sincronizar(params)
        self.assertTrue(r["ok"], r)
        sem4 = raiz / "Programacion_I" / "Sem_4"
        self.assertTrue((sem4 / "Material_de_clase" / "Guia Drive.pdf").exists())
        self.assertTrue((sem4 / "Material_de_clase" / "Apuntes Doc.pdf").exists())
        self.assertTrue((sem4 / "Material_de_clase" / "Diapositivas.pptx").exists())
        self.assertTrue((sem4 / "Material_de_clase" / "Datos Lab.xlsx").exists())
        self.assertTrue((sem4 / "Material_adicional" / "Archivo Grande.zip").exists())

        # Segunda sincronización: ya están en el historial, no vuelve a descargar
        with mock.patch.object(drive, "_http_get", side_effect=AssertionError("no debía volver a bajar")):
            r2, _ = self.sincronizar(params)
        self.assertTrue(r2["resumen"].startswith("✓ Todo al día"), r2["resumen"])


class GoogleDriveCuentaInstitucional(ConCarpetaTemporal):
    """DES-06: cuando la cuenta predeterminada no es la institucional, prueba authuser o abre el navegador."""

    def setUp(self):
        super().setUp()
        from pandex.canvas import drive

        self.drive = drive
        self.atajo_original = drive.ATAJO_DRIVE
        drive.ATAJO_DRIVE = self.tmp / "sesion_drive.json"
        self.addCleanup(setattr, drive, "ATAJO_DRIVE", self.atajo_original)

    def test_si_la_cuenta_predeterminada_rebota_prueba_authuser_1_sin_abrir_ventana(self):
        self.drive.guardar_atajo_drive(
            [{"name": "SID", "value": "COOKIE_GOOGLE_SECRETA", "domain": ".google.com", "path": "/"}],
            "UA-Test",
            authuser=0,
        )
        pedidos = []

        def respuesta(url, **_k):
            pedidos.append(url)
            resp = mock.MagicMock()
            resp.url = url
            if "authuser=1" not in url:
                # authuser=0 es la cuenta personal: Google Drive devuelve "Necesitas acceso"
                cuerpo = b"<html><title>Necesitas acceso - Google Drive</title><body>Cambiar de cuenta</body></html>"
                resp.status_code = 200
                resp.headers = {"Content-Type": "text/html; charset=utf-8"}
            else:
                # authuser=1 es la cuenta institucional: descarga el archivo
                cuerpo = b"%PDF-1.4 institucional" * 400
                resp.status_code = 200
                resp.headers = {
                    "Content-Type": "application/pdf",
                    "Content-Disposition": 'attachment; filename="Guia_UTEC.pdf"',
                }
            resp.iter_content = lambda _n=65536: [cuerpo]
            resp.text = cuerpo.decode("utf-8", "replace")
            resp.__enter__.return_value = resp
            return resp

        destino = self.tmp / "archivo.part"
        with mock.patch.object(self.drive, "_http_get", side_effect=respuesta), \
                mock.patch.object(self.drive, "iniciar_sesion_drive",
                                  side_effect=AssertionError("no debía abrir ventana")):
            nombre_real, escritos = self.drive.descargar(
                "https://drive.google.com/file/d/1InstId999/view", destino
            )
        self.assertEqual(nombre_real, "Guia_UTEC.pdf")
        self.assertGreater(escritos, 0)
        guardado = json.loads(self.drive.ATAJO_DRIVE.read_text(encoding="utf-8"))
        self.assertEqual(guardado["authuser"], 1, "recuerda que la cuenta 1 es la institucional")

    def test_abre_el_navegador_para_cambiar_a_cuenta_institucional_y_olvida_sesion(self):
        abrio_ventana = []

        def login_manual(ctx, info, navegador="auto", espera_login=300):
            abrio_ventana.append(info["id"])
            if ctx:
                ctx.decir("Google Drive pide tu cuenta institucional")
            galletas = [{"name": "SID", "value": "SID_INSTITUCIONAL_99", "domain": ".google.com", "path": "/"}]
            self.drive.guardar_atajo_drive(galletas, "UA-Inst", authuser=1)
            return galletas, "UA-Inst", 1

        def respuesta(url, cookies=None, **_k):
            resp = mock.MagicMock()
            resp.url = url
            if not cookies or cookies.get("SID") != "SID_INSTITUCIONAL_99" or "authuser=1" not in url:
                cuerpo = b"<html><body>You need access. Switch to your institutional account.</body></html>"
                resp.status_code = 403
                resp.headers = {"Content-Type": "text/html; charset=utf-8"}
            else:
                cuerpo = b"%PDF-1.4 bajado tras cambiar de cuenta" * 300
                resp.status_code = 200
                resp.headers = {
                    "Content-Type": "application/pdf",
                    "Content-Disposition": 'attachment; filename="Lab_Drive.pdf"',
                }
            resp.iter_content = lambda _n=65536: [cuerpo]
            resp.text = cuerpo.decode("utf-8", "replace")
            resp.__enter__.return_value = resp
            return resp

        raiz = self.tmp / "Cursos"
        raiz.mkdir()
        CanvasFalso.reiniciar(
            cursos=[{"id": 1, "name": "Programación I (CS6002) - Teoría 1"}],
            modulos={
                1: [{
                    "name": "Semana 5",
                    "items": [
                        {"type": "SubHeader", "title": "Material de clase"},
                        {"type": "ExternalUrl", "title": "Lab en Drive",
                         "external_url": "https://drive.google.com/file/d/1PrivadoUTEC/view"},
                    ],
                }]
            },
            archivos={},
        )
        params = {
            "canvas_url": "https://canvas.ejemplo.edu",
            "destino": str(raiz),
            "estilo_carpetas": "guiones_bajos",
            "cursos": [{"canvas_id": 1, "carpeta": "Programacion_I", "crear_secciones": True}],
        }
        with mock.patch.object(self.drive, "_http_get", side_effect=respuesta), \
                mock.patch.object(self.drive, "iniciar_sesion_drive", side_effect=login_manual):
            r, ctx = self.sincronizar(params)

        self.assertTrue(r["ok"], r)
        self.assertEqual(abrio_ventana, ["1PrivadoUTEC"])
        self.assertTrue((raiz / "Programacion_I" / "Sem_5" / "Material_de_clase" / "Lab en Drive.pdf").exists())
        self.assertTrue(any("cuenta institucional" in g for g in ctx.globos))
        if os.name != "nt":
            self.assertEqual(os.stat(self.drive.ATAJO_DRIVE).st_mode & 0o777, 0o600)

        # «Olvidar mi sesión» también borra la sesión guardada de Google Drive
        sesion.olvidar()
        self.assertFalse(self.drive.ATAJO_DRIVE.exists())

    def test_iniciar_sesion_drive_detecta_authuser_en_url_y_guarda_cookies(self):
        from pandex.canvas import navegador

        class PaginaFalsa:
            url = "https://drive.google.com/drive/u/2/folders/xyz"

            def goto(self, *_a, **_k):
                pass

            def wait_for_timeout(self, _ms):
                pass

            def evaluate(self, _js):
                return "Guia_UTEC.pdf - Google Drive"

        class ContextoFalso:
            pages = [PaginaFalsa()]

            def user_agent(self):
                return "Mozilla/5.0 Test"

            def cookies(self):
                return [{"name": "SID", "value": "SID_U2", "domain": ".google.com", "path": "/"}]

            def close(self):
                pass

        info = {"tipo": "file", "id": "1AbCdEfGhIjKl", "url": "https://drive.google.com/file/d/1AbCdEfGhIjKl/view"}
        with mock.patch.object(navegador, "elegir", return_value="firefox"), \
                mock.patch.object(navegador, "abrir", return_value=ContextoFalso()):
            cookies, ua, authuser = self.drive.iniciar_sesion_drive(None, info, navegador="firefox")
        self.assertEqual(authuser, 2)
        self.assertEqual(ua, "Mozilla/5.0 Test")
        self.assertEqual(cookies[0]["value"], "SID_U2")


if __name__ == "__main__":
    unittest.main()
