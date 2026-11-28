"""Descargar material enlazado en Google Drive desde módulos o páginas de Canvas (spec 015).

Muchos docentes suben archivos o documentos como enlaces a ``drive.google.com`` o
``docs.google.com``. Cuando el archivo es solo para cuentas de la universidad y la cuenta
predeterminada del navegador es la personal (``authuser=0``), Google Drive responde con
«Necesitas acceso» o pide iniciar sesión. Pandex prueba primero las demás cuentas ya abiertas en
su perfil (``authuser=1, 2…``) y, si ninguna tiene acceso, abre el navegador para que cambies a tu
cuenta institucional.
"""

import json
import os
import re
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode, urlsplit

from .. import red
from ..log import get_logger, ocultar
from ..rutas import DATOS
from ..tareas import Cancelada, fue_cancelada, si_cancelaron
from . import navegador as _navegador
from .cliente import CanvasError, SinConexion

log = get_logger("pandex.canvas.drive")

ATAJO_DRIVE = DATOS / "sesion_drive.json"
_CANDADO_DRIVE = threading.Lock()
_UA_POR_DEFECTO = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36"

_RE_ARCHIVO_D = re.compile(r"^/file/(?:u/\d+/)?d/([A-Za-z0-9_-]{8,})")
_RE_DOCS_D = re.compile(r"^/(document|presentation|spreadsheets)/(?:u/\d+/)?d/([A-Za-z0-9_-]{8,})")
_RE_AUTHUSER_URL = re.compile(r"/(?:u|a/[^/]+/u)/(\d+)(?:/|$)|[?&]authuser=(\d+)")

_EXTENSIONES_MIME = {
    "application/pdf": ".pdf",
    "application/zip": ".zip",
    "application/x-zip-compressed": ".zip",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/csv": ".csv",
    "text/plain": ".txt",
    "text/x-python": ".py",
}

_MARCAS_DENEGADO = (
    "necesitas acceso",
    "you need access",
    "request access",
    "solicitar acceso",
    "cambiar de cuenta",
    "switch account",
    "accounts.google.com",
    "servicelogin",
    "accountchooser",
    "inicia sesión",
    "sign in",
)


class AccesoDenegadoDrive(CanvasError):
    """Google Drive pidió iniciar sesión o cambiar a la cuenta institucional."""


def extraer_drive(url):
    """``{"tipo", "id", "url"}`` si ``url`` apunta a un archivo o documento de Google Drive; si no, None."""
    if not url:
        return None
    try:
        partes = urlsplit(str(url).strip())
    except ValueError:
        return None
    host = (partes.hostname or "").lower()
    if host not in red.GOOGLE_DRIVE or partes.scheme not in ("http", "https"):
        return None
    if host == "docs.google.com":
        m = _RE_DOCS_D.match(partes.path)
        if m:
            return {"tipo": m.group(1), "id": m.group(2), "url": str(url).strip()}
        return None
    m = _RE_ARCHIVO_D.match(partes.path)
    if m:
        return {"tipo": "file", "id": m.group(1), "url": str(url).strip()}
    if partes.path in ("/open", "/uc", "/download"):
        ids = parse_qs(partes.query).get("id") or []
        if ids and re.fullmatch(r"[A-Za-z0-9_-]{8,}", ids[0]):
            return {"tipo": "file", "id": ids[0], "url": str(url).strip()}
    return None


def _formato_exportacion(tipo, titulo=""):
    bajo = (titulo or "").lower()
    if tipo == "document":
        return "docx" if bajo.endswith(".docx") else "pdf"
    if tipo == "presentation":
        return "pptx" if bajo.endswith(".pptx") else "pdf"
    if tipo == "spreadsheets":
        return "pdf" if bajo.endswith(".pdf") else "xlsx"
    return None


def nombre_inicial(titulo, url):
    """Nombre preliminar para un ítem de Google Drive antes de consultar sus cabeceras."""
    info = extraer_drive(url)
    base = (titulo or "").strip() or (info["id"] if info else "archivo")
    if not info or info["tipo"] == "file":
        return base
    ext = "." + _formato_exportacion(info["tipo"], base)
    return base if base.lower().endswith(ext) else base + ext


def _url_descarga(info, authuser=None, titulo=""):
    tipo, fid = info["tipo"], info["id"]
    if tipo in ("document", "spreadsheets"):
        fmt = _formato_exportacion(tipo, titulo)
        params = {"format": fmt}
        if authuser is not None:
            params["authuser"] = str(authuser)
        return f"https://docs.google.com/{tipo}/d/{fid}/export?{urlencode(params)}"
    if tipo == "presentation":
        fmt = _formato_exportacion(tipo, titulo)
        sufijo = f"?authuser={authuser}" if authuser is not None else ""
        return f"https://docs.google.com/presentation/d/{fid}/export/{fmt}{sufijo}"
    params = {"export": "download", "id": fid}
    if authuser is not None:
        params["authuser"] = str(authuser)
    return f"https://drive.google.com/uc?{urlencode(params)}"


def _url_vista(info):
    tipo, fid = info["tipo"], info["id"]
    if tipo in ("document", "presentation", "spreadsheets"):
        return f"https://docs.google.com/{tipo}/d/{fid}/edit"
    return f"https://drive.google.com/file/d/{fid}/view"


def _es_cookie_google(dominio):
    d = (dominio or "").lstrip(".").lower()
    return d in ("google.com", "drive.google.com", "docs.google.com", "googleusercontent.com") or (
        d.endswith(".google.com") or d.endswith(".googleusercontent.com")
    )


def guardar_atajo_drive(cookies, user_agent, authuser=0):
    """Guarda las cookies de Google Drive y el ``authuser`` institucional en ``DATOS/sesion_drive.json``."""
    propias = [
        {"name": c["name"], "value": c["value"], "domain": c.get("domain", ".google.com"), "path": c.get("path", "/")}
        for c in (cookies or [])
        if isinstance(c, dict) and c.get("name") and c.get("value") and _es_cookie_google(c.get("domain"))
    ]
    ocultar(*(c["value"] for c in propias))  # PRI-03
    try:
        ATAJO_DRIVE.parent.mkdir(parents=True, exist_ok=True)
        temporal = ATAJO_DRIVE.with_name(ATAJO_DRIVE.name + ".tmp")
        fd = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"cookies": propias, "ua": user_agent or _UA_POR_DEFECTO, "authuser": int(authuser or 0)}, fh)
        os.replace(temporal, ATAJO_DRIVE)
    except OSError as exc:
        log.warning("no pude guardar la sesión de Google Drive: %s", exc)


def leer_atajo_drive():
    """``(cookies, user_agent, authuser)`` guardados, o ``([], ua, 0)``."""
    try:
        datos = json.loads(Path(ATAJO_DRIVE).read_text(encoding="utf-8"))
        cookies = datos.get("cookies") or []
        ua = datos.get("ua") or _UA_POR_DEFECTO
        authuser = int(datos.get("authuser") or 0)
        ocultar(*(c.get("value") for c in cookies if isinstance(c, dict)))  # PRI-03
        return cookies, ua, authuser
    except (OSError, ValueError, TypeError):
        return [], _UA_POR_DEFECTO, 0


def olvidar_atajo_drive():
    try:
        ATAJO_DRIVE.unlink(missing_ok=True)
    except OSError as exc:
        log.warning("no pude borrar la sesión de Google Drive: %s", exc)


def _http_get(url, cookies=None, ua=None, timeout=(10, 180)):
    """GET con ``requests`` hacia un host permitido de Google Drive (PRI-04)."""
    import requests

    red.exigir(url, red.GOOGLE_DRIVE)
    cabeceras = {"User-Agent": ua or _UA_POR_DEFECTO}
    try:
        return requests.get(url, cookies=cookies or {}, headers=cabeceras, stream=True, timeout=timeout)
    except requests.RequestException as exc:
        raise SinConexion("Se cortó la conexión con Google Drive") from exc


def _nombre_de_cabeceras(headers, titulo="", tipo_drive="file"):
    disp = (headers or {}).get("Content-Disposition") or (headers or {}).get("content-disposition") or ""
    m_utf8 = re.search(r"filename\*\s*=\s*UTF-8''([^;\r\n]+)", disp, re.IGNORECASE)
    if m_utf8:
        return unquote(m_utf8.group(1).strip().strip('"'))
    m_simple = re.search(r'filename\s*=\s*"([^"]+)"|filename\s*=\s*([^;\s]+)', disp, re.IGNORECASE)
    if m_simple:
        return (m_simple.group(1) or m_simple.group(2) or "").strip().strip('"')
    mime = ((headers or {}).get("Content-Type") or (headers or {}).get("content-type") or "").split(";", 1)[0].strip()
    ext = _EXTENSIONES_MIME.get(mime.lower(), "")
    if not ext and tipo_drive != "file":
        ext = "." + _formato_exportacion(tipo_drive, titulo)
    base = (titulo or "archivo").strip()
    if ext and not base.lower().endswith(ext):
        return base + ext
    return base


def _url_confirmacion_html(html, info, authuser=None):
    """Extrae la URL de confirmación cuando Google Drive avisa del escaneo de virus en archivos grandes."""
    if not html:
        return None
    if "drive.usercontent.google.com/download" not in html and 'name="confirm"' not in html and "confirm=" not in html:
        return None
    params = {"id": info["id"], "export": "download", "confirm": "t"}
    m_confirm = re.search(r'name="confirm"\s+value="([^"]+)"|[?&]confirm=([A-Za-z0-9_-]+)', html)
    if m_confirm:
        params["confirm"] = m_confirm.group(1) or m_confirm.group(2)
    m_uuid = re.search(r'name="uuid"\s+value="([^"]+)"|[?&]uuid=([A-Za-z0-9_-]+)', html)
    if m_uuid:
        params["uuid"] = m_uuid.group(1) or m_uuid.group(2)
    if authuser is not None:
        params["authuser"] = str(authuser)
    return f"https://drive.usercontent.google.com/download?{urlencode(params)}"


def _es_html_denegado(resp, html):
    url_final = (getattr(resp, "url", "") or "").lower()
    if "accounts.google.com" in url_final or "servicelogin" in url_final:
        return True
    bajo = (html or "").lower()
    return any(m in bajo for m in _MARCAS_DENEGADO)


def _intentar_descarga(info, destino_tmp, cookies, ua, authuser, parar=None, titulo=""):
    import requests

    frasco = {c["name"]: c["value"] for c in (cookies or []) if isinstance(c, dict) and c.get("name")}
    url = _url_descarga(info, authuser=authuser, titulo=titulo)
    with _http_get(url, cookies=frasco, ua=ua) as resp:
        if resp.status_code in (401, 403):
            raise AccesoDenegadoDrive("Google Drive pidió tu cuenta institucional")
        if resp.status_code != 200:
            raise CanvasError(f"Google Drive devolvió {resp.status_code}", resp.status_code)
        tipo = ((resp.headers or {}).get("Content-Type") or (resp.headers or {}).get("content-type") or "").lower()
        disp = (resp.headers or {}).get("Content-Disposition") or (resp.headers or {}).get("content-disposition") or ""
        if tipo.startswith("text/html") and "attachment" not in disp.lower():
            html = getattr(resp, "text", "") or ""
            if not html:
                trozos = []
                for trozo in resp.iter_content(1 << 15):
                    trozos.append(trozo)
                    if sum(len(t) for t in trozos) >= (1 << 16):
                        break
                html = b"".join(trozos).decode("utf-8", "replace")
            url_confirmada = _url_confirmacion_html(html, info, authuser=authuser)
            if not url_confirmada:
                if _es_html_denegado(resp, html):
                    raise AccesoDenegadoDrive("Google Drive pidió tu cuenta institucional")
                raise CanvasError("Google Drive devolvió una página en vez del archivo")
            with _http_get(url_confirmada, cookies=frasco, ua=ua) as resp2:
                if resp2.status_code in (401, 403):
                    raise AccesoDenegadoDrive("Google Drive pidió tu cuenta institucional")
                if resp2.status_code != 200:
                    raise CanvasError(f"Google Drive devolvió {resp2.status_code}", resp2.status_code)
                return _guardar_flujo(resp2, destino_tmp, titulo, info["tipo"], parar)
        return _guardar_flujo(resp, destino_tmp, titulo, info["tipo"], parar)


def _guardar_flujo(resp, destino_tmp, titulo, tipo_drive, parar=None):
    import requests

    tipo = ((resp.headers or {}).get("Content-Type") or (resp.headers or {}).get("content-type") or "").lower()
    disp = (resp.headers or {}).get("Content-Disposition") or (resp.headers or {}).get("content-disposition") or ""
    if tipo.startswith("text/html") and "attachment" not in disp.lower():
        raise AccesoDenegadoDrive("Google Drive pidió tu cuenta institucional")
    nombre_real = _nombre_de_cabeceras(resp.headers, titulo, tipo_drive)
    escritos = 0
    try:
        with open(destino_tmp, "wb") as fh:
            for trozo in resp.iter_content(1 << 16):
                if not trozo:
                    continue
                fh.write(trozo)
                escritos += len(trozo)
                if parar is not None and parar():
                    raise Cancelada()
    except requests.RequestException as exc:
        raise SinConexion("Se cortó la conexión con Google Drive") from exc
    if not escritos:
        raise CanvasError("archivo vacío en Google Drive")
    return nombre_real, escritos


def _authuser_de_url(url):
    m = _RE_AUTHUSER_URL.search(url or "")
    if not m:
        return None
    valor = m.group(1) if m.group(1) is not None else m.group(2)
    return int(valor) if valor and valor.isdigit() else None


def iniciar_sesion_drive(ctx, info, navegador="auto", espera_login=300):
    """Abre el navegador de Pandex en el enlace de Google Drive para cambiar a la cuenta institucional."""
    elegido = _navegador.elegir(navegador)
    url = _url_vista(info)
    if ctx is not None:
        if elegido in _navegador.VENTANA_NORMAL:
            ctx.decir("Google Drive pide tu cuenta institucional: te abrí el navegador. "
                      "Cambia a tu cuenta de la universidad y, cuando veas el archivo, cierra la ventana.")
        else:
            ctx.decir("Google Drive pide tu cuenta institucional: te abrí el navegador. "
                      "Cambia a tu cuenta de la universidad hasta ver el archivo.")

    if elegido in _navegador.VENTANA_NORMAL:
        carpeta = _navegador.perfil(elegido)
        inicio = time.monotonic()
        ventana = _navegador.abrir_ventana_normal(elegido, url)
        limite = inicio + espera_login
        while ventana.poll() is None or _navegador.en_uso(elegido, carpeta):
            vencio = time.monotonic() > limite
            if vencio or fue_cancelada(ctx):
                if ventana.poll() is None:
                    ventana.terminate()
                if not vencio:
                    raise Cancelada()
                raise CanvasError("Se acabó el tiempo para iniciar sesión en Google Drive.")
            time.sleep(0.5)
        contexto = _navegador.abrir(elegido, True)
        try:
            page = contexto.pages[0] if contexto.pages else contexto.new_page()
            ua = contexto.user_agent()
            page.goto(url, timeout=60000)
            page.wait_for_timeout(1500)
            cookies = contexto.cookies()
            authuser = _authuser_de_url(getattr(page, "url", "")) or 0
            guardar_atajo_drive(cookies, ua, authuser=authuser)
            return cookies, ua, authuser
        finally:
            contexto.close()

    contexto = _navegador.abrir(elegido, False)
    try:
        page = contexto.pages[0] if contexto.pages else contexto.new_page()
        ua = contexto.user_agent()
        page.goto(url, timeout=60000)
        limite = time.monotonic() + espera_login
        authuser = 0
        while time.monotonic() < limite:
            si_cancelaron(ctx)
            page.wait_for_timeout(1500)
            actual = getattr(page, "url", "") or ""
            detectado = _authuser_de_url(actual)
            if detectado is not None:
                authuser = detectado
            cookies = contexto.cookies()
            try:
                titulo_pag = (page.evaluate("document.title") or "").lower()
            except Exception:
                titulo_pag = ""
            en_login = "accounts.google.com" in actual.lower() or "necesitas acceso" in titulo_pag or (
                "you need access" in titulo_pag or "inicia sesión" in titulo_pag or "sign in" in titulo_pag
            )
            if not en_login and any(_es_cookie_google(c.get("domain")) for c in cookies):
                guardar_atajo_drive(cookies, ua, authuser=authuser)
                return cookies, ua, authuser
        raise CanvasError("Se acabó el tiempo para cambiar a tu cuenta institucional en Google Drive.")
    finally:
        contexto.close()


def descargar(url, destino_tmp, ctx=None, navegador="auto", espera_login=300, parar=None, titulo=""):
    """Descarga un enlace de Google Drive a ``destino_tmp``. Devuelve ``(nombre_real, bytes_escritos)``."""
    info = extraer_drive(url)
    if not info:
        raise CanvasError("El enlace no es un archivo descargable de Google Drive")

    cookies, ua, preferido = leer_atajo_drive()
    orden_cuentas = [preferido] + [n for n in (0, 1, 2, 3) if n != preferido]

    # 1. Probar la cuenta preferida (o sin cuenta si el archivo es público)
    try:
        return _intentar_descarga(info, destino_tmp, cookies, ua, preferido if cookies else None,
                                  parar=parar, titulo=titulo)
    except AccesoDenegadoDrive:
        pass

    # 2. Si ya hay cookies de Google, probar las otras cuentas abiertas (authuser=0, 1, 2, 3)
    if cookies:
        for cuenta in orden_cuentas:
            try:
                resultado = _intentar_descarga(info, destino_tmp, cookies, ua, cuenta, parar=parar, titulo=titulo)
                if cuenta != preferido:
                    guardar_atajo_drive(cookies, ua, authuser=cuenta)
                return resultado
            except AccesoDenegadoDrive:
                continue

    # 3. Abrir el navegador (un solo hilo a la vez) para cambiar a la cuenta institucional
    with _CANDADO_DRIVE:
        cookies_nuevas, ua_nuevo, cuenta_nueva = leer_atajo_drive()
        if cookies_nuevas and (cookies_nuevas != cookies or cuenta_nueva != preferido):
            for cuenta in [cuenta_nueva] + [n for n in (0, 1, 2, 3) if n != cuenta_nueva]:
                try:
                    return _intentar_descarga(info, destino_tmp, cookies_nuevas, ua_nuevo, cuenta,
                                              parar=parar, titulo=titulo)
                except AccesoDenegadoDrive:
                    continue

        cookies, ua, cuenta_inst = iniciar_sesion_drive(ctx, info, navegador=navegador, espera_login=espera_login)
        for cuenta in [cuenta_inst] + [n for n in (0, 1, 2, 3) if n != cuenta_inst]:
            try:
                resultado = _intentar_descarga(info, destino_tmp, cookies, ua, cuenta, parar=parar, titulo=titulo)
                if cuenta != cuenta_inst:
                    guardar_atajo_drive(cookies, ua, authuser=cuenta)
                return resultado
            except AccesoDenegadoDrive:
                continue

    raise CanvasError("Google Drive sigue sin dar acceso al archivo. Verifica que entraste con tu cuenta "
                      "institucional de la universidad.")
