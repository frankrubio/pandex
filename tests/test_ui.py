"""La interfaz se construye y se pinta sin errores (ventanas invisibles, sin internet)."""

import json
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


class PersonajesPropios(unittest.TestCase):
    """Añadir un personaje desde una imagen: el formato se reconoce solo."""

    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())
        self.destino = self.carpeta / "personajes"

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def _pose(self, color, fondo=(0, 0, 0, 0)):
        from PIL import Image, ImageDraw

        img = Image.new("RGBA", (60, 80), fondo)
        ImageDraw.Draw(img).ellipse((10, 10, 50, 70), fill=color)
        return img

    def test_una_tira_de_poses_se_parte_en_su_orden(self):
        from PIL import Image

        from pandex import personaje_nuevo

        tira = Image.new("RGBA", (240, 80))
        for i, color in enumerate(("red", "green", "blue", "yellow")):
            tira.paste(self._pose(color), (i * 60, 0))
        ruta = self.carpeta / "mi_gato.png"
        tira.save(ruta)
        ident, poses = personaje_nuevo.importar(ruta, "Mi gato", self.destino, ocupados={"rusty"})
        self.assertEqual((ident, poses), ("mi_gato", 4))
        datos = json.loads((self.destino / ident / "personaje.json").read_text(encoding="utf-8"))
        self.assertEqual(datos["cuadros"], {"idle": 0, "trabajando": 1, "feliz": 2, "error": 3})
        self.assertEqual(datos["nombre"], "Mi gato")

    def test_una_imagen_sola_con_fondo_blanco_pierde_el_fondo(self):
        from PIL import Image

        from pandex import personaje_nuevo

        ruta = self.carpeta / "dibujo.jpg"
        self._pose((200, 40, 40, 255), fondo=(255, 255, 255, 255)).convert("RGB").save(ruta, quality=95)
        ident, poses = personaje_nuevo.importar(ruta, "Dibujo", self.destino)
        self.assertEqual(poses, 1)
        hoja = Image.open(self.destino / ident / "spritesheet.png")
        self.assertEqual(hoja.getpixel((0, 0))[3], 0, "el fondo blanco ya no está")

    def test_un_gif_da_una_pose_por_cuadro_y_el_nombre_no_choca(self):
        from pandex import personaje_nuevo

        ruta = self.carpeta / "rusty.gif"
        cuadros = [self._pose(c).convert("RGB") for c in ("red", "blue", "green")]
        cuadros[0].save(ruta, save_all=True, append_images=cuadros[1:], duration=100)
        ident, poses = personaje_nuevo.importar(ruta, "Rusty", self.destino, ocupados={"rusty"})
        self.assertEqual((ident, poses), ("rusty_2", 3), "no pisa a un personaje de Pandex")

    def test_el_catalogo_lo_muestra_y_se_puede_quitar(self):
        from unittest import mock

        from pandex import personaje_nuevo
        from pandex.ui import logo, personajes

        ruta = self.carpeta / "zorro.png"
        self._pose("orange").save(ruta)
        ident, _ = personaje_nuevo.importar(ruta, "Zorro", self.destino)
        with mock.patch.object(personajes, "PERSONAJES_PROPIOS", self.destino):
            personajes.recargar()
            try:
                p = personajes.catalogo()[ident]
                self.assertTrue(p.propio)
                self.assertFalse(personajes.catalogo()["rusty"].propio)
                self.assertFalse(personajes.imagen(ident, "feliz", 120).isNull())
                logo.guardar_ico(ident)
                self.assertTrue(p.icono.exists())
                personaje_nuevo.quitar(ident, self.destino)
                personajes.recargar()
                self.assertNotIn(ident, personajes.catalogo())
            finally:
                personajes.recargar()
        with self.assertRaises(personaje_nuevo.ErrorPersonaje):
            personaje_nuevo.quitar("rusty", self.destino)

    def test_lo_que_no_es_imagen_da_un_mensaje_claro(self):
        from pandex import personaje_nuevo

        ruta = self.carpeta / "roto.png"
        ruta.write_text("no soy una imagen", encoding="utf-8")
        with self.assertRaises(personaje_nuevo.ErrorPersonaje):
            personaje_nuevo.importar(ruta, "Roto", self.destino)


class HorarioSinCron(unittest.TestCase):
    def test_lee_y_arma_los_horarios_simples(self):
        from PyQt6.QtCore import QTime

        from pandex.ui.configuracion import Horario, armar_horario, leer_horario

        self.assertEqual(leer_horario(None)[0], "manual")
        self.assertEqual(leer_horario("0 19 * * *"), ("diario", QTime(19, 0)))
        self.assertEqual(leer_horario("30 7 * * 1-5"), ("semana", QTime(7, 30)))
        self.assertEqual(leer_horario("*/30 8-18 * * 1-5")[0], "cron")
        self.assertEqual(armar_horario("semana", QTime(19, 5)), "5 19 * * 1-5")
        self.assertIsNone(armar_horario("manual", QTime(19, 5)))
        self.assertEqual(Horario("*/30 8-18 * * 1-5").valor(), "*/30 8-18 * * 1-5", "lo avanzado no se pierde")
        diario = Horario("0 19 * * *")
        self.assertEqual(diario.hora.text().replace("\xa0", " "), "7:00 p. m.")


class ExploradorDeArchivos(unittest.TestCase):
    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())
        for nombre in ("Clase 2.pdf", "Clase 10.pdf", "AP3-Sem3.pdf", "Clase 2.md"):
            (self.carpeta / nombre).write_text("x", encoding="utf-8")
        (self.carpeta / "Lecturas").mkdir()

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def test_columnas_orden_busqueda_y_marcar(self):
        from PyQt6.QtCore import Qt

        from pandex.markdown.navegador import ESTADO, NOMBRE, Navegador

        nav = Navegador([("Pruebas", self.carpeta)])
        nav._mostrar(self.carpeta)
        filas = nav._filas()
        self.assertEqual([f.text(NOMBRE) for f in filas],
                         ["..", "Lecturas", "AP3-Sem3.pdf", "Clase 2.pdf", "Clase 10.pdf"])
        estados = {f.text(NOMBRE): f.text(ESTADO) for f in filas}
        self.assertEqual(estados["Clase 2.pdf"], "✓ Ya en .md")
        self.assertTrue(estados["AP3-Sem3.pdf"].startswith("No:"))

        nav.lista.sortItems(NOMBRE, Qt.SortOrder.DescendingOrder)
        nombres = [f.text(NOMBRE) for f in nav._filas()]
        self.assertEqual(nombres[:2], ["..", "Lecturas"], "«..» y las carpetas siempre arriba")
        self.assertEqual(nombres[2], "Clase 10.pdf")

        nav.buscar.setText("clase")
        visibles = [f.text(NOMBRE) for f in nav._filas() if not f.isHidden()]
        self.assertEqual(sorted(visibles), ["..", "Clase 10.pdf", "Clase 2.pdf"])

        nav._marcar_todo()
        self.assertEqual(len(nav.marcados), 2, "marca el material de estudio visible")
        nav._elegir_marcados()
        self.assertEqual(len(nav.resultado["archivos"]), 2)


if __name__ == "__main__":
    unittest.main()
