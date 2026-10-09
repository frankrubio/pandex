"""El logo de Pandex: la cara de un personaje sobre un squircle de color.

Por defecto es la cara del personaje que elegiste; en **Configuración → Apariencia →
Logo** puedes fijar otro. El mismo dibujo da el ícono de la bandeja, el de
las ventanas y el del acceso directo (``assets/personajes/<id>/icono.ico``, que genera
``herramientas/crear_icono.py``).
"""

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QIcon, QLinearGradient, QPainter, QPixmap

from . import personajes

SIGUE_AL_PERSONAJE = "personaje"

_actual = personajes.POR_DEFECTO  # el que usa la app ahora (lo fija ``app.aplicar_logo``)


def elegido(mascota):
    """El id del logo según ``config.mascota``: el fijado o, si no, el del personaje."""
    fijo = mascota.get("logo") or SIGUE_AL_PERSONAJE
    if fijo != SIGUE_AL_PERSONAJE and personajes.existe(fijo):
        return fijo
    personaje = mascota.get("personaje")
    return personaje if personajes.existe(personaje) else personajes.POR_DEFECTO


def fijar(ident):
    global _actual
    _actual = ident


def actual():
    return _actual


def pintar(painter, lado, mini=None, ident=None):
    """El logo en ``painter``, en un cuadrado de ``lado`` píxeles.

    ``mini`` (por defecto, a 32 px o menos) agranda la cara y quita el brillo, para
    que en la bandeja de Windows se lea a la primera.
    """
    p = personajes.elegir(ident or _actual)
    claro, oscuro = p.fondo_logo if p else personajes.FONDO_LOGO
    if mini is None:
        mini = lado <= 32
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(lado / 100.0, lado / 100.0)

    fondo = QLinearGradient(0, 0, 0, 100)
    fondo.setColorAt(0.0, QColor(claro))
    fondo.setColorAt(1.0, QColor(oscuro))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(fondo))
    painter.drawRoundedRect(QRectF(2, 2, 96, 96), 24, 24)
    if not mini:  # brillo sutil arriba
        brillo = QLinearGradient(0, 2, 0, 50)
        brillo.setColorAt(0.0, QColor(255, 255, 255, 46))
        brillo.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(brillo))
        painter.drawRoundedRect(QRectF(2, 2, 96, 48), 24, 24)

    cara = personajes.cabeza(p.id) if p else None
    if cara is not None and not cara.isNull():
        ancho = 90 if mini else 76
        alto = ancho * cara.height() / cara.width()
        if alto > ancho:  # caras altas: que entren a lo alto
            ancho, alto = ancho * ancho / alto, ancho
        destino = QRectF(50 - ancho / 2, 54 - alto / 2 + (2 if mini else 0), ancho, alto)
        # sin suavizar cuando cada píxel del dibujo ocupa varios de la pantalla
        nitido = lado * ancho / 100 >= cara.width() * 2
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, not nitido)
        painter.drawImage(destino, cara)
    painter.restore()


def pixmap(lado, dpr=1.0, ident=None):
    """El logo listo para un ``QLabel`` o un asistente."""
    pix = QPixmap(round(lado * dpr), round(lado * dpr))
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.scale(dpr, dpr)
    pintar(p, lado, ident=ident)
    p.end()
    pix.setDevicePixelRatio(dpr)
    return pix


def icono(ident=None):
    """``QIcon`` para ventanas y bandeja: el ``.ico`` del personaje o, si falta, dibujado."""
    ident = ident or _actual
    ruta = personajes.ruta_icono(ident)
    if ruta is not None:
        return QIcon(str(ruta))
    resultado = QIcon()
    for lado in (16, 24, 32, 48, 64, 256):
        resultado.addPixmap(pixmap(lado, ident=ident))
    return resultado
