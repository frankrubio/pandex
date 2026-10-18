"""Tareas a su hora: ponerse al día si la PC estuvo apagada, y el despertador del sistema."""

import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from pandex import despertador, extras, pendientes
from pandex.rutas import RAIZ

LIMA = datetime.now().astimezone().tzinfo


def momento(dia, hora, minuto=0):
    """Octubre de 2026: el 19 es lunes."""
    return datetime(2026, 10, dia, hora, minuto, tzinfo=LIMA)


class Pendientes(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        parche = mock.patch.object(pendientes, "ARCHIVO", self.tmp / "ultimas.json")
        parche.start()
        self.addCleanup(parche.stop)
        self.config = {"tareas": {"sync_canvas": {"activa": True, "schedule": "0 19 * * 1-5"},
                                  "apagada": {"activa": False, "schedule": "0 19 * * *"},
                                  "manual": {"activa": True}}}

    def test_la_primera_vez_solo_anota_desde_cuando(self):
        self.assertEqual(pendientes.vencidas(self.config, momento(19, 20)), [])
        self.assertEqual(pendientes.vencidas(self.config, momento(19, 21)), [])

    def test_si_la_pc_estuvo_apagada_a_la_hora_la_hace_al_volver(self):
        pendientes.vencidas(self.config, momento(19, 10))  # lunes 10:00 a. m.: empieza a contar
        self.assertEqual(pendientes.vencidas(self.config, momento(19, 18, 59)), [])
        # la PC se apagó antes de las 7 p. m. y se prendió el martes a las 8 a. m.
        self.assertEqual(pendientes.vencidas(self.config, momento(20, 8)), ["sync_canvas"])

    def test_varias_perdidas_cuentan_como_una_y_no_se_repite(self):
        pendientes.vencidas(self.config, momento(19, 10))
        self.assertEqual(pendientes.vencidas(self.config, momento(23, 9)), ["sync_canvas"])
        pendientes.marcar("sync_canvas", "0 19 * * 1-5", momento(23, 9, 5))
        self.assertEqual(pendientes.vencidas(self.config, momento(23, 12)), [])
        self.assertEqual(pendientes.vencidas(self.config, momento(23, 19, 1)), ["sync_canvas"])

    def test_el_fin_de_semana_no_toca(self):
        pendientes.vencidas(self.config, momento(23, 20))  # viernes 8 p. m.
        self.assertEqual(pendientes.vencidas(self.config, momento(25, 22)), [])  # domingo
        self.assertEqual(pendientes.vencidas(self.config, momento(26, 19, 30)), ["sync_canvas"])

    def test_cambiar_el_horario_vuelve_a_contar_desde_ahora(self):
        pendientes.vencidas(self.config, momento(19, 10))
        self.config["tareas"]["sync_canvas"]["schedule"] = "0 8 * * *"
        self.assertEqual(pendientes.vencidas(self.config, momento(21, 7)), [])  # anota el cambio
        self.assertEqual(pendientes.vencidas(self.config, momento(21, 9)), ["sync_canvas"])

    def test_el_horario_del_codigo_cuenta_si_config_no_dice_nada(self):
        pendientes.vencidas({}, momento(19, 10), por_defecto={"saludo": "0 12 * * *"})
        self.assertEqual(pendientes.vencidas({}, momento(19, 13), por_defecto={"saludo": "0 12 * * *"}),
                         ["saludo"])


class DiasDeLaSemana(unittest.TestCase):
    def test_lunes_a_viernes_es_lunes_a_viernes(self):
        """APScheduler cuenta 0 = lunes; cron, 0 = domingo. Antes «1-5» corría de martes a sábado."""
        disparo = pendientes.disparador("0 19 * * 1-5")
        sabado = momento(24, 20)
        self.assertEqual(disparo.get_next_fire_time(None, sabado).strftime("%a %d"), "Mon 26")
        self.assertEqual(pendientes.disparador("0 8 * * 0").get_next_fire_time(None, sabado).strftime("%a"), "Sun")
        self.assertEqual(pendientes.disparador("0 8 * * 7").get_next_fire_time(None, sabado).strftime("%a"), "Sun")


class Despertador(unittest.TestCase):
    def test_cron_a_systemd(self):
        casos = {
            "0 19 * * 1-5": "Mon..Fri *-*-* 19:00:00",
            "30 7 * * *": "*-*-* 07:30:00",
            "*/15 * * * *": "*-*-* *:0/15:00",
            "0 8,20 * * 0,6": "Sun,Sat *-*-* 8,20:00:00",
            "5 4 * * 7": "Sun *-*-* 04:05:00",
        }
        for cron, esperado in casos.items():
            self.assertEqual(despertador.a_oncalendar(cron), esperado, cron)
        self.assertIsNone(despertador.a_oncalendar("0 9 1 * 1"), "cron «día o día-semana» no se traduce")
        self.assertIsNone(despertador.a_oncalendar("basura"))

    @unittest.skipUnless(shutil.which("systemd-analyze"), "hace falta systemd-analyze")
    def test_systemd_entiende_lo_que_escribimos(self):
        for cron in ("0 19 * * 1-5", "30 7 * * *", "*/15 * * * *", "0 8,20 * * 0,6", "0 9 1 * *"):
            calendario = despertador.a_oncalendar(cron)
            r = subprocess.run(["systemd-analyze", "calendar", calendario], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{cron} → {calendario}: {r.stderr}")

    def test_unidades_persistentes_y_al_iniciar_sesion(self):
        servicio, temporizador = despertador.unidades({"sync_canvas": "0 19 * * 1-5", "raro": "0 9 1 * 1"})
        self.assertIn("--pendientes", servicio)
        self.assertIn("OnCalendar=Mon..Fri *-*-* 19:00:00", temporizador)
        self.assertIn(f"OnCalendar={despertador.CADA_15}", temporizador)
        self.assertIn("Persistent=true", temporizador)
        self.assertIn("OnStartupSec=", temporizador)

    def test_windows_ejecuta_lo_antes_posible_si_se_perdio(self):
        script = despertador.script_windows({"sync_canvas": "0 19 * * 1-5", "otra": "30 7 * * *"})
        self.assertIn("-StartWhenAvailable", script)
        self.assertIn("-AtLogOn", script)
        self.assertIn("-Weekly -DaysOfWeek Friday,Monday,Thursday,Tuesday,Wednesday -At '19:00'", script)
        self.assertIn("-Daily -At '07:30'", script)
        self.assertIn("--pendientes", script)

    def test_solo_se_instala_en_modo_a_la_hora(self):
        config = {"tareas": {"sync_canvas": {"schedule": "0 19 * * *"}}}
        with mock.patch.object(despertador, "quitar") as quitar, \
                mock.patch.object(despertador, "_instalar_linux") as instalar, \
                mock.patch.object(despertador, "WINDOWS", False):
            self.assertFalse(despertador.actualizar(config))
            quitar.assert_called_once()
            config["modo"] = "a_la_hora"
            self.assertTrue(despertador.actualizar(config))
            instalar.assert_called_once()

    def test_escribe_y_activa_el_temporizador(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": tmp}), \
                mock.patch.object(despertador.shutil, "which", return_value="/usr/bin/systemctl"), \
                mock.patch.object(despertador, "_systemctl") as systemctl:
            despertador._instalar_linux({"sync_canvas": "0 19 * * 1-5"})
            carpeta = Path(tmp) / "systemd" / "user"
            self.assertTrue((carpeta / "pandex.timer").exists())
            self.assertIn(mock.call("enable", "--now", "pandex.timer"), systemctl.call_args_list)
            despertador._quitar_linux()
            self.assertFalse((carpeta / "pandex.timer").exists())


class SinNadaPendiente(unittest.TestCase):
    def test_sale_enseguida_sin_abrir_la_ventana(self):
        with tempfile.TemporaryDirectory() as tmp:
            entorno = {**os.environ, "PANDEX_DATOS": tmp, "QT_QPA_PLATFORM": "offscreen"}
            codigo = ("import runpy, sys; sys.argv = ['main.py', '--pendientes'];"
                      "import main; r = main.main(); "
                      "print('qt' if 'PyQt6.QtWidgets' in sys.modules else 'sin-qt', r)")
            inicio = time.monotonic()
            r = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, env=entorno,
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.stdout.split(), ["sin-qt", "0"], r.stderr)
            self.assertLess(time.monotonic() - inicio, 10)


class FuncionesOpcionales(unittest.TestCase):
    def test_sin_markdown_no_se_ofrece(self):
        tarea = type("T", (), {"requiere": "markdown"})()
        with mock.patch.object(extras.importlib.util, "find_spec", return_value=None):
            self.assertFalse(extras.disponible(tarea))
        self.assertTrue(extras.disponible(type("T", (), {})()))

    def test_la_tarea_de_markdown_carga_aunque_falte_el_conversor(self):
        """El menú la oculta, pero su archivo no debe romper al cargar las tareas."""
        codigo = ("import sys; sys.modules['markitdown'] = None; sys.modules['pypdfium2'] = None;"
                  "from pandex import tareas; print(sorted(t.id for t in tareas.descubrir()))")
        r = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True,
                           timeout=60, env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
        self.assertIn("convertir_md", r.stdout, r.stderr)

    def test_al_actualizar_reinstala_tambien_lo_opcional_que_ya_tenias(self):
        from pandex import actualizar

        with mock.patch.object(extras, "instalados_en", return_value=["markdown"]), \
                mock.patch.object(actualizar.subprocess, "run",
                                  return_value=mock.Mock(returncode=0, stderr="")) as run:
            actualizar.instalar_dependencias(RAIZ)
        comando = run.call_args.args[0]
        self.assertIn(str(RAIZ / "requirements.txt"), comando)
        self.assertIn(str(RAIZ / "requirements-markdown.txt"), comando)

    def test_los_requisitos_basicos_no_traen_el_conversor(self):
        basicos = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
        self.assertNotIn("markitdown", basicos)
        self.assertIn("markitdown", (RAIZ / "requirements-markdown.txt").read_text(encoding="utf-8"))
        self.assertIn('playwright==1.63.0; sys_platform == "win32"', basicos)


if __name__ == "__main__":
    unittest.main()
