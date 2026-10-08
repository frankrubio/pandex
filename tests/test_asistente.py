"""El asistente de configuración de punta a punta, en una pantalla invisible."""

import time
import unittest

from PyQt6.QtWidgets import QApplication

from pandex.canvas import adoptar, asistente
from tests.apoyo import CanvasFalso, ConCarpetaTemporal, modulo

APP = QApplication.instance() or QApplication([])


class Mensajes:
    """Reemplaza a QMessageBox: los diálogos modales trabarían la prueba."""

    StandardButton = asistente.QMessageBox.StandardButton
    vistos = []

    @classmethod
    def _anotar(cls, *args, **_k):
        cls.vistos.append(args[1] if len(args) > 1 else "")
        return cls.StandardButton.Yes

    information = warning = critical = question = _anotar


def esperar(condicion, segundos=10):
    limite = time.monotonic() + segundos
    while not condicion():
        if time.monotonic() > limite:
            raise AssertionError("se acabó el tiempo esperando al asistente")
        APP.processEvents()
        time.sleep(0.01)


class Asistente(ConCarpetaTemporal):
    def setUp(self):
        super().setUp()
        self._propios = (asistente.Canvas, asistente.QMessageBox)  # la sesión falsa la pone la base
        asistente.Canvas = CanvasFalso
        asistente.QMessageBox = Mensajes
        Mensajes.vistos = []
        CanvasFalso.reiniciar(
            cursos=[
                {"id": 1, "name": "Programación I (CS6002) - Teoría 1 - 2026 - 2"},
                {"id": 2, "name": "Programación I (CS6002) - Laboratorio 14 - 2026 - 2"},
                {"id": 3, "name": "Peer Mentoring 2026-2"},
            ],
            modulos={
                1: [modulo("Semana 1", ("sub", "Material de clase"), ("file", "Clase 1.pdf", 11)),
                    modulo("Semana 2", ("sub", "Material de clase"), ("file", "Clase 2.pdf", 12))],
                2: [modulo("Semana 1", ("file", "Lab 1.pdf", 21))],
                3: [modulo("Bienvenida", ("file", "Guía.pdf", 31))],
            },
            archivos={11: ("Clase 1.pdf", 5000), 12: ("Clase 2.pdf", 5100), 21: ("Lab 1.pdf", 5200),
                      31: ("Guía.pdf", 5300)},
        )
        self.guardado = []
        self.params = {}

    def tearDown(self):
        asistente.Canvas, asistente.QMessageBox = self._propios
        super().tearDown()

    def recorrer_hasta_carpeta(self):
        w = asistente.AsistenteCanvas(self.params, lambda: self.guardado.append(True))
        w.show()
        w.page(asistente.BIENVENIDA).url.setText("canvas.ejemplo.edu")
        w.next()
        esperar(lambda: w.currentId() == asistente.CURSOS)
        self.assertEqual(w.estado.url, "https://canvas.ejemplo.edu", "completa el https://")
        grupos = w.estado.grupos
        self.assertEqual([len(g.resumenes) for g in grupos], [2, 1], "teoría y lab juntos")
        self.assertEqual([g.elegido for g in grupos], [True, False], "propone los cursos por semanas")
        w.next()
        return w

    def test_carpeta_nueva(self):
        w = self.recorrer_hasta_carpeta()
        carpeta = w.page(asistente.CARPETA)
        carpeta.padre.setText(str(self.tmp))
        carpeta.nombre.setText("Mis cursos")
        w.next()
        self.assertEqual(w.currentId(), asistente.DESCARGA)
        descarga = w.page(asistente.DESCARGA)
        descarga.desde.setChecked(True)
        descarga.semana.setValue(2)
        descarga.programar.setChecked(True)
        w.next()
        self.assertEqual(w.currentId(), asistente.LISTO)
        w.accept()

        raiz = self.tmp / "Mis cursos"
        self.assertEqual(self.guardado, [True])
        self.assertEqual(w.entrada, {"inicial": "desde", "desde_semana": 2})
        self.assertEqual(self.params["destino"], str(raiz))
        self.assertEqual(self.params["schedule"], "0 19 * * *")
        reglas = self.params["cursos"]
        self.assertEqual([(r["canvas_id"], r.get("subcarpeta_fija")) for r in reglas],
                         [(1, "Teoría"), (2, "Lab")])
        self.assertTrue((raiz / "Programación I" / "Sem 1" / "Teoría").is_dir(), "arma el esqueleto")
        self.assertTrue((raiz / "Programación I" / "Sem 1" / "Lab").is_dir())

        # y la primera sincronización respeta lo elegido
        r, _ = self.sincronizar(self.params, w.entrada)
        self.assertTrue((raiz / "Programación I" / "Sem 2" / "Teoría" / "Material de clase" / "Clase 2.pdf").exists())
        self.assertFalse((raiz / "Programación I" / "Sem 1" / "Teoría" / "Material de clase").exists(),
                         "la semana 1 quedó fuera por elección")

    def test_carpeta_existente_se_ordena_y_se_puede_deshacer(self):
        prog = self.tmp / "Cursos" / "Programacion_I"
        (prog / "Semana 01" / "Laboratorio").mkdir(parents=True)
        (prog / "Clase 1.pdf").write_bytes(b"x" * 5000)       # de Canvas, suelto en la raíz del curso
        (prog / "Mis notas.docx").write_bytes(b"n" * 300)     # tuyo

        w = self.recorrer_hasta_carpeta()
        carpeta = w.page(asistente.CARPETA)
        carpeta.existente.setChecked(True)
        carpeta.ruta_existente.setText(str(self.tmp / "Cursos"))
        w.next()
        self.assertEqual(w.currentId(), asistente.ADOPTAR)
        adoptar_pagina = w.page(asistente.ADOPTAR)
        self.assertEqual(adoptar_pagina.combos[0].currentText(), "Programacion_I", "empareja solo")
        conv = w.estado.convenciones
        self.assertEqual((conv.formato_semana, conv.lab), ("Semana {n:02d}", "Laboratorio"), "lee tu estilo")

        w.next()
        self.assertEqual(w.currentId(), asistente.REORDENAR)
        esperar(lambda: w.estado.plan is not None)
        reordenar = w.page(asistente.REORDENAR)
        self.assertEqual(len(w.estado.plan.movimientos), 1)
        reordenar.confirmar.setChecked(True)
        w.next()
        w.page(asistente.DESCARGA).todo.setChecked(True)
        w.next()
        w.accept()

        movido = prog / "Semana 01" / "Teoría" / "Material de clase" / "Clase 1.pdf"
        self.assertTrue(movido.exists(), "el archivo de Canvas fue a su lugar, con tu estilo")
        self.assertTrue((prog / "Mis notas.docx").exists(), "lo tuyo no se toca")
        self.assertEqual(self.params["formato_semana"], "Semana {n:02d}")
        self.assertEqual(self.params["cursos"][1]["subcarpeta_fija"], "Laboratorio")

        devueltos, _ = adoptar.deshacer()
        self.assertEqual(devueltos, 1)
        self.assertTrue((prog / "Clase 1.pdf").exists())

    def test_si_falla_el_login_se_puede_reintentar(self):
        def falla(*_a, **_k):
            raise asistente.CanvasError("Cerraste el navegador antes de terminar de iniciar sesión.")

        asistente.sesion.iniciar_sesion = falla
        w = asistente.AsistenteCanvas(self.params, lambda: None)
        w.show()
        w.next()
        pagina = w.page(asistente.CONECTAR)
        esperar(lambda: pagina.reintentar.isVisible())
        self.assertIn("Cerraste el navegador", pagina.mensaje.text())
        self.assertFalse(pagina.isComplete())


    def test_cancelar_mientras_inicia_sesion_no_tumba_la_app(self):
        import threading

        suelta = threading.Event()

        def lento(*_a, **_k):
            suelta.wait(5)  # el navegador esperando que entres
            return [], "ua"

        asistente.sesion.iniciar_sesion = lento
        w = asistente.AsistenteCanvas(self.params, lambda: None)
        w.show()
        w.next()
        w.reject()
        del w  # sin el arreglo, Qt abortaba aquí: «QThread destroyed while still running»
        APP.processEvents()
        self.assertEqual(len(asistente._EN_CURSO), 1)
        suelta.set()
        esperar(lambda: not asistente._EN_CURSO)


if __name__ == "__main__":
    unittest.main()
