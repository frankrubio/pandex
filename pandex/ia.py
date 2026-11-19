"""Adaptadores de inteligencia artificial sin shell ni acciones destructivas."""

import shutil
import subprocess
import json
import urllib.request
from pathlib import Path
import urllib.parse

ENDPOINTS_PERMITIDOS = frozenset({
    "api.openai.com",
    "api.anthropic.com",
    "openrouter.ai",
    "api.x.ai",
    "generativelanguage.googleapis.com",
})


class PermisoRequerido(RuntimeError):
    pass


class ResultadoIA:
    def __init__(self, ok, texto="", error=""):
        self.ok = ok
        self.texto = texto
        self.error = error


class AdaptadorLocal:
    """Ejecuta una CLI local con argumentos separados y sin shell."""

    def __init__(self, proveedor, ejecutable):
        self.proveedor = proveedor
        self.ejecutable = ejecutable

    def comando(self, prompt):
        exe = shutil.which(self.ejecutable) if not __import__("os").path.isabs(self.ejecutable) else self.ejecutable
        if not exe:
            raise RuntimeError(f"No encontré «{self.ejecutable}». Instala la CLI y vuelve a probar.")
        if self.proveedor == "opencode":
            return [exe, "run", prompt]
        if self.proveedor == "antigravity":
            return [exe, "agent", "--prompt", prompt]
        return [exe, prompt]

    def responder(self, prompt):
        try:
            proc = subprocess.run(
                self.comando(prompt),
                shell=False,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return ResultadoIA(False, error=str(exc))
        if proc.returncode != 0:
            detalle = (proc.stderr or proc.stdout or "La IA terminó con un error.").strip()
            return ResultadoIA(False, error=detalle[:500])
        return ResultadoIA(True, texto=(proc.stdout or "").strip())


class AdaptadorCompatible:
    """Proveedor HTTP compatible con una API de chat."""

    def __init__(self, endpoint, api_key, model=""):
        host = urllib.parse.urlparse(endpoint).hostname or ""
        if host not in ENDPOINTS_PERMITIDOS:
            raise ValueError("Endpoint no permitido. Usa un proveedor compatible aprobado.")
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model

    def responder(self, prompt):
        cuerpo = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        solicitud = urllib.request.Request(
            self.endpoint,
            data=cuerpo,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(solicitud, timeout=300) as respuesta:
                data = json.loads(respuesta.read().decode("utf-8"))
        except Exception as exc:
            return ResultadoIA(False, error=str(exc)[:500])
        texto = ""
        try:
            texto = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return ResultadoIA(False, error="El proveedor respondió un formato desconocido.")
        return ResultadoIA(True, texto=texto)


def guardar_estado(carpeta, proveedor, ejecutable="", endpoint="", model=""):
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    estado = {
        "proveedor": proveedor,
        "ejecutable": ejecutable,
        "endpoint": endpoint,
        "model": model,
    }
    import json
    (carpeta / "estado.json").write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    return estado


def leer_estado(carpeta):
    ruta = Path(carpeta) / "estado.json"
    if not ruta.is_file():
        return {}
    import json
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def delegar(prompt, puede_escribir=False, autorizado=False, adaptador=None):
    """Delegar texto o una tarea sin permitir operaciones destructivas."""
    if puede_escribir and not autorizado:
        raise PermisoRequerido("Autoriza primero lo que puede cambiar.")
    if adaptador is None:
        raise RuntimeError("Conecta una IA antes de delegar una tarea.")
    return adaptador.responder(prompt)
