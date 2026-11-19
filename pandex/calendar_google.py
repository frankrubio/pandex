"""Google Calendar: OAuth y operaciones con confirmación explícita."""

import base64
import hashlib
import http.server
import json
import secrets
import threading
import urllib.parse
import urllib.request
import webbrowser

from . import credenciales

REFRESH_KEY = "google.calendar.refresh"


class PermisoRequerido(RuntimeError):
    pass


def crear_evento(payload, autorizado=False):
    if not autorizado:
        raise PermisoRequerido("Autoriza antes de crear el evento.")
    if not isinstance(payload, dict) or not payload.get("summary"):
        raise ValueError("El evento necesita un título.")
    return {"accion": "crear", "payload": payload}


def actualizar_evento(evento_id, payload, autorizado=False):
    if not autorizado:
        raise PermisoRequerido("Autoriza antes de actualizar el evento.")
    if not evento_id or not isinstance(payload, dict):
        raise ValueError("Falta el evento o sus datos.")
    return {"accion": "actualizar", "evento_id": evento_id, "payload": payload}


def revocar():
    credenciales.borrar(REFRESH_KEY)


def crear_evento_google(payload):
    token = _access_token()
    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    cuerpo = json.dumps(payload).encode("utf-8")
    solicitud = urllib.request.Request(
        url,
        data=cuerpo,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(solicitud, timeout=30) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def actualizar_evento_google(evento_id, payload):
    token = _access_token()
    url = "https://www.googleapis.com/calendar/v3/calendars/" + "primary/events/" + urllib.parse.quote(evento_id)
    cuerpo = json.dumps(payload).encode("utf-8")
    solicitud = urllib.request.Request(
        url,
        data=cuerpo,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="PATCH",
    )
    with urllib.request.urlopen(solicitud, timeout=30) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def _parametros_pkce():
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def conectar(client_id, timeout=300):
    """OAuth de escritorio con PKCE y localhost temporal."""
    if not isinstance(client_id, str) or not client_id.strip():
        raise ValueError("Escribe el ID de cliente OAuth de Google.")
    verifier, challenge = _parametros_pkce()
    estado = secrets.token_urlsafe(24)
    recibido = {}
    terminado = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            consulta = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            recibido.update(consulta)
            respuesta = b"Puedes cerrar esta ventana y volver a Pandex."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(respuesta)))
            self.end_headers()
            self.wfile.write(respuesta)
            terminado.set()

        def log_message(self, _formato, *_args):
            return

    servidor = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    puerto = servidor.server_address[1]
    hilo = threading.Thread(target=servidor.handle_request, daemon=True)
    hilo.start()
    redirect = f"http://127.0.0.1:{puerto}/"
    consulta = urllib.parse.urlencode({
        "client_id": client_id.strip(),
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/calendar",
        "access_type": "offline",
        "prompt": "consent",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": estado,
    })
    webbrowser.open("https://accounts.google.com/o/oauth2/v2/auth?" + consulta)
    terminado.wait(timeout)
    servidor.server_close()
    hilo.join(timeout=1)
    if not terminado.is_set():
        raise RuntimeError("Google no confirmó el acceso a tiempo.")
    if recibido.get("state") != [estado]:
        raise RuntimeError("Google devolvió un estado de autorización distinto.")
    if recibido.get("error"):
        raise RuntimeError("Google rechazó la conexión.")
    codigo = recibido.get("code")
    if not codigo:
        raise RuntimeError("Google no devolvió un código de autorización.")
    cuerpo = urllib.parse.urlencode({
        "client_id": client_id.strip(),
        "code": codigo[0],
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect,
    }).encode("ascii")
    solicitud = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=cuerpo,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(solicitud, timeout=30) as respuesta:
            tokens = json.loads(respuesta.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("Google no pudo completar la autorización.") from exc
    refresh = tokens.get("refresh_token")
    if not refresh:
        raise RuntimeError("Google no devolvió una credencial renovable.")
    credenciales.guardar(REFRESH_KEY, refresh)
    return True


def _access_token():
    refresh = credenciales.leer(REFRESH_KEY)
    if not refresh:
        raise RuntimeError("Conecta Google Calendar antes de usarlo.")
    cuerpo = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh,
    }).encode("ascii")
    solicitud = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=cuerpo,
        method="POST",
    )
    with urllib.request.urlopen(solicitud, timeout=30) as respuesta:
        data = json.loads(respuesta.read().decode("utf-8"))
    token = data.get("access_token")
    if not token:
        raise RuntimeError("Google no renovó el acceso.")
    return token


def consultar_eventos(desde=None, hasta=None):
    token = _access_token()
    parametros = {"calendarId": "primary", "singleEvents": "true", "orderBy": "startTime", "maxResults": "100"}
    if desde:
        parametros["timeMin"] = desde
    if hasta:
        parametros["timeMax"] = hasta
    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events?" + urllib.parse.urlencode(parametros)
    solicitud = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(solicitud, timeout=30) as respuesta:
        data = json.loads(respuesta.read().decode("utf-8"))
    return data.get("items", [])
