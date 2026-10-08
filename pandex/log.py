"""Registro de eventos en ``logs/pandex.log`` (rota solo al pasar de 1 MB)."""

import logging
from logging.handlers import RotatingFileHandler

from .rutas import LOG_FILE

_CONFIGURADO = False


def get_logger(nombre="pandex"):
    global _CONFIGURADO
    if not _CONFIGURADO:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        raiz = logging.getLogger("pandex")
        raiz.setLevel(logging.INFO)
        raiz.addHandler(handler)
        _CONFIGURADO = True
    return logging.getLogger(nombre)
