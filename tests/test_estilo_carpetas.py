"""Spec 008: las carpetas nuevas van en «_» y sin tildes, o con el estilo que ya tienes (EST-01…07)."""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pandex.canvas import adoptar, destinos, nombres, sincronizar

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "herramientas"))


class ConEstilo(unittest.TestCase):
    """Cada prueba parte del estilo predeterminado y lo deja como estaba."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(setattr, nombres, "ESTILO_CARPETAS", nombres.ESTILO_CARPETAS)
        nombres.ESTILO_CARPETAS = "guiones_bajos"


class GuionesBajos(ConEstilo):
    """EST-01 y EST-04."""

    def test_sin_espacios_tildes_enie_ni_signos(self):
        casos = {
            "Diseño: Teoría": "Diseno_Teoria",
            "Matemáticas Discretas I": "Matematicas_Discretas_I",
            "Física I (Lab.)": "Fisica_I_Lab",
            "  Año   nuevo__2026 ": "Ano_nuevo_2026",
            "Ñandú": "Nandu",
            "¿Qué es?": "Que_es",
            "Sílabo y anexo": "Silabo_y_anexo",
            "Sem 3": "Sem_3",
            "a/b\\c|d": "a_b_c_d",
            "???": "carpeta",
            "": "carpeta",
        }
        for entrada, esperado in casos.items():
            self.assertEqual(nombres.en_guiones_bajos(entrada), esperado, entrada)
        self.assertRegex(nombres.nombre_de_carpeta("Diseño: Teoría"), r"^[A-Za-z0-9_]+$")

    def test_se_crean_con_guiones_bajos(self):
        self.assertEqual(destinos.resolver_subcarpeta(self.tmp, "Material de clase").name, "Material_de_clase")
        self.assertEqual(destinos.resolver_subcarpeta(self.tmp, destinos.nombre_semana(3)).name, "Sem_3")
        self.assertEqual(destinos.resolver_subcarpeta(self.tmp, "Teoría").name, "Teoria")

    def test_reutiliza_la_que_ya_tienes(self):
        (self.tmp / "Material de clase").mkdir()
        (self.tmp / "Programación").mkdir()
        (self.tmp / "Sem_4").mkdir()
        self.assertEqual(destinos.resolver_subcarpeta(self.tmp, "Material_de_clase").name, "Material de clase")
        self.assertEqual(destinos.resolver_subcarpeta(self.tmp, "Programacion").name, "Programación")
        self.assertEqual(destinos.resolver_subcarpeta(self.tmp, "Sem 4", destinos.alias_semana(4)).name, "Sem_4")
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()),
                         ["Material de clase", "Programación", "Sem_4"], "no se creó ni renombró nada")


class EstiloPropio(ConEstilo):
    """EST-02."""

    def setUp(self):
        super().setUp()
        nombres.ESTILO_CARPETAS = "propio"

    def test_se_escribe_tal_como_lo_tienes(self):
        self.assertEqual(destinos.resolver_subcarpeta(self.tmp, "Teoría").name, "Teoría")
        self.assertEqual(destinos.resolver_subcarpeta(self.tmp, "Material de clase").name, "Material de clase")
        self.assertEqual(destinos.resolver_subcarpeta(self.tmp, destinos.nombre_semana(8)).name, "Sem 8")

    def test_solo_cambia_lo_que_windows_no_acepta(self):
        self.assertEqual(nombres.nombre_de_carpeta("Diseño: Teoría"), "Diseño- Teoría")

    def test_el_estilo_explicito_de_la_llamada_manda(self):
        self.assertEqual(nombres.nombre_de_carpeta("Sem 8", "guiones_bajos"), "Sem_8")


class CarpetaDeCurso(ConEstilo):
    """EST-03: la carpeta del curso va en «_» aunque el resto siga tu estilo."""

    def test_siempre_en_guiones_bajos(self):
        for estilo in ("guiones_bajos", "propio"):
            nombres.ESTILO_CARPETAS = estilo
            self.assertEqual(nombres.nombre_de_curso("Matemáticas Discretas I"), "Matematicas_Discretas_I")

    def test_la_tarea_crea_el_curso_en_guiones_bajos_y_lo_de_dentro_como_tu_estilo(self):
        nombres.ESTILO_CARPETAS = "propio"
        tarea = sincronizar.Sincronizacion(mock.Mock(params={"estilo_carpetas": "propio"}))
        tarea.raiz = self.tmp
        tarea.ctx.log = mock.Mock()
        carpeta = tarea._carpeta_curso({"carpeta": "Física I"})
        self.assertEqual(carpeta.name, "Fisica_I")
        self.assertEqual(destinos.resolver_subcarpeta(carpeta, "Teoría").name, "Teoría")

    def test_un_curso_que_ya_existe_no_se_renombra(self):
        (self.tmp / "Física I").mkdir()
        tarea = sincronizar.Sincronizacion(mock.Mock(params={}))
        tarea.raiz = self.tmp
        self.assertEqual(tarea._carpeta_curso({"carpeta": "Fisica_I"}).name, "Física I")


class Estilo(ConEstilo):
    """EST-06: de dónde sale el estilo."""

    def test_valores_explicitos(self):
        self.assertEqual(nombres.estilo_de({"estilo_carpetas": "propio"}), "propio")
        self.assertEqual(nombres.estilo_de({"estilo_carpetas": "guiones_bajos", "cursos": [{}]}), "guiones_bajos")

    def test_sin_nada_es_guiones_bajos(self):
        self.assertEqual(nombres.estilo_de({}), "guiones_bajos")
        self.assertEqual(nombres.estilo_de({"estilo_carpetas": "cualquier cosa"}), "guiones_bajos")

    def test_configuracion_anterior(self):
        """Quien ya tenía cursos configurados sigue con sus nombres: no se mezclan estilos."""
        self.assertEqual(nombres.estilo_de({"cursos": [{"carpeta": "X"}], "destino": "/x"}), "propio")
        self.assertEqual(nombres.estilo_de({"carpetas_sin_tildes": False}), "propio")

    def test_la_tarea_lo_fija_al_empezar(self):
        sincronizar.Sincronizacion(mock.Mock(params={"estilo_carpetas": "propio"}))
        self.assertEqual(nombres.ESTILO_CARPETAS, "propio")
        sincronizar.Sincronizacion(mock.Mock(params={}))
        self.assertEqual(nombres.ESTILO_CARPETAS, "guiones_bajos")


class Asistente(unittest.TestCase):
    """EST-05."""

    def setUp(self):
        self.raiz = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.raiz, True)

    def test_detectada_solo_si_leyo_algo(self):
        (self.raiz / "Prog" / "Sem 1" / "Teoría").mkdir(parents=True)
        self.assertTrue(adoptar.detectar_convenciones([self.raiz / "Prog"]).detectada)
        (self.raiz / "Vacia").mkdir()
        self.assertFalse(adoptar.detectar_convenciones([self.raiz / "Vacia"]).detectada)
        self.assertFalse(adoptar.detectar_convenciones([]).detectada)
        self.assertFalse(adoptar.Convenciones().detectada)

    def test_el_estado_elige_el_estilo(self):
        from pandex.canvas.asistente import Estado

        estado = Estado({})
        self.assertEqual(estado.estilo_carpetas(), "guiones_bajos")
        estado.modo = "existente"
        self.assertEqual(estado.estilo_carpetas(), "guiones_bajos", "no leyó ningún estilo")
        (self.raiz / "Prog" / "Sem 1" / "Teoría").mkdir(parents=True)
        estado.convenciones = adoptar.detectar_convenciones([self.raiz / "Prog"])
        self.assertEqual(estado.estilo_carpetas(), "propio")
        estado.modo = "nueva"
        self.assertEqual(estado.estilo_carpetas(), "guiones_bajos")


class AplicarConfig(unittest.TestCase):
    """EST-07."""

    def setUp(self):
        import aplicar_config_canvas

        self.herramienta = aplicar_config_canvas
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.config = self.tmp / "config.json"
        self.config.write_text(json.dumps({
            "mascota": {"nombre": "Rusty"},
            "tareas": {"sync_canvas": {"schedule": "0 19 * * *", "cursos": [{"carpeta": "Vieja"}]},
                       "otra": {"x": 1}}}), encoding="utf-8")
        self.nuevo = self.tmp / "mi_canvas.json"

    def aplicar(self, texto):
        self.nuevo.write_text(texto, encoding="utf-8")
        return self.herramienta.aplicar(self.nuevo, self.config)

    def test_mezcla_sin_tocar_lo_demas(self):
        self.aplicar(json.dumps({"formato_semana": "Sem {n}", "cursos": [{"carpeta": "Nueva"}]}))
        datos = json.loads(self.config.read_text(encoding="utf-8"))
        canvas = datos["tareas"]["sync_canvas"]
        self.assertEqual(canvas["cursos"], [{"carpeta": "Nueva"}], "la lista se reemplaza")
        self.assertEqual(canvas["schedule"], "0 19 * * *", "lo que no viene se queda")
        self.assertEqual(canvas["formato_semana"], "Sem {n}")
        self.assertEqual(datos["tareas"]["otra"], {"x": 1})
        self.assertEqual(datos["mascota"], {"nombre": "Rusty"})

    def test_deja_copia_de_respaldo(self):
        antes = self.config.read_text(encoding="utf-8")
        self.aplicar(json.dumps({"formato_semana": "Sem {n}"}))
        respaldos = list(self.tmp.glob("config.json.antes-*"))
        self.assertEqual(len(respaldos), 1)
        self.assertEqual(respaldos[0].read_text(encoding="utf-8"), antes)

    def test_json_invalido_no_toca_nada(self):
        antes = self.config.read_text(encoding="utf-8")
        with self.assertRaises(self.herramienta.ErrorConfig):
            self.aplicar("{esto no es json")
        self.assertEqual(self.config.read_text(encoding="utf-8"), antes)
        self.assertEqual(list(self.tmp.glob("config.json.antes-*")), [])

    def test_que_no_sea_un_objeto_tampoco(self):
        with self.assertRaises(self.herramienta.ErrorConfig):
            self.aplicar("[1, 2]")

    def test_crea_config_si_no_existe(self):
        self.config.unlink()
        self.aplicar(json.dumps({"formato_semana": "Sem {n}"}))
        datos = json.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual(datos["tareas"]["sync_canvas"], {"formato_semana": "Sem {n}"})


if __name__ == "__main__":
    unittest.main()
