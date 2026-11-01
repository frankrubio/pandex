"""Sin residuos (spec 003): pip no deja copias fuera de Pandex y actualizar quita lo que sobra."""

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pandex import actualizar, extras, limpieza, paquetes

RAIZ = Path(__file__).resolve().parent.parent


class PipSinCache(unittest.TestCase):
    """RES-02: ninguna llamada a pip deja caché ni compila todo."""

    def test_pip_sin_cache_en_los_instaladores(self):
        for nombre in ("instalar.sh", "instalar.bat"):
            texto = (RAIZ / nombre).read_text(encoding="utf-8")
            self.assertRegex(texto, r"PIP_NO_CACHE_DIR=1", nombre)
            for linea in texto.splitlines():
                if re.search(r"pip install -r", linea):
                    self.assertIn("--no-compile", linea, f"{nombre}: {linea.strip()}")

    def test_pip_solo_desde_paquetes(self):
        """Nadie más en pandex/ llama a «pip install»: así nadie se olvida de las opciones."""
        for archivo in (RAIZ / "pandex").rglob("*.py"):
            if archivo.name == "paquetes.py":
                continue
            self.assertNotRegex(archivo.read_text(encoding="utf-8"), r"[\"']pip[\"'],\s*[\"']install",
                                archivo.name)

    def test_instalar_pasa_sin_cache_y_sin_pyc(self):
        with mock.patch.object(paquetes.subprocess, "run", return_value=mock.Mock(returncode=0)) as run:
            paquetes.instalar([RAIZ / "requirements.txt"], "python")
        comando = run.call_args.args[0]
        self.assertIn("--no-cache-dir", comando)
        self.assertIn("--no-compile", comando)

    def test_instalar_fallido_avisa(self):
        with mock.patch.object(paquetes.subprocess, "run", return_value=mock.Mock(returncode=1, stderr="sin red")), \
                self.assertRaises(paquetes.ErrorPaquetes):
            paquetes.instalar([RAIZ / "requirements.txt"], "python")


class Huerfanos(unittest.TestCase):
    """RES-06: tras actualizar, .venv no guarda paquetes que nadie pide."""

    def test_calcula_con_dependencias_y_extras(self):
        """En este mismo Python: lo que pide requirements.txt (y sus dependencias) no sobra."""
        with tempfile.TemporaryDirectory() as tmp:
            req = Path(tmp) / "requirements.txt"
            req.write_text("requests\n", encoding="utf-8")
            sobran = paquetes.huerfanos([req])
        for necesario in ("requests", "urllib3", "idna", "certifi", "pip"):
            self.assertNotIn(necesario, sobran)

    def test_ante_un_error_no_quita_nada(self):
        with mock.patch.object(paquetes.subprocess, "run", return_value=mock.Mock(returncode=1, stdout="", stderr="x")):
            self.assertEqual(paquetes.huerfanos([RAIZ / "requirements.txt"]), [])

    def test_desinstalar_nunca_quita_pip(self):
        with mock.patch.object(paquetes.subprocess, "run", return_value=mock.Mock(returncode=0)) as run:
            quitados = paquetes.desinstalar(["pandas", "pip", "setuptools", "Wheel"], "python")
        self.assertEqual(quitados, ["pandas"])
        self.assertEqual(run.call_args.args[0][-1], "pandas")

    def test_actualizar_quita_huerfanos(self):
        with mock.patch.object(extras, "instalados_en", return_value=[]), \
                mock.patch.object(paquetes, "instalar"), \
                mock.patch.object(paquetes, "es_del_proyecto", return_value=True), \
                mock.patch.object(paquetes, "huerfanos", return_value=["playwright", "pandas"]), \
                mock.patch.object(paquetes, "desinstalar", side_effect=lambda p, py: p) as desinstalar:
            quitados = actualizar.instalar_dependencias(RAIZ)
        self.assertEqual(quitados, ["playwright", "pandas"])
        desinstalar.assert_called_once()

    def test_si_no_puede_quitar_igual_termina_de_actualizar(self):
        with mock.patch.object(extras, "instalados_en", return_value=[]), \
                mock.patch.object(paquetes, "instalar"), \
                mock.patch.object(paquetes, "es_del_proyecto", return_value=True), \
                mock.patch.object(paquetes, "huerfanos", return_value=["pandas"]), \
                mock.patch.object(paquetes, "desinstalar", side_effect=paquetes.ErrorPaquetes("x")):
            self.assertEqual(actualizar.instalar_dependencias(RAIZ), [])

    def test_nunca_quita_paquetes_fuera_del_venv_de_pandex(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            propio = raiz / ".venv" / "bin" / "python"
            propio.parent.mkdir(parents=True)
            propio.touch()
            self.assertTrue(paquetes.es_del_proyecto(propio, raiz))
            self.assertFalse(paquetes.es_del_proyecto("/usr/bin/python3", raiz))
        with mock.patch.object(extras, "instalados_en", return_value=[]), \
                mock.patch.object(paquetes, "instalar"), \
                mock.patch.object(paquetes, "huerfanos") as huerfanos:
            self.assertEqual(actualizar.instalar_dependencias(RAIZ / "no-existe"), [])
        huerfanos.assert_not_called()

    def test_quitar_un_extra_deja_la_base(self):
        with mock.patch.object(extras, "instalados_en", return_value=["markdown"]), \
                mock.patch.object(paquetes, "huerfanos", return_value=["markitdown", "magika"]) as huerfanos, \
                mock.patch.object(paquetes, "desinstalar", side_effect=lambda p, py: p):
            quitados = extras.quitar("markdown", "python", RAIZ)
        self.assertEqual(quitados, ["markitdown", "magika"])
        self.assertEqual(huerfanos.call_args.args[0], [RAIZ / "requirements.txt"], "sin el archivo del extra")


class Limites(unittest.TestCase):
    """RES-04/RES-05 y «Liberar espacio» (ADR-0001, D4)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)

    def crear(self, carpeta, nombres, es_carpeta=False):
        import os
        import time

        carpeta.mkdir(parents=True, exist_ok=True)
        ahora = time.time()
        for i, nombre in enumerate(nombres):
            ruta = carpeta / nombre
            if es_carpeta:
                ruta.mkdir()
                (ruta / "a.txt").write_text("x" * 100, encoding="utf-8")
            else:
                ruta.write_text("{}", encoding="utf-8")
            os.utime(ruta, (ahora - 100 * (len(nombres) - i), ahora - 100 * (len(nombres) - i)))

    def test_respaldos_con_limite(self):
        respaldos = self.tmp / "respaldos"
        self.crear(respaldos, [f"2.{i}.0" for i in range(5)], es_carpeta=True)
        liberado = limpieza.limitar(respaldos, "*", 2)
        self.assertEqual(sorted(p.name for p in respaldos.iterdir()), ["2.3.0", "2.4.0"])
        self.assertEqual(liberado, 300)

    def test_copias_de_config_con_limite(self):
        self.crear(self.tmp, [f"config-canvas-anterior-2026100{i}.json" for i in range(5)] + ["otro.json"])
        limpieza.limitar(self.tmp, "config-canvas-anterior-*.json", 3)
        quedan = sorted(p.name for p in self.tmp.iterdir())
        self.assertEqual(len(quedan), 4)
        self.assertIn("otro.json", quedan, "solo toca lo que coincide")
        self.assertNotIn("config-canvas-anterior-20261000.json", quedan)

    def test_caches_viejas_con_su_tamano(self):
        cache = self.tmp / "cache"
        (cache / "pip" / "http-v2").mkdir(parents=True)
        (cache / "pip" / "http-v2" / "rueda").write_bytes(b"x" * 2048)
        with mock.patch.object(limpieza, "WINDOWS", False), \
                mock.patch.dict("os.environ", {"XDG_CACHE_HOME": str(cache)}), \
                mock.patch.object(limpieza.Path, "home", return_value=self.tmp / "casa"):
            elementos = limpieza.caches_viejas()
        self.assertEqual([(e.clave, e.tamano) for e in elementos], [("pip", 2048)])

    def test_liberar_borra_y_cuenta(self):
        carpeta = self.tmp / "sobra"
        carpeta.mkdir()
        (carpeta / "x").write_bytes(b"x" * 10)
        elemento = limpieza.Elemento("pip", "Caché", [carpeta], 10)
        liberado, fallidos = limpieza.liberar([elemento])
        self.assertEqual((liberado, fallidos), (10, []))
        self.assertFalse(carpeta.exists())

    def test_otra_copia_va_a_la_papelera_si_se_puede(self):
        copia = self.tmp / "pandex-viejo"
        copia.mkdir()
        papelera = mock.Mock(return_value=True)
        limpieza.liberar([limpieza.Elemento(f"copia:{copia}", "Otra copia", [copia], 5)], papelera)
        papelera.assert_called_once_with(copia)

    def test_lo_que_no_se_pudo_borrar_se_lista(self):
        ruta = self.tmp / "en-uso"
        ruta.mkdir()
        with mock.patch.object(limpieza, "_borrar", side_effect=PermissionError("en uso")):
            liberado, fallidos = limpieza.liberar([limpieza.Elemento("pip", "Caché", [ruta], 10)])
        self.assertEqual((liberado, fallidos), (0, [ruta]))

    def test_recuerda_todas_las_copias_anteriores(self):
        from pandex import accesos

        vieja, nueva = self.tmp / "vieja", self.tmp / "nueva"
        for c in (vieja, nueva):
            c.mkdir()
            (c / "main.py").touch()
        registro = self.tmp / "instalacion.json"
        registro.write_text(json.dumps({"carpeta": str(vieja)}), encoding="utf-8")
        with mock.patch.object(accesos, "INSTALACION", registro), \
                mock.patch.object(accesos, "crear_en_escritorio"), \
                mock.patch.object(accesos, "arranca_con_el_sistema", return_value=False):
            accesos.instalar_aqui(nueva, nueva / "config.json")
            self.assertEqual(accesos.instalaciones_anteriores(nueva), [vieja])
            with mock.patch.object(limpieza, "tamano", return_value=1):
                self.assertEqual([e.rutas for e in limpieza.copias_anteriores(nueva)], [[vieja]])

    def test_no_ofrece_una_copia_que_contiene_a_esta(self):
        """Si descomprimiste la versión nueva dentro de la vieja, borrar la vieja borraría esta."""
        from pandex import accesos

        vieja = self.tmp / "vieja"
        nueva = vieja / "pandex-nuevo"
        dentro = self.tmp / "otra"
        afuera = dentro / "sub"
        for c in (vieja, nueva, dentro, afuera):
            c.mkdir(parents=True)
            (c / "main.py").touch()
        registro = self.tmp / "instalacion.json"
        registro.write_text(json.dumps({"carpeta": str(vieja), "anteriores": [str(nueva / "x")]}),
                            encoding="utf-8")
        with mock.patch.object(accesos, "INSTALACION", registro):
            self.assertEqual(accesos.instalaciones_anteriores(nueva), [])
        registro.write_text(json.dumps({"carpeta": str(afuera)}), encoding="utf-8")
        with mock.patch.object(accesos, "INSTALACION", registro):
            self.assertEqual(accesos.instalaciones_anteriores(dentro), [])  # una copia dentro de esta

    def test_no_ofrece_una_copia_que_guarda_tus_cursos_o_tus_datos(self):
        from pandex import accesos

        vieja = self.tmp / "vieja"
        cursos = vieja / "Cursos"
        cursos.mkdir(parents=True)
        (vieja / "main.py").touch()
        with mock.patch.object(accesos, "instalaciones_anteriores", return_value=[vieja]):
            self.assertEqual(limpieza.copias_anteriores(self.tmp / "nueva", protegidas=[cursos]), [])
            with mock.patch.object(limpieza, "tamano", return_value=1):
                self.assertEqual(len(limpieza.copias_anteriores(self.tmp / "nueva", protegidas=[])), 1)

    def test_lee_la_carpeta_de_cursos_para_protegerla(self):
        raiz = self.tmp / "pandex"
        raiz.mkdir()
        (raiz / "config.json").write_text(json.dumps({"tareas": {"sync_canvas": {"destino": "/x/Cursos"}}}),
                                          encoding="utf-8")
        self.assertIn(Path("/x/Cursos"), limpieza.carpetas_protegidas(raiz))

    def test_una_copia_que_no_va_a_la_papelera_no_se_borra_para_siempre(self):
        """P4: borrar otra copia de Pandex necesita poder deshacerse."""
        copia = self.tmp / "copia"
        copia.mkdir()
        (copia / "main.py").touch()
        liberado, fallidos = limpieza.liberar(
            [limpieza.Elemento(f"copia:{copia}", "Otra copia", [copia], 5)], lambda _r: False)
        self.assertTrue((copia / "main.py").exists())
        self.assertEqual((liberado, fallidos), (0, [copia]))
        liberado, fallidos = limpieza.liberar([limpieza.Elemento(f"copia:{copia}", "Otra copia", [copia], 5)])
        self.assertTrue(copia.exists())  # sin papelera, tampoco

    def test_al_estrenar_version_sin_venv_propio_no_toca_paquetes(self):
        with mock.patch.object(limpieza, "DATOS", self.tmp), \
                mock.patch.object(paquetes, "huerfanos") as huerfanos, \
                mock.patch.object(limpieza, "externos", return_value=[]):
            r = limpieza.al_estrenar_version(self.tmp)
        huerfanos.assert_not_called()
        self.assertEqual(r, {"liberado": 0, "externos": []})


class Desinstalar(unittest.TestCase):
    """RES-07 a RES-10: desinstalar quita todo lo que Pandex creó, salvo tus cursos."""

    def setUp(self):
        from pandex import accesos, desinstalar, despertador, inventario, onedrive

        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)
        self.casa = self.tmp / "casa"
        self.datos = self.tmp / "datos"
        self.raiz = self.tmp / "pandex"
        self.cursos = self.casa / "OneDrive" / "Cursos"
        for carpeta in (self.casa / "Escritorio", self.datos, self.raiz / ".venv", self.cursos):
            carpeta.mkdir(parents=True)
        (self.cursos / "Sem 1.pdf").write_bytes(b"mio")
        (self.raiz / "config.json").write_text("{}", encoding="utf-8")
        entorno = {"XDG_CONFIG_HOME": str(self.casa / ".config"), "XDG_DATA_HOME": str(self.casa / ".local/share")}
        parches = [
            mock.patch.dict("os.environ", entorno),
            mock.patch.object(Path, "home", return_value=self.casa),
            mock.patch.object(accesos, "WINDOWS", False),
            mock.patch.object(desinstalar, "WINDOWS", False),
            mock.patch.object(despertador, "WINDOWS", False),
            mock.patch.object(desinstalar, "DATOS", self.datos),
            mock.patch.object(inventario, "ARCHIVO", self.datos / "inventario.json"),
            mock.patch.object(accesos, "_carpeta_escritorio", return_value=self.casa / "Escritorio"),
            mock.patch.object(accesos.subprocess, "run"),  # gio
            mock.patch.object(onedrive, "disponible", return_value=False),
            mock.patch.object(despertador, "_systemctl"),
        ]
        for parche in parches:
            parche.start()
            self.addCleanup(parche.stop)
        self.accesos, self.desinstalar, self.despertador, self.inventario = accesos, desinstalar, despertador, inventario

    def instalar_todo(self):
        self.accesos._crear_linux(self.tmp / "no-hay.ico")
        self.accesos.activar_arranque()
        with mock.patch.object(self.despertador.shutil, "which", return_value="/usr/bin/systemctl"):
            self.despertador._instalar_linux({"sync_canvas": "0 19 * * *"})
        (self.datos / "historial_canvas.json").write_text("{}", encoding="utf-8")

    def test_inventario_registra_accesos_y_despertador(self):
        self.instalar_todo()
        motivos = sorted(d["motivo"] for d in self.inventario.todo())
        self.assertEqual(motivos, ["acceso directo"] * 3 + ["despertador"] * 2)
        self.accesos.desactivar_arranque()
        self.assertEqual(len(self.inventario.todo()), 4)

    def test_desinstalar_quita_todo_lo_inventariado(self):
        self.instalar_todo()
        pasos = self.desinstalar.plan(self.raiz, conservar_config=True)
        nombres = " ".join(p.nombre for p in pasos)
        for esperado in ("Despertador", "Accesos directos", "Datos de Pandex", "Entorno de Python"):
            self.assertIn(esperado, nombres)
        quedan = self.desinstalar.ejecutar(pasos)
        self.assertEqual(quedan, [])
        restos = [p for p in self.casa.rglob("*") if p.is_file() and not p.is_relative_to(self.cursos)]
        self.assertEqual(restos, [], "no queda nada de Pandex en la casa")
        self.assertFalse(self.datos.exists())
        self.assertFalse((self.raiz / ".venv").exists())

    def test_desinstalar_no_toca_la_carpeta_de_cursos(self):
        self.instalar_todo()
        self.desinstalar.ejecutar(self.desinstalar.plan(self.raiz, conservar_config=False))
        self.assertEqual((self.cursos / "Sem 1.pdf").read_bytes(), b"mio")

    def test_desinstalar_puede_conservar_config(self):
        self.desinstalar.ejecutar(self.desinstalar.plan(self.raiz, conservar_config=True))
        self.assertTrue((self.raiz / "config.json").exists())
        self.desinstalar.ejecutar(self.desinstalar.plan(self.raiz, conservar_config=False))
        self.assertFalse((self.raiz / "config.json").exists())

    def test_desinstalar_pide_confirmacion(self):
        self.instalar_todo()
        with mock.patch.object(self.desinstalar, "RAIZ", self.raiz), \
                mock.patch("builtins.input", side_effect=["", "n"]), \
                mock.patch("builtins.print"):
            self.assertEqual(self.desinstalar._cli([]), 2)
        self.assertTrue(self.datos.exists())
        self.assertTrue((self.casa / "Escritorio" / "pandex.desktop").exists())

    def test_hay_un_desinstalador_por_sistema(self):
        for nombre in ("desinstalar.sh", "desinstalar.bat"):
            self.assertIn("pandex.desinstalar", (RAIZ / nombre).read_text(encoding="utf-8"), nombre)


if __name__ == "__main__":
    unittest.main()


class BorrarVenvEnWindows(unittest.TestCase):
    def test_espera_con_ping_y_no_con_timeout(self):
        """«timeout» falla al instante sin consola (DETACHED_PROCESS): borraría el .venv en uso."""
        from pandex.ui import desinstalar as ui_desinstalar

        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        (tmp / ".venv").mkdir()
        with mock.patch.object(ui_desinstalar, "RAIZ", tmp), \
                mock.patch.object(ui_desinstalar.subprocess, "Popen") as popen:
            ui_desinstalar._borrar_venv_al_salir()
        comando = " ".join(popen.call_args.args[0])
        self.assertIn("ping -n", comando)
        self.assertNotIn("timeout", comando)
        self.assertIn(str(tmp / ".venv"), comando)

