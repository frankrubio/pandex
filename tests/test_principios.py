"""Los principios del proyecto que se pueden verificar con el repositorio en la mano.

Ver ``specs/principios.md``. Cada prueba cita el requisito que cuida (``PRI-01``…), así
``grep -rn "PRI-01" tests/`` encuentra la prueba de cada requisito. Si una de estas falla,
no se relaja la prueba: se corrige el repositorio.
"""

import re
import shutil
import subprocess
import unittest
from pathlib import Path

from pandex import tareas
from pandex.extras import EXTRAS
from pandex.rutas import RAIZ, TASKS_DIR

# Archivos que guardan datos de quien usa Pandex. Nunca se versionan.
PERSONALES = (
    re.compile(r"(^|/)config\.json(\.tmp)?$"),
    re.compile(r"(^|/)logs/"),
    re.compile(r"\.log$"),
    re.compile(r"(^|/)historial_canvas\.json$"),
    re.compile(r"(^|/)registro_canvas\.json$"),
    re.compile(r"(^|/)sesion_canvas\.json$"),
    re.compile(r"(^|/)inventario\.json$"),
    re.compile(r"(^|/)onedrive\.json$"),
    re.compile(r"(^|/)rclone\.conf$"),
    re.compile(r"(^|/)browser-profile"),
    re.compile(r"(^|/)cookies\.sqlite"),
    re.compile(r"(^|/)\.env$"),
)

# Lo que nunca se recorre al buscar archivos sin git (no es del proyecto).
_FUERA = {".git", ".venv", "venv", "__pycache__", "logs", ".ruff_cache", ".pytest_cache", ".uv"}


def _hay_git():
    return shutil.which("git") is not None and (RAIZ / ".git").exists()


def _git(*args):
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout


def versionados():
    """Rutas relativas (con ``/``) de los archivos del proyecto.

    Con git: lo que está versionado. Sin git (descargado como ZIP): lo que hay en la carpeta,
    sin ``.venv``, cachés ni datos personales conocidos.
    """
    if _hay_git():
        codigo, salida = _git("ls-files", "-z")
        if codigo == 0:
            return [r for r in salida.split("\0") if r]
    salida = []
    for ruta in RAIZ.rglob("*"):
        relativa = ruta.relative_to(RAIZ)
        if ruta.is_file() and not (_FUERA & set(relativa.parts)):
            salida.append(relativa.as_posix())
    return salida


def _requisitos(archivo):
    """Líneas de dependencias de un requirements, sin comentarios."""
    lineas = []
    for linea in (RAIZ / archivo).read_text(encoding="utf-8").splitlines():
        linea = linea.split("#", 1)[0].strip()
        if linea and not linea.startswith("-"):
            lineas.append(linea)
    return lineas


class Privacidad(unittest.TestCase):
    """P1: los datos de quien usa Pandex nunca llegan a GitHub."""

    def test_gitignore_cubre_datos_personales(self):
        """PRI-01: config.json, logs/ y el entorno virtual quedan fuera de git."""
        rutas = ("config.json", "config.json.tmp", "logs/pandex.log", ".venv/pyvenv.cfg")
        if _hay_git():
            for ruta in rutas:
                codigo, _ = _git("check-ignore", "-q", "--no-index", ruta)
                self.assertEqual(codigo, 0, f"{ruta} no está en .gitignore")
        else:
            texto = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
            for patron in ("config.json", "config.json.tmp", "logs/", ".venv/"):
                self.assertIn(patron, texto, f"falta «{patron}» en .gitignore")

    def test_repositorio_sin_archivos_personales(self):
        """PRI-02: ningún archivo versionado guarda datos de una persona."""
        if not _hay_git():
            self.skipTest("sin git no se puede saber qué está versionado")
        encontrados = [r for r in versionados() if any(p.search(r) for p in PERSONALES)]
        self.assertEqual(encontrados, [], "estos archivos personales están versionados: "
                                          "sácalos con «git rm --cached» y revisa el historial")


class Dependencias(unittest.TestCase):
    """P5 y P7: dependencias fijas y cada una solo en el sistema que la usa."""

    ARCHIVOS = ("requirements.txt", *(datos["archivo"] for datos in EXTRAS.values()))

    # paquete → marcador que debe llevar
    SOLO_EN = {
        "playwright": 'sys_platform == "win32"',
        "winrt-": 'sys_platform == "win32"',
        "selenium": 'sys_platform != "win32"',
    }

    def test_versiones_fijas(self):
        """PLA-06: cada dependencia lleva su versión exacta (==)."""
        for archivo in self.ARCHIVOS:
            for linea in _requisitos(archivo):
                paquete = linea.split(";", 1)[0]
                self.assertIn("==", paquete, f"{archivo}: «{linea}» no tiene versión fija")

    def test_cada_una_en_su_sistema(self):
        """PLA-06: lo que solo sirve en un sistema no se instala en el otro."""
        for archivo in self.ARCHIVOS:
            for linea in _requisitos(archivo):
                nombre = linea.split("==", 1)[0].split("[", 1)[0].strip().lower()
                for prefijo, marcador in self.SOLO_EN.items():
                    if nombre.startswith(prefijo):
                        self.assertIn(marcador, linea, f"{archivo}: «{linea}» necesita «; {marcador}»")

    def test_cada_extra_tiene_su_archivo(self):
        """PES-05: cada función opcional declara su requirements y existe."""
        for extra, datos in EXTRAS.items():
            self.assertTrue((RAIZ / datos["archivo"]).is_file(), f"falta {datos['archivo']} ({extra})")


class Tareas(unittest.TestCase):
    """P9: el contrato de los plug-ins, verificado antes de llegar al usuario."""

    @classmethod
    def setUpClass(cls):
        cls.archivos = sorted(p for p in TASKS_DIR.glob("*.py") if not p.name.startswith("_"))
        cls.tareas = tareas.descubrir()

    def test_todas_cargan(self):
        """EXT-01: ningún archivo de tasks/ se salta por estar roto."""
        self.assertEqual(sorted(t.id for t in self.tareas), sorted(p.stem for p in self.archivos),
                         "alguna tarea no cargó: mira el registro de descubrir()")

    def test_contrato(self):
        """EXT-01: id válido e igual al archivo, nombre, run y extras conocidos."""
        for tarea in self.tareas:
            with self.subTest(tarea=tarea.id):
                self.assertRegex(tarea.id, r"^[a-z][a-z0-9_]*$", "id: minúsculas ASCII y _")
                self.assertTrue(tarea.nombre and tarea.nombre != tarea.id, "falta un nombre para el menú")
                self.assertTrue(callable(getattr(tarea, "run", None)))
                requiere = getattr(tarea, "requiere", None)
                if requiere:
                    self.assertIn(requiere, EXTRAS, f"requiere «{requiere}», que no está en EXTRAS")
        ids = {t.id for t in self.tareas}
        for archivo in self.archivos:
            self.assertIn(archivo.stem, ids, f"{archivo.name}: el id debe ser «{archivo.stem}»")

    def test_tareas_delgadas(self):
        """EXT-02: la lógica vive en pandex/; tasks/ solo la conecta."""
        for archivo in self.archivos:
            lineas = len(archivo.read_text(encoding="utf-8").splitlines())
            self.assertLessEqual(lineas, 120, f"{archivo.name} tiene {lineas} líneas: "
                                              "mueve la lógica a un módulo de pandex/")


class Documentacion(unittest.TestCase):
    """P9: quien llega al proyecto encuentra cada pieza en la documentación."""

    def test_mapa_de_modulos_completo(self):
        """EXT-03: cada módulo de pandex/ figura en docs/arquitectura.md."""
        mapa = (RAIZ / "docs" / "arquitectura.md").read_text(encoding="utf-8")
        paquete = RAIZ / "pandex"
        faltan = [f"pandex/{p.name}" for p in sorted(paquete.glob("*.py"))
                  if p.name != "__init__.py" and f"pandex/{p.name}" not in mapa]
        faltan += [f"pandex/{d.name}/" for d in sorted(paquete.iterdir())
                   if d.is_dir() and (d / "__init__.py").exists() and f"pandex/{d.name}/" not in mapa]
        self.assertEqual(faltan, [], "añade estos módulos al mapa de docs/arquitectura.md")

    def test_cada_spec_tiene_sus_tres_archivos(self):
        """specs/README.md: spec, plan y tareas por carpeta."""
        for carpeta in sorted((RAIZ / "specs").glob("[0-9][0-9][0-9]_*")):
            for nombre in ("spec.md", "plan.md", "tareas.md"):
                self.assertTrue((carpeta / nombre).is_file(), f"falta {carpeta.name}/{nombre}")


class Nombres(unittest.TestCase):
    """Convención: nombres de archivo sin tildes, sin ñ y sin espacios."""

    def test_nombres_de_archivo_portables(self):
        malos = [r for r in versionados() if not r.isascii() or " " in r]
        self.assertEqual(malos, [], "usa solo ASCII y «_» o «-» en los nombres de archivo")


if __name__ == "__main__":
    unittest.main()
