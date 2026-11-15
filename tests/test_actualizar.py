"""Actualizar Pandex: versiones, y aplicar un ZIP sin internet ni tocar tus datos."""

import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from pandex import actualizar
from pandex.config import PANDA_VIEJO, Config

# el bloque que las versiones 1.x y 2.x guardaban en config.json
SPRITE_PIXEL = {"archivo": PANDA_VIEJO, "frame_ancho": 346, "frame_alto": 355,
                "animaciones": {"idle": {"frames": [[0, 0]], "fps": 1}}}


class Versiones(unittest.TestCase):
    def test_comparar(self):
        self.assertTrue(actualizar.es_mas_nueva("2.1.0", "2.0.0"))
        self.assertTrue(actualizar.es_mas_nueva("2.10.0", "2.9.3"))
        self.assertFalse(actualizar.es_mas_nueva("2.0.0", "2.0.0"))
        self.assertFalse(actualizar.es_mas_nueva("1.9", "2.0.0"))

    def test_leer_version_y_novedades(self):
        self.assertEqual(actualizar.leer_version('"""x"""\n\n__version__ = "3.4.5"\n'), "3.4.5")
        self.assertIsNone(actualizar.leer_version("nada"))
        cambios = "# Cambios\n\n## 2.1.0 · hoy\n\n- nuevo\n\n## 2.0.0\n\n- viejo\n"
        self.assertEqual(actualizar.novedades_de(cambios, "2.1.0"), "## 2.1.0 · hoy\n\n- nuevo")


class AplicarZip(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.raiz = self.tmp / "pandex"
        (self.raiz / "pandex").mkdir(parents=True)
        (self.raiz / "tasks").mkdir()
        (self.raiz / "logs").mkdir()
        (self.raiz / "main.py").write_text("viejo", encoding="utf-8")
        (self.raiz / "pandex" / "app.py").write_text("viejo", encoding="utf-8")
        (self.raiz / "requirements.txt").write_text("a==1\n", encoding="utf-8")
        (self.raiz / "config.json").write_text('{"mio": true}', encoding="utf-8")
        (self.raiz / "logs" / "pandex.log").write_text("mi registro", encoding="utf-8")
        (self.raiz / "tasks" / "mi_tarea.py").write_text("mía", encoding="utf-8")

        self.zip = self.tmp / "main.zip"
        with zipfile.ZipFile(self.zip, "w") as z:
            z.writestr("pandex-main/main.py", "nuevo")
            z.writestr("pandex-main/pandex/app.py", "nuevo")
            z.writestr("pandex-main/pandex/nuevo.py", "nuevo")
            z.writestr("pandex-main/requirements.txt", "a==2\n")
            z.writestr("pandex-main/config.json", '{"de_fabrica": true}')
            z.writestr("pandex-main/logs/pandex.log", "otro")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_copia_lo_nuevo_y_respeta_lo_tuyo(self):
        r = actualizar.aplicar(self.raiz, zip_local=self.zip)
        self.assertEqual(r["modo"], "zip")
        self.assertEqual((self.raiz / "main.py").read_text(encoding="utf-8"), "nuevo")
        self.assertEqual((self.raiz / "pandex" / "nuevo.py").read_text(encoding="utf-8"), "nuevo")
        self.assertEqual((self.raiz / "config.json").read_text(encoding="utf-8"), '{"mio": true}')
        self.assertEqual((self.raiz / "logs" / "pandex.log").read_text(encoding="utf-8"), "mi registro")
        self.assertEqual((self.raiz / "tasks" / "mi_tarea.py").read_text(encoding="utf-8"), "mía")
        self.assertTrue(r["dependencias"], "cambió requirements.txt")
        self.assertEqual((r["respaldo"] / "main.py").read_text(encoding="utf-8"), "viejo")

    def test_un_zip_que_no_es_pandex_no_toca_nada(self):
        otro = self.tmp / "otro.zip"
        with zipfile.ZipFile(otro, "w") as z:
            z.writestr("algo/leeme.txt", "hola")
        with self.assertRaises(actualizar.ErrorActualizacion):
            actualizar.aplicar(self.raiz, zip_local=otro)
        self.assertEqual((self.raiz / "main.py").read_text(encoding="utf-8"), "viejo")

    def test_rutas_que_se_salen_se_rechazan(self):
        malo = self.tmp / "malo.zip"
        with zipfile.ZipFile(malo, "w") as z:
            z.writestr("pandex-main/../../fuera.txt", "x")
        with self.assertRaises(actualizar.ErrorActualizacion):
            actualizar.aplicar(self.raiz, zip_local=malo)
        self.assertFalse((self.tmp / "fuera.txt").exists())


class MigrarConfig(unittest.TestCase):
    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())
        self.ruta = self.carpeta / "config.json"

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def test_el_sprite_de_fabrica_deja_paso_al_personaje_nuevo(self):
        self.ruta.write_text(json.dumps({"mascota": {"nombre": "Pygu", "spritesheet": SPRITE_PIXEL,
                                                     "animacion": True}}), encoding="utf-8")
        config = Config(self.ruta)
        self.assertEqual(config.mascota["personaje"], "rusty")
        self.assertEqual(config.mascota["nombre"], "Pygu")
        self.assertNotIn("animacion", config.mascota)
        guardado = json.loads(self.ruta.read_text(encoding="utf-8"))
        self.assertEqual(guardado["version_config"], 4)
        self.assertNotIn("spritesheet", guardado["mascota"], "el de fábrica no se vuelve a guardar")

    def test_el_de_fabrica_con_otros_valores_tambien_pasa_a_rusty(self):
        viejo = {**SPRITE_PIXEL, "archivo": "assets\\panda_robot\\spritesheet.png", "frame_ancho": 192,
                 "frame_alto": 208, "animaciones": {"idle": {"frames": [[0, 0], [0, 1]], "fps": 2}}}
        self.ruta.write_text(json.dumps({"mascota": {"spritesheet": viejo, "posicion": [10, 20]},
                                         "tareas": {"x": {"activa": False}}}), encoding="utf-8")
        config = Config(self.ruta)
        self.assertEqual(config.mascota["personaje"], "rusty")
        self.assertEqual(config.mascota["posicion"], [10, 20])
        self.assertFalse(config.tarea("x")["activa"])
        self.assertNotIn("spritesheet", json.loads(self.ruta.read_text(encoding="utf-8"))["mascota"])

    def test_quien_quedo_en_el_panda_viejo_con_la_v2_pasa_a_rusty(self):
        viejo = {**SPRITE_PIXEL, "frame_ancho": 192}
        self.ruta.write_text(json.dumps({"version_config": 2, "mascota": {
            "personaje": "pixel", "spritesheet": viejo, "nombre": "Pygu"}}), encoding="utf-8")
        config = Config(self.ruta)
        self.assertEqual(config.mascota["personaje"], "rusty")
        self.assertEqual(config.mascota["nombre"], "Pygu")

    def test_un_sprite_propio_pasa_a_rusty_y_su_bloque_se_conserva(self):
        propio = {**SPRITE_PIXEL, "archivo": "assets/mi_gato/sheet.png"}
        for version in (1, 2, 3):
            self.ruta.write_text(json.dumps({"version_config": version, "mascota": {
                "personaje": "pixel", "spritesheet": propio}}), encoding="utf-8")
            config = Config(self.ruta)
            self.assertEqual(config.mascota["personaje"], "rusty", f"v{version}")
            self.assertEqual(config.mascota["spritesheet"]["archivo"], "assets/mi_gato/sheet.png")

    def test_quien_eligio_el_panda_pixel_en_la_2x_pasa_a_panda_clasico(self):
        self.ruta.write_text(json.dumps({"version_config": 3, "mascota": {"personaje": "pixel"}}),
                             encoding="utf-8")
        self.assertEqual(Config(self.ruta).mascota["personaje"], "panda_clasico")

    def test_el_panda_vectorial_ya_no_existe_y_pasa_a_rusty(self):
        self.ruta.write_text(json.dumps({"version_config": 3, "mascota": {"personaje": "vectorial"}}),
                             encoding="utf-8")
        config = Config(self.ruta)
        self.assertEqual(config.mascota["personaje"], "rusty")
        self.assertEqual(config.mascota["logo"], "personaje")
        self.assertEqual(json.loads(self.ruta.read_text(encoding="utf-8"))["version_config"], 4)



class ErroresDeRed(unittest.TestCase):
    """El mensaje dice qué pasó de verdad, no siempre «sin internet»."""

    def _mensaje(self, exc):
        from unittest import mock

        with mock.patch("urllib.request.urlopen", side_effect=exc):
            with self.assertLogs("pandex.actualizar", "WARNING") as logs:
                with self.assertRaises(actualizar.ErrorActualizacion) as ctx:
                    actualizar._abrir("https://raw.githubusercontent.com/x")
        self.assertIn(type(exc).__name__, logs.output[0], "la causa real queda en el registro")
        return str(ctx.exception)

    def test_cada_causa_tiene_su_mensaje(self):
        import ssl
        import urllib.error

        http = urllib.error.HTTPError("u", 429, "Too Many", {}, None)
        self.assertIn("esperar", self._mensaje(http))
        http404 = urllib.error.HTTPError("u", 404, "Not Found", {}, None)
        self.assertIn("404", self._mensaje(http404))
        certificado = urllib.error.URLError(ssl.SSLCertVerificationError("CERTIFICATE_VERIFY_FAILED"))
        self.assertIn("antivirus", self._mensaje(certificado))
        self.assertIn("tardó", self._mensaje(TimeoutError("timed out")))
        self.assertIn("conexión a internet", self._mensaje(urllib.error.URLError("sin red")))


class Obsoletos(unittest.TestCase):
    def test_aparta_lo_que_dejaron_versiones_anteriores_sin_borrarlo(self):
        raiz = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, raiz, ignore_errors=True)
        for relativa in ("Pandex.bat", "pandex/ui/sprites.py", "pandex/ui/__pycache__/sprites.cpython-313.pyc",
                         "assets/rusty/spritesheet.png", "pandex/ui/mascota.py"):
            (raiz / relativa).parent.mkdir(parents=True, exist_ok=True)
            (raiz / relativa).write_text("x", encoding="utf-8")
        self.assertEqual(actualizar.limpiar_obsoletos(raiz), 3)
        self.assertFalse((raiz / "Pandex.bat").exists())
        self.assertFalse((raiz / "assets/rusty").exists(), "la carpeta vacía también se va")
        self.assertFalse((raiz / "pandex/ui/__pycache__/sprites.cpython-313.pyc").exists())
        self.assertTrue((raiz / "pandex/ui/mascota.py").exists(), "lo que sí se usa se queda")
        respaldo = actualizar.DATOS / "respaldos" / f"obsoletos-{actualizar.version_local()}"
        self.assertTrue((respaldo / "Pandex.bat").exists(), "se guarda una copia, no se borra")
        self.assertEqual(actualizar.limpiar_obsoletos(raiz), 0, "la segunda vez no hay nada")


# ---------- spec 012: actualizar sin miedo ----------

API = actualizar.URL_PUBLICADA
DESCARGAS = f"https://github.com/{actualizar.REPO}/releases/download/v9.0.0/"


def _zip_de(carpeta, archivos):
    """Un ZIP como el que publica la CI (``git archive --prefix=pandex-9.0.0/``)."""
    import io

    datos = io.BytesIO()
    with zipfile.ZipFile(datos, "w") as z:
        for nombre, texto in archivos.items():
            z.writestr(f"{carpeta}/{nombre}", texto)
    return datos.getvalue()


def _red_falsa(respuestas):
    """``_abrir`` simulado: ``respuestas[url]`` son bytes, o None para un 404."""
    import io

    pedidos = []

    def abrir(url, timeout=10, si_falta=False):
        pedidos.append(url)
        if url not in respuestas:
            raise AssertionError(f"pedido inesperado: {url}")
        cuerpo = respuestas[url]
        if cuerpo is None:
            if si_falta:
                return None
            raise actualizar.ErrorActualizacion("404")
        return io.BytesIO(cuerpo)

    return abrir, pedidos


class _ConRaiz(unittest.TestCase):
    """Una carpeta de Pandex 1.0.0 de mentira y un ZIP 9.0.0 que cambia, agrega y deja igual."""

    def setUp(self):
        from pandex import vuelta

        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.raiz = self.tmp / "pandex"
        for relativa, texto in {"main.py": "viejo", "pandex/app.py": "viejo", "pandex/igual.py": "igual",
                                "requirements.txt": "a==1\n", "config.json": '{"mio": true}',
                                "tasks/mi_tarea.py": "mía"}.items():
            (self.raiz / relativa).parent.mkdir(parents=True, exist_ok=True)
            (self.raiz / relativa).write_text(texto, encoding="utf-8")
        self.archivos = {"main.py": "nuevo", "pandex/app.py": "nuevo", "pandex/igual.py": "igual",
                         "pandex/nuevo.py": "nuevo", "pandex/__init__.py": '__version__ = "9.0.0"\n',
                         "requirements.txt": "a==1\n"}
        self.zip = _zip_de("pandex-9.0.0", self.archivos)
        self.addCleanup(lambda: vuelta.ARCHIVO.unlink(missing_ok=True))
        vuelta.ARCHIVO.unlink(missing_ok=True)

    def _texto(self, relativa):
        return (self.raiz / relativa).read_text(encoding="utf-8")

    def _publicada(self, sha=None):
        import hashlib

        sha = sha or hashlib.sha256(self.zip).hexdigest()
        return {DESCARGAS + "pandex-9.0.0.zip": self.zip,
                DESCARGAS + "pandex-9.0.0.zip.sha256": f"{sha}  pandex-9.0.0.zip\n".encode()}

    def _aplicar_zip(self):
        archivo = self.tmp / "pandex-9.0.0.zip"
        archivo.write_bytes(self.zip)
        return actualizar.aplicar(self.raiz, zip_local=archivo)

    def _info(self, sha256=True):
        return {"local": "1.0.0", "remota": "9.0.0", "hay_nueva": True, "novedades": "", "etiqueta": "v9.0.0",
                "zip": DESCARGAS + "pandex-9.0.0.zip",
                "sha256": DESCARGAS + "pandex-9.0.0.zip.sha256" if sha256 else None}


class Confirmar(unittest.TestCase):
    """ACT-01: el clic en la mascota abre la ventana; no instala."""

    def test_el_clic_en_la_mascota_no_instala(self):
        from unittest import mock

        from pandex import app as modulo

        app = mock.MagicMock()
        app._nueva = {"local": "1.0.0", "remota": "9.0.0", "hay_nueva": True, "novedades": ""}
        app._dialogos = []
        app.ejecutor.ocupado = False
        app.actualizar_ya = lambda: modulo.PandexApp.actualizar_ya(app)
        with mock.patch.object(modulo, "DialogoActualizacion") as dialogo, \
                mock.patch.object(actualizar, "aplicar") as aplicar:
            self.assertTrue(modulo.PandexApp._clic_en_mascota(app))
        self.assertFalse(dialogo.call_args.kwargs.get("aplicar_ya", False), "sin confirmar no instala")
        aplicar.assert_not_called()


class Publicadas(_ConRaiz):
    """ACT-02: la versión publicada, con su SHA-256."""

    def test_buscar_prefiere_la_version_publicada(self):
        from unittest import mock

        cuerpo = json.dumps({"tag_name": "v9.0.0", "body": "## 9.0.0\n\n- algo",
                             "assets": [{"name": "pandex-9.0.0.zip",
                                         "browser_download_url": DESCARGAS + "pandex-9.0.0.zip"},
                                        {"name": "pandex-9.0.0.zip.sha256",
                                         "browser_download_url": DESCARGAS + "pandex-9.0.0.zip.sha256"}]})
        abrir, pedidos = _red_falsa({API: cuerpo.encode()})
        with mock.patch.object(actualizar, "_abrir", abrir):
            info = actualizar.buscar()
        self.assertEqual((info["remota"], info["etiqueta"], info["hay_nueva"]), ("9.0.0", "v9.0.0", True))
        self.assertEqual(info["zip"], DESCARGAS + "pandex-9.0.0.zip")
        self.assertEqual(info["sha256"], DESCARGAS + "pandex-9.0.0.zip.sha256")
        self.assertIn("- algo", info["novedades"])
        self.assertEqual(pedidos, [API], "no lee main si hay versión publicada")

    def test_sin_versiones_publicadas_usa_main(self):
        from unittest import mock

        abrir, _pedidos = _red_falsa({API: None, actualizar.URL_VERSION: b'__version__ = "9.0.0"\n',
                                     actualizar.URL_NOVEDADES: b"## 9.0.0\n\n- algo\n"})
        with mock.patch.object(actualizar, "_abrir", abrir):
            info = actualizar.buscar()
        self.assertEqual(info["remota"], "9.0.0")
        self.assertNotIn("etiqueta", info)

    def test_con_su_sha256_se_aplica(self):
        from unittest import mock

        abrir, _ = _red_falsa(self._publicada())
        with mock.patch.object(actualizar, "_abrir", abrir), mock.patch.object(actualizar, "modo", return_value="zip"):
            r = actualizar.aplicar(self.raiz, info=self._info())
        self.assertEqual(r["modo"], "zip")
        self.assertEqual(self._texto("main.py"), "nuevo")
        self.assertEqual(self._texto("config.json"), '{"mio": true}')

    def test_un_sha256_que_no_coincide_no_toca_nada(self):
        from unittest import mock

        abrir, _ = _red_falsa(self._publicada(sha="0" * 64))
        with mock.patch.object(actualizar, "_abrir", abrir), mock.patch.object(actualizar, "modo", return_value="zip"):
            with self.assertRaises(actualizar.ErrorActualizacion) as error:
                actualizar.aplicar(self.raiz, info=self._info())
        self.assertIn("no coincide", str(error.exception))
        self.assertEqual(self._texto("main.py"), "viejo")
        self.assertFalse((self.raiz / "pandex" / "nuevo.py").exists())

    def test_sin_sha256_no_se_instala(self):
        from unittest import mock

        abrir, _ = _red_falsa(self._publicada())
        with mock.patch.object(actualizar, "_abrir", abrir), mock.patch.object(actualizar, "modo", return_value="zip"):
            with self.assertRaises(actualizar.ErrorActualizacion):
                actualizar.aplicar(self.raiz, info=self._info(sha256=False))
        self.assertEqual(self._texto("main.py"), "viejo")


class PuntoDeVuelta(_ConRaiz):
    """ACT-03 y ACT-04: guardar el punto de vuelta y volver a la versión anterior."""

    def test_zip_guarda_el_punto(self):
        from pandex import vuelta

        self._aplicar_zip()
        punto = vuelta.leer()
        self.assertEqual((punto["modo"], punto["desde"], punto["hacia"], punto["estado"]),
                         ("zip", actualizar.version_local(), "9.0.0", "probando"))
        self.assertIn("pandex/nuevo.py", punto["agregados"])
        self.assertNotIn("pandex/igual.py", punto["agregados"])
        self.assertEqual((Path(punto["respaldo"]) / "main.py").read_text(encoding="utf-8"), "viejo")

    def test_volver_con_zip(self):
        from pandex import vuelta

        antes = set((actualizar.DATOS / "respaldos").glob("deshecho-*"))
        self._aplicar_zip()
        obsoleto = actualizar.DATOS / "respaldos" / "obsoletos-9.0.0" / "pandex" / "quitado.py"
        obsoleto.parent.mkdir(parents=True, exist_ok=True)
        obsoleto.write_text("lo usaba la anterior", encoding="utf-8")
        self.addCleanup(shutil.rmtree, obsoleto.parent.parent, ignore_errors=True)
        punto = vuelta.volver(self.raiz)
        self.assertEqual(punto["hacia"], "9.0.0")
        self.assertEqual(self._texto("main.py"), "viejo")
        self.assertEqual(self._texto("pandex/app.py"), "viejo")
        self.assertFalse((self.raiz / "pandex" / "nuevo.py").exists())
        self.assertEqual(self._texto("pandex/quitado.py"), "lo usaba la anterior")
        self.assertEqual(self._texto("config.json"), '{"mio": true}')
        self.assertEqual(self._texto("tasks/mi_tarea.py"), "mía")
        nuevos = set((actualizar.DATOS / "respaldos").glob("deshecho-*")) - antes
        self.assertEqual(len(nuevos), 1)
        self.assertTrue((nuevos.pop() / "pandex" / "nuevo.py").is_file(), "lo agregado se aparta, no se borra")
        self.assertIsNone(vuelta.leer(), "ya no hay a dónde volver")

    def _git(self, carpeta, *args):
        import subprocess

        r = subprocess.run(["git", "-C", str(carpeta), *args], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def _repo_con_dos_versiones(self):
        """Un remoto con la 1.0.0 y la 9.0.0 (etiqueta v9.0.0), y un clon en la 1.0.0."""
        import shutil as sh

        if not sh.which("git"):
            self.skipTest("sin git")
        trabajo = self.tmp / "trabajo"
        trabajo.mkdir()
        self._git(trabajo, "init", "-q", "-b", "main")
        self._git(trabajo, "config", "user.email", "prueba@ejemplo.edu")
        self._git(trabajo, "config", "user.name", "Prueba")
        (trabajo / "main.py").write_text("viejo", encoding="utf-8")
        (trabajo / "requirements.txt").write_text("a==1\n", encoding="utf-8")
        self._git(trabajo, "add", ".")
        self._git(trabajo, "commit", "-qm", "1.0.0")
        anterior = self._git(trabajo, "rev-parse", "HEAD")
        (trabajo / "main.py").write_text("nuevo", encoding="utf-8")
        self._git(trabajo, "commit", "-qam", "9.0.0")
        self._git(trabajo, "tag", "v9.0.0")
        remoto = self.tmp / "remoto.git"
        self._git(self.tmp, "clone", "-q", "--bare", str(trabajo), str(remoto))
        clon = self.tmp / "clon"
        self._git(self.tmp, "clone", "-q", str(remoto), str(clon))
        self._git(clon, "reset", "-q", "--hard", anterior)
        return clon, anterior

    def test_git_guarda_el_commit_y_vuelve(self):
        from pandex import vuelta

        clon, anterior = self._repo_con_dos_versiones()
        actualizar.aplicar(clon, info={"etiqueta": "v9.0.0", "remota": "9.0.0"})
        self.assertEqual((clon / "main.py").read_text(encoding="utf-8"), "nuevo")
        punto = vuelta.leer()
        self.assertEqual((punto["modo"], punto["commit"]), ("git", anterior))
        vuelta.volver(clon)
        self.assertEqual(self._git(clon, "rev-parse", "HEAD"), anterior)
        self.assertEqual((clon / "main.py").read_text(encoding="utf-8"), "viejo")

    def test_volver_con_git_no_pisa_tus_cambios(self):
        from pandex import vuelta

        clon, _anterior = self._repo_con_dos_versiones()
        actualizar.aplicar(clon, info={"etiqueta": "v9.0.0", "remota": "9.0.0"})
        (clon / "main.py").write_text("mío", encoding="utf-8")
        with self.assertRaises(vuelta.ErrorVuelta):
            vuelta.volver(clon)
        self.assertEqual((clon / "main.py").read_text(encoding="utf-8"), "mío")


class VueltaAutomatica(_ConRaiz):
    """ACT-05: si la versión nueva no abre, vuelve sola y lo dice una vez."""

    def test_si_la_nueva_no_abre_vuelve_sola(self):
        from pandex import vuelta

        self._aplicar_zip()
        self.assertTrue(vuelta.si_no_abrio(self.raiz))
        self.assertEqual(self._texto("main.py"), "viejo")
        aviso = vuelta.aviso_pendiente()
        self.assertEqual(aviso, f"La versión 9.0.0 no abrió; volví a la {actualizar.version_local()}.")
        self.assertIsNone(vuelta.aviso_pendiente(), "se dice una sola vez")

    def test_si_abrio_bien_no_vuelve(self):
        from pandex import vuelta

        self._aplicar_zip()
        vuelta.arranco()
        self.assertEqual(vuelta.leer()["estado"], "ok")
        self.assertFalse(vuelta.si_no_abrio(self.raiz), "un fallo después de abrir bien no es de la versión")
        self.assertEqual(self._texto("main.py"), "nuevo")

    def test_main_vuelve_y_abre_otra_vez(self):
        from unittest import mock

        import main
        from pandex import vuelta

        with mock.patch.object(vuelta, "si_no_abrio", return_value=True), \
                mock.patch.object(main, "_abrir_otra_vez") as abrir, mock.patch.object(main, "_ventana_de_error"):
            try:
                raise RuntimeError("la versión nueva está rota")
            except RuntimeError:
                main.arranque_fallido(silencioso=False)
        abrir.assert_called_once()


if __name__ == "__main__":
    unittest.main()
