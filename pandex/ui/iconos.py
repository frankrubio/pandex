"""Íconos de línea para el menú, dibujados con QPainter (sin archivos extra).

Se pintan una vez y quedan en caché. Cada tarea puede elegir el suyo con el
atributo ``icono = "sincronizar"`` (si no, lleva uno genérico).
"""

from functools import lru_cache

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from . import tema

LADO = 32  # se dibuja a 2× y Qt lo reduce a 16 px: queda nítido en pantallas HiDPI


def _sincronizar(p):
    p.drawArc(QRectF(7, 7, 18, 18), 30 * 16, 150 * 16)
    p.drawArc(QRectF(7, 7, 18, 18), 210 * 16, 150 * 16)
    _flecha(p, (23.8, 11.5), (24.5, 6.5), (19.7, 9.6))
    _flecha(p, (8.2, 20.5), (7.5, 25.5), (12.3, 22.4))


def _flecha(p, a, b, c):
    ruta = QPainterPath(QPointF(*b))
    ruta.lineTo(QPointF(*a))
    ruta.lineTo(QPointF(*c))
    p.drawPath(ruta)


def _documento(p):
    ruta = QPainterPath(QPointF(9, 5))
    ruta.lineTo(19, 5)
    ruta.lineTo(24, 10)
    ruta.lineTo(24, 27)
    ruta.lineTo(9, 27)
    ruta.closeSubpath()
    p.drawPath(ruta)
    p.drawLine(QPointF(13, 15), QPointF(20, 15))
    p.drawLine(QPointF(13, 19.5), QPointF(20, 19.5))
    p.drawLine(QPointF(13, 24), QPointF(17, 24))


def _hola(p):
    p.drawRoundedRect(QRectF(5, 7, 22, 15), 6, 6)
    ruta = QPainterPath(QPointF(10, 22))
    ruta.lineTo(9, 27)
    ruta.lineTo(15, 22)
    p.drawPath(ruta)


def _engranaje(p):
    p.drawEllipse(QPointF(16, 16), 4, 4)
    p.drawEllipse(QPointF(16, 16), 9, 9)
    for i in range(8):
        p.save()
        p.translate(16, 16)
        p.rotate(i * 45)
        p.drawLine(QPointF(0, -9), QPointF(0, -12))
        p.restore()


def _lista(p):
    for y in (9, 16, 23):
        p.drawPoint(QPointF(7, y))
        p.drawLine(QPointF(12, y), QPointF(26, y))


def _recargar(p):
    p.drawArc(QRectF(7, 7, 18, 18), 60 * 16, 290 * 16)
    _flecha(p, (21.5, 6.5), (17, 7.6), (20.5, 11.5))


def _descargar(p):
    p.drawLine(QPointF(16, 5), QPointF(16, 20))
    _flecha(p, (10.5, 15), (16, 20.5), (21.5, 15))
    p.drawLine(QPointF(7, 26), QPointF(25, 26))


def _ojo(p):
    ruta = QPainterPath(QPointF(4, 16))
    ruta.quadTo(16, 4, 28, 16)
    ruta.quadTo(16, 28, 4, 16)
    p.drawPath(ruta)
    p.drawEllipse(QPointF(16, 16), 3.6, 3.6)


def _ocultar(p):
    _ojo(p)
    p.drawLine(QPointF(7, 25), QPointF(25, 7))


def _salir(p):
    p.drawArc(QRectF(7, 8, 18, 18), 125 * 16, -250 * 16)
    p.drawLine(QPointF(16, 5), QPointF(16, 15))


def _canvas(p):
    p.drawRoundedRect(QRectF(5, 7, 22, 18), 4, 4)
    p.drawLine(QPointF(5, 12), QPointF(27, 12))
    p.drawLine(QPointF(12, 17), QPointF(21, 17))


def _tarea(p):
    p.drawRoundedRect(QRectF(6, 6, 20, 20), 5, 5)
    _flecha(p, (11, 16.5), (14.5, 20), (21, 12))


def _mas(p):
    p.drawLine(QPointF(16, 7), QPointF(16, 25))
    p.drawLine(QPointF(7, 16), QPointF(25, 16))


def _carpeta(p):
    ruta = QPainterPath(QPointF(5, 24))
    ruta.lineTo(QPointF(5, 9))
    ruta.lineTo(QPointF(12, 9))
    ruta.lineTo(QPointF(15, 12))
    ruta.lineTo(QPointF(27, 12))
    ruta.lineTo(QPointF(27, 24))
    ruta.closeSubpath()
    p.drawPath(ruta)


def _buscar(p):
    p.drawEllipse(QPointF(14, 14), 7, 7)
    p.drawLine(QPointF(19.5, 19.5), QPointF(26, 26))


def _subir(p):
    p.drawLine(QPointF(16, 26), QPointF(16, 7))
    _flecha(p, (9.5, 13.5), (16, 7), (22.5, 13.5))


DIBUJOS = {
    "sincronizar": _sincronizar, "documento": _documento, "hola": _hola,
    "engranaje": _engranaje, "lista": _lista, "recargar": _recargar,
    "descargar": _descargar, "mostrar": _ojo, "ocultar": _ocultar, "salir": _salir,
    "canvas": _canvas, "tarea": _tarea, "mas": _mas, "carpeta": _carpeta, "buscar": _buscar,
    "subir": _subir,
}


@lru_cache(maxsize=64)
def _icono(nombre, color):
    pix = QPixmap(LADO, LADO)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(QPen(QColor(color), 2.2, cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    DIBUJOS.get(nombre, _tarea)(p)
    p.end()
    pix.setDevicePixelRatio(2.0)
    return QIcon(pix)


def icono(nombre, color=None):
    return _icono(nombre, color or tema.hex_("texto_suave"))
