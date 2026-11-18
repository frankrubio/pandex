"""Robustez (spec 011): Pandex no se cae ni se queda colgado."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pandex.config import DEFAULTS, Config  # noqa: E402
from pandex.rutas import RAIZ  # noqa: E402
from tests.apoyo import CanvasFalso, ConCarpetaTemporal, CtxFalso, modulo  # noqa: E402


def _correr(codigo, datos):
    """Corre ``codigo`` en un Python aparte (un error de Qt aborta el proceso entero)."""
    entorno = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "PANDEX_DATOS": str(datos),
               "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, "-c", codigo], cwd=str(RAIZ), env=entorno,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)


class ErroresInesperados(unittest.TestCase):
    """ROB-01: un error que nadie atrapó no cierra Pandex."""

    def setUp(self):
        self.datos = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.datos, ignore_errors=True)

    def test_un_error_en_la_interfaz_no_cierra_pandex(self):
        r = _correr(
            "import sys\n"
            "from PyQt6.QtCore import QTimer\n"
            "from PyQt6.QtWidgets import QApplication\n"
            "from pandex import errores\n"
            "app = QApplication(sys.argv)\n"
            "avisos = []\n"
            "errores.instalar(avisos.append)\n"
            "def falla():\n"
            "    raise RuntimeError('error de prueba en un reloj')\n"
            "QTimer.singleShot(50, falla)\n"
            "QTimer.singleShot(600, lambda: (print('SIGUE VIVO', len(avisos)), app.quit()))\n"
            "sys.exit(app.exec())\n", self.datos)
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        self.assertIn("SIGUE VIVO 1", r.stdout)

    def test_se_anota_con_su_traza_y_se_avisa(self):
        from pandex import errores

        avisos = []
        with mock.patch.object(errores, "_avisar", avisos.append), \
                self.assertLogs("pandex.errores", level="ERROR") as registro:
            try:
                raise ValueError("dato raro")
            except ValueError:
                errores.atender(*sys.exc_info())
        self.assertIn("ValueError: dato raro", "\n".join(registro.output))
        self.assertIn("test_robustez.py", "\n".join(registro.output), "la traza dice dónde fue")
        self.assertEqual(len(avisos), 1)
        self.assertIn("Ver registro", avisos[0])

    def test_un_error_que_se_repite_no_llena_el_registro_ni_de_globos(self):
        from pandex import errores

        avisos = []
        with mock.patch.object(errores, "_avisar", avisos.append), \
                mock.patch.dict(errores._VISTOS, clear=True), \
                mock.patch.object(errores, "_ultimo_aviso", 0.0), \
                self.assertLogs("pandex.errores", level="ERROR") as registro:
            for _ in range(250):
                try:
                    raise KeyError("otra vez")
                except KeyError:
                    errores.atender(*sys.exc_info())
        trazas = [l for l in registro.output if "Traceback" in l]
        self.assertEqual(len(trazas), 1, "la traza completa, solo la primera vez")
        self.assertLessEqual(len(registro.output), 4, "luego, una línea cada 10 y 100 repeticiones")
        self.assertEqual(len(avisos), 1, "un globo cada 30 s como mucho")

    def test_un_error_en_otro_hilo_tambien_se_anota(self):
        from pandex import errores

        previo_hilo, previo = threading.excepthook, sys.excepthook
        avisos = []
        try:
            errores.instalar(avisos.append)
            with mock.patch.dict(errores._VISTOS, clear=True), \
                    self.assertLogs("pandex.errores", level="ERROR") as registro:
                hilo = threading.Thread(target=lambda: 1 / 0)
                hilo.start()
                hilo.join()
            self.assertIn("ZeroDivisionError", "\n".join(registro.output))
        finally:
            threading.excepthook, sys.excepthook = previo_hilo, previo
            errores.instalar.__globals__["_avisar"] = None

    def test_ctrl_c_sigue_cerrando(self):
        from pandex import errores

        with mock.patch.object(sys, "__excepthook__") as original:
            errores.atender(KeyboardInterrupt, KeyboardInterrupt(), None)
        original.assert_called_once()


class ConfiguracionDanada(unittest.TestCase):
    """ROB-02 y ROB-03: un ``config.json`` dañado no impide abrir Pandex."""

    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())
        self.ruta = self.carpeta / "config.json"
        self.datos = self.carpeta / "datos"
        self.copia = self.datos / "config-ultima-buena.json"

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def _abrir(self):
        return Config(self.ruta, copia=self.copia)

    def _buena(self):
        self.ruta.write_text(json.dumps({"mascota": {"nombre": "Pygu"},
                                         "tareas": {"sync_canvas": {"destino": "/cursos"}}}), encoding="utf-8")
        return self._abrir()

    def test_un_archivo_bueno_deja_su_copia(self):
        config = self._buena()
        self.assertIsNone(config.recuperada)
        self.assertEqual(json.loads(self.copia.read_text(encoding="utf-8"))["mascota"]["nombre"], "Pygu")

    def test_danado_se_recupera_de_la_ultima_copia_buena(self):
        self._buena()
        for contenido in ("", '{"mascota": {"nombre": "Pan', "[]", "null", "\x00\x00\x00"):
            with self.subTest(contenido=contenido):
                self.ruta.write_text(contenido, encoding="utf-8")
                config = self._abrir()
                self.assertEqual(config.recuperada, "copia")
                self.assertEqual(config.mascota["nombre"], "Pygu")
                self.assertEqual(config.tarea("sync_canvas")["destino"], "/cursos")
                self.assertEqual(json.loads(self.ruta.read_text(encoding="utf-8"))["mascota"]["nombre"], "Pygu",
                                 "config.json vuelve a ser un archivo bueno")

    def test_danado_y_sin_copia_abre_con_los_valores_de_fabrica(self):
        self.ruta.write_text("{esto no es json", encoding="utf-8")
        config = self._abrir()
        self.assertEqual(config.recuperada, "fabrica")
        self.assertEqual(config.mascota["nombre"], DEFAULTS["mascota"]["nombre"])

    def test_el_danado_se_guarda_aparte_y_quedan_tres(self):
        self._buena()
        for n in range(5):
            self.ruta.write_text(f"dañado {n}", encoding="utf-8")
            with mock.patch("pandex.config._marca", return_value=f"20261110-12000{n}"):
                self._abrir()
        apartados = sorted(self.datos.glob("config-danado-*.json"))
        self.assertEqual(len(apartados), 3)
        self.assertEqual(apartados[-1].read_text(encoding="utf-8"), "dañado 4")

    def test_una_seccion_de_otro_tipo_no_rompe_nada(self):
        self.ruta.write_text(json.dumps({"mascota": 5, "tareas": {"sync_canvas": "x", "otra": {"a": 1}}}),
                             encoding="utf-8")
        config = self._abrir()
        self.assertEqual(config.mascota["nombre"], DEFAULTS["mascota"]["nombre"])
        self.assertEqual(config.tarea("sync_canvas"), {})
        self.assertEqual(config.tarea("otra"), {"a": 1})

    def test_tareas_de_otro_tipo(self):
        self.ruta.write_text(json.dumps({"tareas": []}), encoding="utf-8")
        self.assertEqual(self._abrir().tarea("x"), {})

    def test_guardar_fuerza_la_escritura(self):
        config = self._buena()
        with mock.patch("pandex.config.os.fsync") as fsync:
            config.guardar()
        fsync.assert_called_once()
        self.assertFalse(self.ruta.with_suffix(".json.tmp").exists())

    def test_sin_copia_configurada_tambien_abre(self):
        self.ruta.write_text("", encoding="utf-8")
        config = Config(self.ruta, copia=None)
        self.assertEqual(config.recuperada, "fabrica")


class ArranqueFallido(unittest.TestCase):
    """ROB-04: si no puede arrancar, lo anota y avisa; no muere en silencio."""

    def setUp(self):
        self.datos = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.datos, ignore_errors=True)

    def test_sin_persona_delante_lo_anota_y_sale_con_1(self):
        r = _correr(
            "import sys\n"
            "import main, pandex.app\n"
            "def roto(*a, **k):\n"
            "    raise RuntimeError('no arranco')\n"
            "pandex.app.PandexApp = roto\n"
            "main.avisar_al_que_ya_corre = lambda *a: False\n"
            "sys.argv = ['main.py', '--test']\n"
            "sys.exit(main.main())\n", self.datos)
        self.assertEqual(r.returncode, 1, r.stderr[-600:])

    def test_con_persona_delante_muestra_que_hacer(self):
        import main

        with mock.patch.object(main, "_ventana_de_error") as ventana, \
                self.assertLogs("pandex", level="ERROR") as registro:
            try:
                raise RuntimeError("no arranco")
            except RuntimeError:
                codigo = main.arranque_fallido(silencioso=False)
        self.assertEqual(codigo, 1)
        self.assertIn("RuntimeError: no arranco", "\n".join(registro.output))
        texto = ventana.call_args.args[0]
        self.assertIn("instalar", texto)
        self.assertIn("pandex.log", texto)

    def test_sin_persona_delante_no_abre_ventanas(self):
        import main

        with mock.patch.object(main, "_ventana_de_error") as ventana, self.assertLogs("pandex", level="ERROR"):
            try:
                raise RuntimeError("no arranco")
            except RuntimeError:
                main.arranque_fallido(silencioso=True)
        ventana.assert_not_called()


class Cancelar(ConCarpetaTemporal):
    """ROB-05 y ROB-06: una tarea se puede cancelar, y «Salir» no la deja a medias."""

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.qapp = QApplication.instance() or QApplication([])

    def _ctx(self):
        from pandex.tareas import TaskContext

        return TaskContext("x", Config(self.tmp / "config.json", copia=None))

    # ---------- el contexto y el ejecutor ----------

    def test_el_ctx_avisa_lanza_y_cierra_lo_abierto(self):
        from pandex.tareas import Cancelada

        ctx, cerrados = self._ctx(), []
        ctx.al_cancelar(lambda: cerrados.append("navegador"))
        self.assertFalse(ctx.cancelada)
        ctx.comprobar_cancelacion()  # todavía no: no lanza
        ctx.cancelar()
        ctx.cancelar()  # dos veces no cierra dos veces
        self.assertTrue(ctx.cancelada)
        self.assertEqual(cerrados, ["navegador"])
        with self.assertRaises(Cancelada):
            ctx.comprobar_cancelacion()
        ctx.al_cancelar(lambda: cerrados.append("tarde"))  # ya estaba cancelada: se cierra enseguida
        self.assertEqual(cerrados, ["navegador", "tarde"])

    def test_un_cierre_que_falla_no_impide_cancelar(self):
        ctx, cerrados = self._ctx(), []
        ctx.al_cancelar(lambda: 1 / 0)
        ctx.al_cancelar(lambda: cerrados.append("ok"))
        with self.assertLogs("pandex", level="WARNING"):
            ctx.cancelar()
        self.assertEqual(cerrados, ["ok"])

    def _ejecutar(self, run):
        from pandex.ejecutor import Ejecutor

        tarea = type("Task", (), {"id": "lenta", "nombre": "Lenta", "run": lambda self, ctx: run(ctx)})()
        ejecutor, resultados = Ejecutor(Config(self.tmp / "config.json", copia=None)), []
        ejecutor.terminada.connect(lambda _id, r: resultados.append(r))
        self.assertTrue(ejecutor.ejecutar(tarea))
        return ejecutor, resultados

    def test_el_ejecutor_cancela_una_tarea_que_coopera(self):
        empezo = threading.Event()

        def run(ctx):
            empezo.set()
            while True:
                ctx.comprobar_cancelacion()
                time.sleep(0.005)

        ejecutor, resultados = self._ejecutar(run)
        self.assertTrue(empezo.wait(5))
        self.assertEqual(ejecutor.actual, "Lenta")
        self.assertTrue(ejecutor.cancelar())
        self.assertTrue(ejecutor.esperar(5000), "la tarea paró a tiempo")
        self.qapp.processEvents()
        self.assertEqual(len(resultados), 1)
        self.assertTrue(resultados[0]["cancelada"])
        self.assertEqual(resultados[0]["resumen"], "Cancelé «Lenta».")
        self.assertFalse(ejecutor.cancelar(), "sin tarea en curso no hay nada que cancelar")

    def test_esperar_dice_si_la_tarea_no_termino(self):
        suelta = threading.Event()
        ejecutor, _ = self._ejecutar(lambda ctx: suelta.wait(10) and {"ok": True})
        try:
            self.assertFalse(ejecutor.esperar(50))
        finally:
            suelta.set()
            ejecutor.esperar(5000)
            self.qapp.processEvents()

    # ---------- las tareas que tardan ----------

    def test_sincronizar_se_cancela_entre_descargas_y_no_deja_restos(self):
        from pandex.canvas import sincronizar
        from pandex.canvas.historial import Historial
        from pandex.tareas import Cancelada

        ciclo = self.tmp / "Ciclo"
        ciclo.mkdir()
        CanvasFalso.reiniciar(
            cursos=[{"id": 3, "name": "Cálculo (CC6101) - Teoría 4"}],
            modulos={3: [modulo("Semana 6", *[("file", f"Clase {n}.pdf", 100 + n) for n in range(1, 9)])]},
            archivos={100 + n: (f"Clase {n}.pdf", 5000 + n) for n in range(1, 9)})
        ctx = CtxFalso({"canvas_url": "https://canvas.ejemplo.edu", "destino": str(ciclo),
                        "cursos": [{"codigo": "CC6101", "carpeta": "Calculo", "alias": "Cálculo",
                                    "crear_secciones": True}]})
        original = CanvasFalso.descargar

        def descargar(falso, curso_id, file_id, destino_tmp, **mas):
            escritos = original(falso, curso_id, file_id, destino_tmp, **mas)
            ctx.cancelada = True  # el usuario cancela mientras baja el primero
            return escritos

        with mock.patch.object(sincronizar, "HILOS_DESCARGA", 1), \
                mock.patch.object(CanvasFalso, "descargar", descargar):
            with self.assertRaises(Cancelada):
                sincronizar.Sincronizacion(ctx).ejecutar()
        bajados = sorted(p.name for p in ciclo.rglob("*.pdf"))
        self.assertLess(len(bajados), 8, "no siguió bajando")
        self.assertEqual(list(sincronizar.TEMPORAL.glob("*.part")), [], "sin descargas a medias")
        self.assertEqual(len(Historial().archivos), len(bajados), "lo que sí bajó quedó anotado (P4)")

    def test_una_descarga_grande_para_en_el_siguiente_trozo(self):
        from pandex.canvas.cliente import Canvas
        from pandex.tareas import Cancelada

        respuesta = mock.MagicMock(status_code=200, headers={"content-type": "application/pdf"})
        respuesta.__enter__.return_value = respuesta
        respuesta.iter_content.return_value = iter([b"a" * 10, b"b" * 10, b"c" * 10])
        canvas = Canvas("https://canvas.ejemplo.edu", [], "ua")
        with mock.patch.object(canvas, "_get", return_value=respuesta):
            with self.assertRaises(Cancelada):
                canvas.descargar(1, 2, self.tmp / "x.part", parar=lambda: True)
        self.assertEqual((self.tmp / "x.part").stat().st_size, 10, "paró tras el primer trozo")

    def test_la_espera_del_inicio_de_sesion_se_cancela(self):
        from pandex.canvas import sesion
        from pandex.tareas import Cancelada

        ctx = CtxFalso({})
        ctx.cancelada = True
        pagina = mock.Mock(url="https://sso.ejemplo.edu/login")
        with mock.patch.object(sesion, "_sesion_valida", return_value=False):
            with self.assertRaises(Cancelada):
                sesion._esperar_sesion(mock.Mock(), pagina, "https://canvas.ejemplo.edu", 5, 10, ctx=ctx)

    def test_cancelar_cierra_la_ventana_de_chrome_o_edge(self):
        from pandex.canvas import sesion
        from pandex.tareas import Cancelada

        ctx = CtxFalso({})
        ctx.cancelada = True
        ventana = mock.Mock()
        ventana.poll.return_value = None
        with mock.patch.object(sesion._navegador, "abrir_ventana_normal", return_value=ventana), \
                mock.patch.object(sesion._navegador, "en_uso", return_value=True):
            with self.assertRaises(Cancelada):
                sesion._entrar_en_ventana_normal(ctx, "https://canvas.ejemplo.edu", "chrome",
                                                 mock.Mock(), (RuntimeError,), 300)
        ventana.terminate.assert_called_once()

    def test_convertir_cierra_su_proceso_al_cancelar(self):
        import io

        from pandex.markdown import proceso
        from pandex.tareas import Cancelada

        class Hijo:
            returncode = None

            def __init__(self):
                self.fin, self.stdin, self.stdout = threading.Event(), io.StringIO(), self._lineas()

            def _lineas(self):
                self.fin.wait(10)  # como un PDF enorme: no dice nada hasta que lo cierran
                return
                yield

            def terminate(self):
                self.returncode = -15
                self.fin.set()

            def __enter__(self):
                return self

            def __exit__(self, *_a):
                self.fin.set()

        hijo, ctx, errores_ = Hijo(), self._ctx(), []

        def convertir():
            try:
                proceso.convertir_aparte(ctx)
            except Cancelada:
                errores_.append("cancelada")

        with mock.patch.object(proceso.subprocess, "Popen", return_value=hijo):
            hilo = threading.Thread(target=convertir)
            hilo.start()
            time.sleep(0.1)
            ctx.cancelar()
            hilo.join(5)
        self.assertFalse(hilo.is_alive(), "no se quedó esperando al proceso")
        self.assertEqual(hijo.returncode, -15, "cerró el proceso de conversión")
        self.assertEqual(errores_, ["cancelada"])

    def test_comprimir_no_deja_un_zip_a_medias(self):
        import importlib.util

        from pandex.rutas import TASKS_DIR
        from pandex.tareas import Cancelada

        carpeta = self.tmp / "Curso"
        carpeta.mkdir()
        for n in range(5):
            (carpeta / f"apunte{n}.txt").write_text("hola " * 100, encoding="utf-8")
        spec = importlib.util.spec_from_file_location("comprimir_tarea", TASKS_DIR / "comprimir.py")
        modulo_ = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo_)
        ctx = CtxFalso({}, {"carpeta": str(carpeta), "pdfs": False})
        ctx.progreso = lambda n, _t: setattr(ctx, "cancelada", n >= 2)
        with self.assertRaises(Cancelada):
            modulo_.Task().run(ctx)
        self.assertEqual([p.name for p in self.tmp.iterdir() if p.name != "Curso"], [])

    # ---------- la app ----------

    def _app(self, ocupado=True):
        app = mock.MagicMock()
        app._nueva, app.tareas, app._dialogos = None, [], []
        app.ejecutor.ocupado, app.ejecutor.actual = ocupado, "Sincronizar Canvas"
        app.config = Config(self.tmp / "config.json", copia=None)
        return app

    def _textos(self, app):
        from pandex.app import PandexApp

        menu = PandexApp._construir_menu(app, None)
        return [a.text() for a in menu.actions()]

    def test_el_menu_ofrece_cancelar_solo_con_una_tarea_en_curso(self):
        self.assertIn("Cancelar «Sincronizar Canvas»", self._textos(self._app(ocupado=True)))
        self.assertFalse([t for t in self._textos(self._app(ocupado=False)) if t.startswith("Cancelar")])

    def test_una_tarea_cancelada_no_es_un_error(self):
        from pandex.app import PandexApp

        app = self._app()
        PandexApp._tarea_terminada(app, "x", {"ok": False, "cancelada": True, "resumen": "Cancelé «X».",
                                              "detalle": []})
        app.mascota.set_estado.assert_called_with("idle")
        self.assertEqual(app.mascota.decir.call_args.args[0], "Cancelé «X».")
        self.assertNotEqual(app.mascota.decir.call_args.kwargs.get("tipo"), "error")

    def test_salir_cancela_y_espera(self):
        from pandex.app import PandexApp

        app = self._app()
        app.ejecutor.esperar.return_value = True
        PandexApp._cerrar(app)
        app.ejecutor.cancelar.assert_called_once()
        app.ejecutor.esperar.assert_called_once_with(5000)
        app.qapp.quit.assert_called_once()
        app._forzar_salida.assert_not_called()

    def test_si_la_tarea_no_termina_pandex_se_cierra_igual(self):
        from pandex.app import PandexApp

        app = self._app()
        app.ejecutor.esperar.return_value = False
        with self.assertLogs("pandex.app", level="WARNING"):
            PandexApp._cerrar(app)
        app._forzar_salida.assert_called_once()

    def test_salir_sin_tarea_no_espera(self):
        from pandex.app import PandexApp

        app = self._app(ocupado=False)
        PandexApp._cerrar(app)
        app.ejecutor.cancelar.assert_not_called()
        app.qapp.quit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
