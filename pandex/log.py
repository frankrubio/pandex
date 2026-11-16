"""Registro de eventos en ``logs/pandex.log`` (rota solo al pasar de 1 MB).

Nada secreto llega al archivo (spec 004, PRI-03): un filtro tapa con ``[oculto]`` los valores de
las cookies de tu sesión (``ocultar``), las cabeceras ``Authorization`` y ``Cookie`` y los
parámetros con tokens (``verifier=``, ``access_token=``…), aunque vengan dentro de un error.
"""

import logging
import re
import threading
from logging.handlers import RotatingFileHandler

from .rutas import LOG_FILE

_CONFIGURADO = False
OCULTO = "[oculto]"

_PATRONES = (
    re.compile(r"(?i)\b(authorization\s*[:=]\s*)(?:(?:bearer|basic|token)\s+)?[^\s,;'\"]+"),
    re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?im)\b((?:set-)?cookie\s*:\s*).*$"),
    re.compile(r"(?i)\b((?:access_token|refresh_token|verifier|token|_csrf_token|canvas_session|"
               r"_legacy_normandy_session|log_session_id|_normandy_session)=)[^&\s;,'\"]+"),
    re.compile(r'(?i)("(?:access_token|refresh_token|id_token|token)"\s*:\s*")[^"]+'),  # JSON (rclone)
    re.compile(r"(?im)^(\s*token\s*=\s*).+$"),  # rclone.conf
)
_VALORES = set()
_candado = threading.Lock()
MINIMO = 6  # un valor más corto taparía palabras comunes


def ocultar(*valores):
    """Anota valores secretos (las cookies de la sesión): nunca se escriben en el registro."""
    with _candado:
        _VALORES.update(str(v) for v in valores if v and len(str(v)) >= MINIMO)


def limpiar(texto):
    """``texto`` sin secretos."""
    with _candado:
        valores = sorted(_VALORES, key=len, reverse=True)
    for valor in valores:
        if valor in texto:
            texto = texto.replace(valor, OCULTO)
    for patron in _PATRONES:
        texto = patron.sub(lambda m: m.group(1) + OCULTO, texto)
    return texto


class FiltroSecretos(logging.Filter):
    def filter(self, record):
        try:
            mensaje = record.getMessage()
        except Exception:  # un formato roto no es motivo para perder la línea
            mensaje = str(record.msg)
        limpio = limpiar(mensaje)
        if limpio != mensaje or record.args:
            record.msg, record.args = limpio, None
        return True


def _manejador(ruta):
    """El archivo de registro, con formato y filtro de secretos."""
    handler = RotatingFileHandler(ruta, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    handler.addFilter(FiltroSecretos())
    return handler


def get_logger(nombre="pandex"):
    global _CONFIGURADO
    if not _CONFIGURADO:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        raiz = logging.getLogger("pandex")
        raiz.setLevel(logging.INFO)
        raiz.addHandler(_manejador(LOG_FILE))
        _CONFIGURADO = True
    return logging.getLogger(nombre)
