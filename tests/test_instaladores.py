"""Instalar sin Python previo (spec 006, PLA-03): el Python portátil se baja fijo y comprobado.

La descarga real y los dos instaladores completos los prueba el job ``instaladores`` de la CI
(con ``PANDEX_PYTHON=portatil``). Aquí, sin internet: el archivo con las huellas, la lógica de
``python_portatil.sh`` con un ``curl`` falso, y que el resto de Pandex respete ``.python/``.
"""

import hashlib
import io
import os
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pandex import red, rutas
from pandex.rutas import RAIZ

FIJO = RAIZ / "herramientas" / "python_portatil.txt"
SISTEMAS = {"linux-x86_64", "linux-aarch64", "windows-x86_64"}


def leer_fijo(ruta=FIJO):
    filas = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if linea.strip() and not linea.startswith("#"):
            sistema, huella, url = linea.split()
            filas[sistema] = (huella, url)
    return filas


class VersionFija(unittest.TestCase):
    def test_cada_sistema_tiene_huella_y_url_de_github(self):
        filas = leer_fijo()
        self.assertEqual(set(filas), SISTEMAS)
        for sistema, (huella, url) in filas.items():
            with self.subTest(sistema=sistema):
                self.assertRegex(huella, r"^[0-9a-f]{64}$")
                red.exigir(url, {"github.com"})  # solo https y solo ese host
                self.assertIn("/astral-sh/python-build-standalone/releases/download/", url)
                self.assertTrue(url.endswith("-install_only_stripped.tar.gz"), url)

    def test_la_version_es_una_que_prueba_la_ci(self):
        versiones = {re.search(r"cpython-(3\.\d+)\.\d+", url).group(1) for _h, url in leer_fijo().values()}
        self.assertEqual(len(versiones), 1, "los tres sistemas con la misma versión")
        ci = (RAIZ / ".github" / "workflows" / "pruebas.yml").read_text(encoding="utf-8")
        self.assertIn(f'"{versiones.pop()}"', ci)


def _tar_con_python(destino, binario="bin/python3"):
    """Un .tar.gz como el de python-build-standalone, con un «python» de mentira."""
    with tarfile.open(destino, "w:gz") as tar:
        datos = b"#!/bin/sh\necho 3.13\n"
        info = tarfile.TarInfo(f"python/{binario}")
        info.size, info.mode = len(datos), 0o755
        tar.addfile(info, io.BytesIO(datos))
    return hashlib.sha256(Path(destino).read_bytes()).hexdigest()


def _ejecutable(ruta, texto):
    ruta.write_text(texto, encoding="utf-8")
    ruta.chmod(ruta.stat().st_mode | stat.S_IXUSR)


@unittest.skipIf(rutas.WINDOWS or not shutil.which("bash"), "python_portatil.sh es para Linux")
class PythonPortatilEnLinux(unittest.TestCase):
    """``herramientas/python_portatil.sh`` con un ``curl`` y un ``uname`` de mentira."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pandex-portatil-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.raiz = self.tmp / "pandex"
        (self.raiz / "herramientas").mkdir(parents=True)
        shutil.copy2(RAIZ / "herramientas" / "python_portatil.sh", self.raiz / "herramientas")
        self.servido = self.tmp / "servido.tar.gz"
        self.huella = _tar_con_python(self.servido)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.pedidos = self.tmp / "pedidos.txt"
        # curl falso: anota la URL y «descarga» el archivo servido en el destino de -o
        _ejecutable(self.bin / "curl", f"""#!/bin/sh
destino=""; url=""
while [ $# -gt 0 ]; do
    case "$1" in -o) destino="$2"; shift ;; http*) url="$1" ;; esac
    shift
done
echo "$url" >> "{self.pedidos}"
cp "{self.servido}" "$destino"
""")
        self.maquina("x86_64")

    def maquina(self, nombre):
        _ejecutable(self.bin / "uname", f"#!/bin/sh\necho {nombre}\n")

    def fijo(self, huella=None):
        url = "https://github.com/astral-sh/python-build-standalone/releases/download/1/cpython-3.13.0.tar.gz"
        (self.raiz / "herramientas" / "python_portatil.txt").write_text(
            "# comentario\n"
            f"linux-x86_64 {huella or self.huella} {url}\n"
            f"windows-x86_64 {'0' * 64} https://github.com/otro.tar.gz\n", encoding="utf-8")

    def correr(self, respuesta="", **entorno):
        env = {**os.environ, "PATH": f"{self.bin}:/usr/bin:/bin", **entorno}
        env.pop("PANDEX_PYTHON", None)
        env.update(entorno)
        return subprocess.run(["bash", "herramientas/python_portatil.sh"], cwd=self.raiz, input=respuesta,
                              capture_output=True, text=True, env=env, timeout=60)

    def sin_restos(self):
        return sorted(p.name for p in self.raiz.iterdir() if p.name.startswith(".python-"))

    def test_baja_comprueba_y_deja_python_en_la_carpeta(self):
        self.fijo()
        r = self.correr(PANDEX_PYTHON="portatil")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.access(self.raiz / ".python" / "bin" / "python3", os.X_OK))
        self.assertEqual(self.sin_restos(), [], "ni el archivo descargado ni la carpeta temporal")
        self.assertIn("cpython-3.13.0.tar.gz", self.pedidos.read_text(encoding="utf-8"))

    def test_si_no_coincide_la_huella_no_lo_usa(self):
        self.fijo(huella="f" * 64)
        r = self.correr(PANDEX_PYTHON="portatil")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("SHA-256", r.stdout)
        self.assertFalse((self.raiz / ".python").exists())
        self.assertEqual(self.sin_restos(), [])

    def test_pregunta_antes_y_respeta_el_no(self):
        self.fijo()
        r = self.correr(respuesta="n\n")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(self.pedidos.exists(), "dijiste que no: no descarga nada")
        self.assertFalse((self.raiz / ".python").exists())
        r = self.correr(respuesta="\n")  # Enter = sí
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.raiz / ".python" / "bin" / "python3").exists())

    def test_equipo_sin_python_portatil_no_descarga(self):
        self.fijo()
        self.maquina("riscv64")
        r = self.correr(PANDEX_PYTHON="portatil")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("riscv64", r.stdout)
        self.assertFalse(self.pedidos.exists())

    def test_un_archivo_sin_python_dentro_no_se_usa(self):
        self.huella = _tar_con_python(self.servido, binario="otra/cosa")
        self.fijo()
        r = self.correr(PANDEX_PYTHON="portatil")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.raiz / ".python").exists())
        self.assertEqual(self.sin_restos(), [])


class LosInstaladoresLoUsan(unittest.TestCase):
    def test_instaladores_bajan_python_solo_si_hace_falta(self):
        sh = (RAIZ / "instalar.sh").read_text(encoding="utf-8")
        bat = (RAIZ / "instalar.bat").read_text(encoding="utf-8")
        self.assertIn("herramientas/python_portatil.sh", sh)
        self.assertIn(r"herramientas\python_portatil.bat", bat)
        bat_portatil = (RAIZ / "herramientas" / "python_portatil.bat").read_text(encoding="utf-8")
        for texto in ("python_portatil.txt", "Get-FileHash", "SHA256", "tar -xzf", "PANDEX_PYTHON"):
            self.assertIn(texto, bat_portatil)
        for texto in ("--clear", ".python"):  # un .venv roto (carpeta movida) se rehace
            self.assertIn(texto, sh)
            self.assertIn(texto, bat)

    def test_los_bat_tienen_fin_de_linea_de_windows(self):
        atributos = (RAIZ / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("*.bat text eol=crlf", atributos)

    def test_python_portatil_fuera_de_git(self):
        ignorados = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
        for ruta in (".python/", ".python-nuevo/", ".python-descarga.tar.gz"):
            self.assertIn(ruta, ignorados)


class ElRestoLoRespeta(unittest.TestCase):
    def test_actualizar_no_toca_el_python_portatil(self):
        from pandex import actualizar

        self.assertIn(".python", actualizar.PROTEGIDOS)

    def test_desinstalar_lo_quita(self):
        from pandex import desinstalar

        tmp = Path(tempfile.mkdtemp(prefix="pandex-desinstalar-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / ".venv").mkdir()
        (tmp / ".python" / "bin").mkdir(parents=True)
        with mock.patch.object(desinstalar, "DATOS", tmp / "no-hay"), \
                mock.patch.object(desinstalar, "inventario") as inventario:
            inventario.todo.return_value = []
            rutas_plan = [r for paso in desinstalar.plan(tmp) for r in paso.rutas]
        self.assertIn(tmp / ".python", rutas_plan)
        for nombre in ("desinstalar.sh", "desinstalar.bat"):
            self.assertIn(".python", (RAIZ / nombre).read_text(encoding="utf-8"), nombre)

    def test_el_peso_lo_cuenta_aparte(self):
        """Hace las veces del Python del sistema, que no cuenta (spec 002); se informa aparte."""
        import importlib.util

        spec = importlib.util.spec_from_file_location("medir_peso", RAIZ / "herramientas" / "medir_peso.py")
        medir_peso = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(medir_peso)
        tmp = Path(tempfile.mkdtemp(prefix="pandex-peso-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / ".python" / "bin").mkdir(parents=True)
        (tmp / ".python" / "bin" / "python3").write_bytes(b"x" * 300)
        (tmp / "main.py").write_bytes(b"x" * 100)
        r = medir_peso.medir(tmp, tmp / "no-hay")
        self.assertEqual((r["proyecto_sin_venv"], r["python_portatil"], r["total"]), (100, 300, 100))


if __name__ == "__main__":
    unittest.main()
