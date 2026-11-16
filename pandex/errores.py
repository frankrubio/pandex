"""Red de seguridad: un error que nadie atrapó no cierra Pandex (spec 011, ROB-01).

Sin un manejador propio, PyQt6 aborta el proceso cuando un clic, un reloj o una señal lanza
un error; como Pandex corre sin consola, la mascota desaparecía sin decir nada. Aquí el error
queda en el registro con su traza y la mascota lo avisa.

``instalar(avisar)`` se llama una vez, desde ``main.py``. ``avisar(texto)`` puede llegar desde
cualquier hilo: ``PandexApp`` le pasa una señal de Qt.
"""

import sys
import threading
import time
import traceback

from .log import get_logger

log = get_logger("pandex.errores")

AVISAR_CADA = 30  # s: un error que se repite no llena la pantalla de globos
MENSAJE = "Algo falló y lo anoté. Si se repite, mira «Ver registro»."

_avisar = None
_ultimo_aviso = 0.0
_VISTOS = {}  # (tipo, archivo, línea) -> cuántas veces
_candado = threading.Lock()


def instalar(avisar=None):
    """Atiende los errores de la interfaz y de los hilos. ``avisar`` es opcional."""
    global _avisar
    _avisar = avisar
    sys.excepthook = atender
    threading.excepthook = lambda args: atender(args.exc_type, args.exc_value, args.exc_traceback)


def avisar_con(avisar):
    """Cambia a quién se avisa (la app, cuando ya tiene mascota)."""
    global _avisar
    _avisar = avisar


def _firma(tipo, traza):
    ultimo = traceback.extract_tb(traza)[-1:] if traza is not None else []
    return (tipo.__name__, ultimo[0].filename if ultimo else "", ultimo[0].lineno if ultimo else 0)


def atender(tipo, valor, traza):
    """Anota el error y avisa. Ctrl+C sigue cerrando como siempre."""
    global _ultimo_aviso
    if issubclass(tipo, (KeyboardInterrupt, SystemExit)):
        sys.__excepthook__(tipo, valor, traza)
        return
    firma = _firma(tipo, traza)
    with _candado:
        veces = _VISTOS[firma] = _VISTOS.get(firma, 0) + 1
        ahora = time.monotonic()
        toca_avisar = _ultimo_aviso == 0.0 or ahora - _ultimo_aviso >= AVISAR_CADA
        if toca_avisar:
            _ultimo_aviso = ahora
    try:
        if veces == 1:
            log.error("error inesperado:\n%s", "".join(traceback.format_exception(tipo, valor, traza)).rstrip())
        elif veces in (10, 100, 1000, 10000):
            log.error("el error de %s:%d (%s) ya se repitió %d veces", firma[1], firma[2], firma[0], veces)
    except Exception:  # el registro no puede ser otro motivo para caerse
        pass
    if toca_avisar and _avisar is not None:
        try:
            _avisar(MENSAJE)
        except Exception:
            pass
