import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pandex import calendar_google, credenciales, ia


class Credenciales(unittest.TestCase):
    def test_clave_no_se_escribe_en_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text(json.dumps({"mascota": {"nombre": "Pandex"}}), encoding="utf-8")
            with mock.patch.object(credenciales, "_keyring", None):
                with self.assertRaises(credenciales.ErrorCredencial):
                    credenciales.guardar("ia.openai.key", "sk-falso")
            texto = config.read_text(encoding="utf-8")
        self.assertNotIn("sk-falso", texto)


class InteligenciaArtificial(unittest.TestCase):
    def test_endpoint_remoto_desconocido_se_rechaza(self):
        with self.assertRaises(ValueError):
            ia.AdaptadorCompatible("https://ejemplo.net/v1/chat", "clave-falsa")

    def test_ejecutable_local_sin_shell(self):
        adaptador = ia.AdaptadorLocal("opencode", "opencode")
        with mock.patch.object(ia.subprocess, "run") as run:
            run.return_value.stdout = "Listo"
            run.return_value.stderr = ""
            run.return_value.returncode = 0
            resultado = adaptador.responder("Resume mis tareas")
        comando = run.call_args.args[0]
        self.assertEqual(comando[1:], ["run", "Resume mis tareas"])
        self.assertEqual(run.call_args.kwargs["shell"], False)
        self.assertTrue(resultado.ok)

    def test_no_usa_powershell_shell_en_windows(self):
        adaptador = ia.AdaptadorLocal("antigravity", "antigravity")
        comando = adaptador.comando("; borrar todo")
        self.assertIsInstance(comando, list)
        self.assertIn("; borrar todo", comando)

    def test_accion_escritura_requiere_autorizacion(self):
        with self.assertRaises(ia.PermisoRequerido):
            ia.delegar("prepara una entrega", puede_escribir=True, autorizado=False)


class GoogleCalendar(unittest.TestCase):
    def test_crear_evento_requiere_confirmacion(self):
        with self.assertRaises(calendar_google.PermisoRequerido):
            calendar_google.crear_evento(
                {"summary": "Estudiar", "start": {"dateTime": "2026-11-20T10:00:00-05:00"}},
                autorizado=False,
            )

    def test_actualizar_evento_muestra_payload(self):
        evento = calendar_google.actualizar_evento(
            "abc",
            {"summary": "Estudiar",
             "start": {"dateTime": "2026-11-20T10:00:00-05:00"},
             "end": {"dateTime": "2026-11-20T11:00:00-05:00"}},
            autorizado=True,
        )
        self.assertEqual(evento["evento_id"], "abc")
        self.assertEqual(evento["payload"]["summary"], "Estudiar")

    def test_revocacion_no_toca_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text("{}", encoding="utf-8")
            with mock.patch.object(calendar_google.credenciales, "borrar") as borrar:
                calendar_google.revocar()
            borrar.assert_called_once_with("google.calendar.refresh")
            self.assertNotIn("refresh", config.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
