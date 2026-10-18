"""OneDrive en Linux con rclone: cuentas, carpetas, montar y la protección de no escribir fuera."""

import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from pandex import onedrive as od


class ConDatosTemporales(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pandex-od-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for nombre, valor in (("CONF", self.tmp / "rclone.conf"), ("CUENTAS", self.tmp / "onedrive.json"),
                              ("DATOS", self.tmp)):
            parche = mock.patch.object(od, nombre, valor)
            parche.start()
            self.addCleanup(parche.stop)
        self.casa = self.tmp / "casa"
        self.casa.mkdir()


class Carpetas(ConDatosTemporales):
    def test_la_personal_va_en_onedrive_y_las_demas_con_su_nombre(self):
        self.assertEqual(od.carpeta_para("Personal", "personal", self.casa), self.casa / "OneDrive")
        self.assertEqual(od.carpeta_para("UTEC", "business", self.casa), self.casa / "OneDrive - UTEC")

    def test_una_segunda_personal_no_choca_con_la_primera(self):
        od._guardar([od.Cuenta("pandex-personal", "Personal", "personal", str(self.casa / "OneDrive"))])
        self.assertEqual(od.carpeta_para("Hermano", "personal", self.casa), self.casa / "OneDrive - Hermano")

    def test_nombres_raros_no_rompen_la_ruta(self):
        self.assertEqual(od.carpeta_para("UTEC/../x", "business", self.casa).parent, self.casa)

    def test_cada_cuenta_tiene_su_nombre_en_rclone(self):
        od._guardar([od.Cuenta("pandex-utec", "UTEC", "business", "/x")])
        self.assertEqual(od._slug("utec"), "pandex-utec-2")
        self.assertEqual(od._slug("Mi Cuenta Ñ"), "pandex-mi-cuenta")


class Proteccion(ConDatosTemporales):
    def setUp(self):
        super().setUp()
        self.cuenta = od.Cuenta("pandex-utec", "UTEC", "business", str(self.casa / "OneDrive - UTEC"))
        od._guardar([self.cuenta])

    def test_fuera_de_onedrive_no_hace_nada(self):
        with mock.patch.object(od, "montar") as montar:
            self.assertIsNone(od.asegurar(self.casa / "Documentos"))
        montar.assert_not_called()

    def test_dentro_de_onedrive_lo_abre_antes(self):
        with mock.patch.object(od, "montar") as montar:
            self.assertIsNone(od.asegurar(self.cuenta.ruta / "Ciclo 3" / "Cálculo"))
        montar.assert_called_once()

    def test_si_no_se_puede_abrir_avisa_y_no_deja_seguir(self):
        with mock.patch.object(od, "montar", side_effect=od.ErrorOneDrive("sin internet")):
            mensaje = od.asegurar(self.cuenta.ruta / "Ciclo 3")
        self.assertIn("UTEC", mensaje)
        self.assertIn("sin internet", mensaje)

    def test_no_monta_sobre_una_carpeta_con_archivos(self):
        self.cuenta.ruta.mkdir()
        (self.cuenta.ruta / "local.txt").write_text("x")
        with mock.patch.object(od, "disponible", return_value=True), \
                mock.patch("subprocess.run") as run, self.assertRaises(od.ErrorOneDrive):
            od.montar(self.cuenta)
        run.assert_not_called()


class Conectar(ConDatosTemporales):
    def _rclone_falso(self, codigo, lineas, tipo="business"):
        conf = self.tmp / "rclone.conf"

        class Proceso:
            returncode = None

            def __init__(self, comando, **_k):
                self.comando = comando
                self.stdout = iter(lineas)

            def __enter__(self):
                return self

            def __exit__(self, *_a):
                self.returncode = codigo
                if codigo == 0:
                    conf.write_text(f"[{self.comando[5]}]\ntype = onedrive\ndrive_type = {tipo}\n")

            def poll(self):
                return self.returncode

        return Proceso

    def test_conecta_guarda_la_cuenta_y_la_abre(self):
        lineas = ["NOTICE: If your browser doesn't open automatically go to the following link: "
                  "http://127.0.0.1:53682/auth?state=abc\n", "NOTICE: Waiting for code...\n"]
        enlaces = []
        with mock.patch.object(od, "disponible", return_value=True), \
                mock.patch.object(od.subprocess, "Popen", self._rclone_falso(0, lineas)), \
                mock.patch.object(od, "montar") as montar, \
                mock.patch.object(od.Path, "home", return_value=self.casa):
            cuenta = od.Conexion("UTEC").ejecutar(enlaces.append)
        self.assertEqual(enlaces, ["http://127.0.0.1:53682/auth?state=abc"])
        self.assertEqual((cuenta.tipo, Path(cuenta.carpeta)), ("business", self.casa / "OneDrive - UTEC"))
        self.assertEqual([c.remoto for c in od.cuentas()], ["pandex-utec"])
        montar.assert_called_once()

    def test_si_falla_no_deja_nada_a_medias(self):
        with mock.patch.object(od, "disponible", return_value=True), \
                mock.patch.object(od.subprocess, "Popen", self._rclone_falso(1, ["error\n"])), \
                mock.patch.object(od, "_borrar_remoto") as borrar, self.assertRaises(od.ErrorOneDrive):
            od.Conexion("UTEC").ejecutar()
        borrar.assert_called_once_with("pandex-utec")
        self.assertEqual(od.cuentas(), [])

    def test_sin_rclone_dice_como_instalarlo(self):
        with mock.patch.object(od, "disponible", return_value=False), \
                self.assertRaises(od.ErrorOneDrive) as error:
            od.Conexion("UTEC").ejecutar()
        self.assertIn("apt install rclone", str(error.exception))


@unittest.skipUnless(shutil.which("rclone") and shutil.which("fusermount3") and os.path.exists("/dev/fuse"),
                     "hace falta rclone y FUSE")
class MontajeReal(ConDatosTemporales):
    """Con una «nube» que en realidad es otra carpeta: monta, escribe, sube y desmonta."""

    def test_escribir_en_la_carpeta_lo_sube_a_la_nube(self):
        nube = self.tmp / "nube"
        (nube / "Cursos").mkdir(parents=True)
        (self.tmp / "rclone.conf").write_text(f"[pandex-prueba]\ntype = alias\nremote = {nube}\n")
        cuenta = od.Cuenta("pandex-prueba", "Prueba", "business", str(self.casa / "OneDrive - Prueba"))
        od._guardar([cuenta])
        try:
            self.assertIsNone(od.asegurar(cuenta.ruta / "Cursos"))
        except subprocess.SubprocessError as exc:
            self.skipTest(f"no se pudo montar aquí: {exc}")
        if not od.montada(cuenta):
            self.skipTest("FUSE no disponible en este entorno")
        try:
            (cuenta.ruta / "Cursos" / "nuevo.md").write_text("# hola")
            limite = time.monotonic() + 20
            while not (nube / "Cursos" / "nuevo.md").exists() and time.monotonic() < limite:
                time.sleep(0.5)
            self.assertTrue((nube / "Cursos" / "nuevo.md").exists())
        finally:
            od.desmontar(cuenta)
        self.assertFalse(od.montada(cuenta))


if __name__ == "__main__":
    unittest.main()
