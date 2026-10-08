"""Rusty, el panda rojo de Pandex: el pixel art original, tal cual.

La imagen sale de ``assets/rusty/spritesheet.png`` (6 cuadros de 192×208, creados a
partir del GIF de Rusty con ``herramientas/gif_a_sprite.py``). Cada estado usa **un
cuadro fijo**: la mascota no anima nada, así que en reposo no usa CPU. Cada cuadro se
escala una sola vez por tamaño y queda en caché.
"""

from functools import lru_cache

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QImage, QPixmap

from ..rutas import ASSETS_DIR

HOJA = ASSETS_DIR / "rusty" / "spritesheet.png"
CUADRO = (192, 208)

# qué cuadro del GIF usa cada estado
CUADROS = {
    "idle": 0,        # mirando de frente
    "trabajando": 1,  # cabeza ladeada, concentrado
    "feliz": 3,       # ojos cerrados, sonriendo
    "error": 0,       # el globo rojo ya avisa; la cara no cambia
}
ESTADOS = tuple(CUADROS)

# caja común a todos los cuadros (sin el margen transparente del GIF): así la
# figura no salta al cambiar de estado
RECORTE = QRect(5, 5, 183, 199)
# la cabeza, para el logo
CABEZA = QRect(4, 4, 142, 122)


@lru_cache(maxsize=1)
def _hoja():
    hoja = QImage(str(HOJA))
    return None if hoja.isNull() else hoja.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)


def disponible():
    return _hoja() is not None


def _cuadro(indice, caja):
    return _hoja().copy(caja.translated(indice * CUADRO[0], 0))


def tamano(alto):
    """Tamaño de la ventana para ese alto, con la proporción de Rusty."""
    return max(24, round(alto * RECORTE.width() / RECORTE.height())), max(24, int(alto))


def _escalar(img, ancho, alto):
    # al ampliar 2× o más, sin suavizar (píxeles nítidos); al reducir, suavizado
    # para no perder detalle del dibujo original
    modo = (Qt.TransformationMode.FastTransformation if alto >= img.height() * 2
            else Qt.TransformationMode.SmoothTransformation)
    return img.scaled(ancho, alto, Qt.AspectRatioMode.KeepAspectRatio, modo)


@lru_cache(maxsize=16)
def _imagen(estado, alto, dpr):
    ancho, alto_ = tamano(alto)
    pix = QPixmap.fromImage(_escalar(_cuadro(CUADROS[estado], RECORTE), round(ancho * dpr), round(alto_ * dpr)))
    pix.setDevicePixelRatio(dpr)
    return pix


def imagen(estado, alto, dpr=1.0):
    """Rusty listo para pintar (``QPixmap`` con la escala de la pantalla), en caché.

    Ocupa como mucho ``alto`` píxeles lógicos; quien lo pinta lo centra.
    """
    if estado not in CUADROS:
        estado = "idle"
    return _imagen(estado, int(alto), round(float(dpr), 2))


@lru_cache(maxsize=1)
def cabeza():
    """Solo la cabeza (para el logo), como ``QImage`` en su tamaño original."""
    return _cuadro(0, CABEZA)
