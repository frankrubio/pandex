"""La interfaz se construye y se pinta sin errores (ventanas invisibles, sin internet)."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from pandex.config import Config  # noqa: E402
from pandex.ui import dibujo, tema  # noqa: E402

app = QApplication.instance() or QApplication([])


class Interfaz(unittest.TestCase):
    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())
        self.config = Config(self.carpeta / "config.json")
        tema.aplicar(app)

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def test_cada_estado_se_pinta_y_queda_en_cache(self):
        for estado in dibujo.ESTADOS:
            pix = dibujo.imagen(estado, 120, 120)
            self.assertFalse(pix.isNull())
            self.assertIs(pix, dibujo.imagen(estado, 120, 120), "la segunda vez sale de la caché")

    def test_rusty_un_cuadro_fijo_por_estado(self):
        from pandex.ui import rusty

        self.assertTrue(rusty.disponible(), "assets/rusty/spritesheet.png")
        for estado in rusty.ESTADOS:
            pix = rusty.imagen(estado, 126)
            self.assertFalse(pix.isNull())
            self.assertLessEqual(pix.height(), 126)
            self.assertIs(pix, rusty.imagen(estado, 126), "la segunda vez sale de la caché")
        pix = rusty.imagen("idle", 126, 1.5)
        self.assertEqual(pix.devicePixelRatio(), 1.5)
        self.assertFalse(rusty.cabeza().isNull())

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
