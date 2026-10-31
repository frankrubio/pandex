"""Sin residuos (spec 003): pip no deja copias fuera de Pandex y actualizar quita lo que sobra."""

import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pandex import actualizar, extras, paquetes

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
                mock.patch.object(paquetes, "huerfanos", return_value=["playwright", "pandas"]), \
                mock.patch.object(paquetes, "desinstalar", side_effect=lambda p, py: p) as desinstalar:
            quitados = actualizar.instalar_dependencias(RAIZ)
        self.assertEqual(quitados, ["playwright", "pandas"])
        desinstalar.assert_called_once()

    def test_si_no_puede_quitar_igual_termina_de_actualizar(self):
        with mock.patch.object(extras, "instalados_en", return_value=[]), \
                mock.patch.object(paquetes, "instalar"), \
                mock.patch.object(paquetes, "huerfanos", return_value=["pandas"]), \
                mock.patch.object(paquetes, "desinstalar", side_effect=paquetes.ErrorPaquetes("x")):
            self.assertEqual(actualizar.instalar_dependencias(RAIZ), [])

    def test_quitar_un_extra_deja_la_base(self):
        with mock.patch.object(extras, "instalados_en", return_value=["markdown"]), \
                mock.patch.object(paquetes, "huerfanos", return_value=["markitdown", "magika"]) as huerfanos, \
                mock.patch.object(paquetes, "desinstalar", side_effect=lambda p, py: p):
            quitados = extras.quitar("markdown", "python", RAIZ)
        self.assertEqual(quitados, ["markitdown", "magika"])
        self.assertEqual(huerfanos.call_args.args[0], [RAIZ / "requirements.txt"], "sin el archivo del extra")


if __name__ == "__main__":
    unittest.main()
