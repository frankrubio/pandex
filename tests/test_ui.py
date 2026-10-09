"""La interfaz se construye y se pinta sin errores (ventanas invisibles, sin internet)."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from pandex.config import Config  # noqa: E402
from pandex.ui import tema  # noqa: E402

app = QApplication.instance() or QApplication([])


class Interfaz(unittest.TestCase):
    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())
        self.config = Config(self.carpeta / "config.json")
        tema.aplicar(app)

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def test_cada_personaje_un_cuadro_fijo_por_estado(self):
        from pandex.ui import personajes

        todos = personajes.catalogo()
        self.assertEqual(next(iter(todos)), "rusty", "Rusty va primero")
        for esperado in ("rusty", "bmo", "robot", "panda_clasico"):
            self.assertIn(esperado, todos)
        for ident, p in todos.items():
            self.assertTrue(p.icono.exists(), f"falta {ident}/icono.ico")
            for estado in personajes.ESTADOS:
                pix = personajes.imagen(ident, estado, 126)
                self.assertFalse(pix.isNull())
                self.assertLessEqual(pix.height(), 126)
                self.assertIs(pix, personajes.imagen(ident, estado, 126), "la segunda vez sale de la caché")
            self.assertFalse(personajes.cabeza(ident).isNull())
        pix = personajes.imagen("rusty", "idle", 126, 1.5)
        self.assertEqual(pix.devicePixelRatio(), 1.5)

    def test_un_personaje_que_no_existe_cae_en_rusty(self):
        from pandex.ui import personajes
        from pandex.ui.mascota import Mascota

        self.assertEqual(personajes.elegir("vectorial").id, "rusty")
        self.config.mascota["personaje"] = "no_existe"
        self.assertEqual(Mascota(self.config).personaje, "rusty")

    def test_el_logo_sigue_al_personaje_o_queda_fijo(self):
        from pandex.ui import logo

        self.assertEqual(logo.elegido({"personaje": "bmo"}), "bmo")
        self.assertEqual(logo.elegido({"personaje": "bmo", "logo": "personaje"}), "bmo")
        self.assertEqual(logo.elegido({"personaje": "bmo", "logo": "robot"}), "robot")
        self.assertEqual(logo.elegido({"personaje": "pixel", "logo": "no_existe"}), "rusty")
        self.assertFalse(logo.icono("bmo").isNull())
        self.assertFalse(logo.pixmap(48, ident="robot").isNull())

    def test_el_acceso_directo_usa_el_icono_del_logo_elegido(self):
        import json
        from unittest import mock

        from pandex import accesos

        ruta = self.carpeta / "config.json"
        casos = [({"personaje": "bmo"}, "bmo"), ({"personaje": "bmo", "logo": "robot"}, "robot"),
                 ({"personaje": "../../algo"}, None), ({}, None)]
        for mascota, esperado in casos:
            ruta.write_text(json.dumps({"mascota": mascota}), encoding="utf-8")
            with mock.patch.object(accesos, "CONFIG_FILE", ruta):
                ico = accesos.icono_elegido()
            self.assertEqual(ico.parent.name if esperado else ico, esperado or accesos.ICONO)

    def test_la_mascota_es_estatica(self):
        from PyQt6.QtCore import QTimer

        from pandex.ui.mascota import Mascota

        m = Mascota(self.config)
        m.show()
        m.set_estado("trabajando")
        activos = [t for t in m.findChildren(QTimer) if t.isActive()]
        self.assertEqual(activos, [], "en reposo o trabajando no corre ningún temporizador")
        m.set_estado("feliz", 1.5)
        self.assertEqual(len([t for t in m.findChildren(QTimer) if t.isActive()]), 1,
                         "solo el disparo único que la devuelve al reposo")
        m.grab()
        m.close()

    def test_dialogos(self):
        from pandex.ui.configuracion import DialogoConfiguracion
        from pandex.ui.informe import DialogoInforme
        from pandex.ui.visor_registro import VisorRegistro

        for dlg in (DialogoConfiguracion(self.config, []), DialogoInforme("Prueba", "línea 1\nlínea 2"),
                    VisorRegistro()):
            self.assertFalse(dlg.grab().isNull())

    def test_actualizar_con_un_clic_aplica_y_reinicia_solo(self):
        from PyQt6.QtCore import QEventLoop, QTimer

        from pandex import actualizar
        from pandex.ui.actualizacion import DialogoActualizacion

        original = actualizar.aplicar
        actualizar.aplicar = lambda avisar=None, **_k: {"modo": "zip", "archivos": 3, "respaldo": None}
        reinicios = []
        try:
            info = {"local": "2.1.0", "remota": "2.2.0", "hay_nueva": True, "novedades": "## 2.2.0"}
            dlg = DialogoActualizacion(lambda: reinicios.append(1), info=info, aplicar_ya=True)
            espera = QEventLoop()
            QTimer.singleShot(2500, espera.quit)
            espera.exec()
        finally:
            actualizar.aplicar = original
        self.assertEqual(reinicios, [1], "sin un segundo clic: aplica y reinicia solo")
        dlg.deleteLater()

    def test_globo_de_progreso_no_se_reanima(self):
        from pandex.ui.globo import Globo

        g = Globo()
        g.progreso("Voy 1 de 3…", 1, 3)
        g.setWindowOpacity(1.0)
        g._fade.stop()
        g.progreso("Voy 2 de 3…", 2, 3)
        self.assertEqual(g._avance, (2, 3))
        g.ocultar_ya()


if __name__ == "__main__":
    unittest.main()
