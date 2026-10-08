"""Panda robot dibujado con QPainter, en colores de Python.

Todo se dibuja en una caja lógica de 100x100 y luego se escala al tamaño real,
así la mascota se ve igual de nítida a 80px que a 300px.
"""


from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen

AZUL = QColor("#306998")
AZUL_CLARO = QColor("#4B8BBE")
AZUL_OSCURO = QColor("#20496B")
AMARILLO = QColor("#FFD43B")
AMARILLO_CLARO = QColor("#FFE873")
BLANCO = QColor("#FBFCFD")
GRIS = QColor("#E4E9EF")
NEGRO = QColor("#2A3340")
SOMBRA = QColor(30, 45, 65, 60)


def _squircle(x, y, w, h, r):
    ruta = QPainterPath()
    ruta.addRoundedRect(QRectF(x, y, w, h), r, r)
    return ruta


def dibujar_panda(painter, ancho, alto, estado="idle", mirada=(0.0, 0.0),
                  parpadeo=0.0, respiracion=0.0):
    """estado: idle | feliz | trabajando | error
    mirada: (dx, dy) en -1..1, hacia dónde apuntan las pupilas
    parpadeo: 0 = ojos abiertos, 1 = cerrados
    respiracion: -1..1, ciclo de respiración
    """
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.save()
    painter.scale(ancho / 100.0, alto / 100.0)

    subida = respiracion * 1.2
    ensanche = 1.0 + respiracion * 0.012

    _sombra(painter, respiracion)

    painter.save()
    painter.translate(50, 50 + subida)
    painter.scale(ensanche, 1.0 / ensanche)
    painter.translate(-50, -50)

    _cuerpo(painter, estado)
    _brazos(painter, estado, respiracion)
    _antena(painter, estado)
    _orejas(painter)
    _cabeza(painter)
    _ojos(painter, mirada, parpadeo, estado)
    _hocico(painter, estado)

    painter.restore()
    painter.restore()


def _sombra(painter, respiracion):
    ancho = 34 - respiracion * 2
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(SOMBRA))
    painter.drawEllipse(QRectF(50 - ancho / 2, 94, ancho, 6))


def _antena(painter, estado):
    painter.setPen(QPen(AZUL_OSCURO, 2.2, cap=Qt.PenCapStyle.RoundCap))
    painter.drawLine(QPointF(50, 14), QPointF(50, 5.5))
    painter.setPen(Qt.PenStyle.NoPen)
    if estado == "error":
        bola = QColor("#E8654F")
    elif estado == "trabajando":
        bola = AMARILLO_CLARO
    else:
        bola = AMARILLO
    painter.setBrush(QBrush(QColor(bola.red(), bola.green(), bola.blue(), 90)))
    painter.drawEllipse(QPointF(50, 4.5), 6.0, 6.0)
    painter.setBrush(QBrush(bola))
    painter.drawEllipse(QPointF(50, 4.5), 3.4, 3.4)


def _orejas(painter):
    painter.setPen(QPen(AZUL_OSCURO, 2.4))
    painter.setBrush(QBrush(NEGRO))
    for cx in (27.5, 72.5):
        painter.drawEllipse(QPointF(cx, 17), 10.5, 10.5)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(AZUL))
    for cx in (27.5, 72.5):
        painter.drawEllipse(QPointF(cx, 17), 5.2, 5.2)


def _cabeza(painter):
    cabeza = QRectF(18, 12, 64, 52)
    grad = QLinearGradient(0, 12, 0, 64)
    grad.setColorAt(0.0, BLANCO)
    grad.setColorAt(1.0, GRIS)
    painter.setBrush(QBrush(grad))
    painter.setPen(QPen(AZUL, 2.6))
    painter.drawRoundedRect(cabeza, 26, 24)

    # visera: la banda azul que cruza la frente, marca robótica
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(AZUL))
    visera = QPainterPath()
    visera.addRoundedRect(QRectF(22.5, 15.5, 55, 9), 5, 5)
    painter.drawPath(visera)
    painter.setBrush(QBrush(AMARILLO))
    painter.drawEllipse(QPointF(68, 20), 2.1, 2.1)


def _ojos(painter, mirada, parpadeo, estado):
    dx = max(-1.0, min(1.0, mirada[0])) * 1.9
    dy = max(-1.0, min(1.0, mirada[1])) * 1.4

    for cx in (37.5, 62.5):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(NEGRO))
        painter.drawEllipse(QPointF(cx, 39), 11.5, 12.5)

    abierto = 1.0 - parpadeo
    for cx in (37.5, 62.5):
        if abierto < 0.12:
            painter.setPen(QPen(AMARILLO, 2.2, cap=Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(cx - 4.5, 39), QPointF(cx + 4.5, 39))
            continue

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(AMARILLO_CLARO if estado == "feliz" else AMARILLO))
        painter.drawEllipse(QPointF(cx + dx * 0.4, 39), 6.4, 6.6 * abierto)

        painter.setBrush(QBrush(AZUL_OSCURO))
        painter.drawEllipse(QPointF(cx + dx, 39 + dy), 3.1, 3.3 * abierto)

        painter.setBrush(QBrush(BLANCO))
        painter.drawEllipse(QPointF(cx + dx + 1.2, 37.2 + dy), 1.1, 1.2 * abierto)

    if estado != "error":
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 212, 59, 70)))
        for cx in (26.5, 73.5):
            painter.drawEllipse(QPointF(cx, 50), 4.2, 2.8)


def _hocico(painter, estado):
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(NEGRO))
    painter.drawEllipse(QRectF(46.6, 51.5, 6.8, 4.6))

    painter.setPen(QPen(NEGRO, 1.9, cap=Qt.PenCapStyle.RoundCap))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    boca = QPainterPath()
    if estado == "feliz":
        boca.moveTo(44.5, 57.5)
        boca.quadTo(50, 63.5, 55.5, 57.5)
    elif estado == "trabajando":
        painter.setBrush(QBrush(NEGRO))
        painter.drawEllipse(QRectF(47.6, 57.5, 4.8, 4.4))
        return
    elif estado == "error":
        boca.moveTo(45, 61)
        boca.quadTo(50, 56.5, 55, 61)
    else:
        boca.moveTo(45.5, 57.8)
        boca.quadTo(50, 61.4, 54.5, 57.8)
    painter.drawPath(boca)


def _cuerpo(painter, estado):
    grad = QLinearGradient(0, 62, 0, 95)
    grad.setColorAt(0.0, AZUL_CLARO)
    grad.setColorAt(1.0, AZUL)
    painter.setBrush(QBrush(grad))
    painter.setPen(QPen(AZUL_OSCURO, 2.2))
    painter.drawPath(_squircle(31, 60, 38, 33, 15))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(NEGRO))
    painter.drawPath(_squircle(38, 68, 24, 15, 4.5))

    # panel del pecho: ">_" que parpadea cuando trabaja
    painter.setPen(QPen(AMARILLO, 1.7, cap=Qt.PenCapStyle.RoundCap,
                        join=Qt.PenJoinStyle.RoundJoin))
    flecha = QPainterPath()
    flecha.moveTo(43, 72)
    flecha.lineTo(47, 75.5)
    flecha.lineTo(43, 79)
    painter.drawPath(flecha)
    if estado != "trabajando":
        painter.drawLine(QPointF(49.5, 79), QPointF(56.5, 79))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(NEGRO))
    for cx in (41.5, 58.5):
        painter.drawPath(_squircle(cx - 5, 88, 10, 7, 3.4))


def _brazos(painter, estado, respiracion):
    painter.setPen(QPen(AZUL_OSCURO, 2.0))
    painter.setBrush(QBrush(NEGRO))
    balanceo = respiracion * 2.6 if estado == "trabajando" else respiracion * 0.8
    for lado, cx in ((-1, 27.5), (1, 72.5)):
        painter.save()
        painter.translate(cx, 68)
        painter.rotate(lado * balanceo * 3.0)
        painter.drawPath(_squircle(-4.5, -2, 9, 17, 4.5))
        painter.restore()


def icono_bandeja(painter, lado):
    """Versión mini para la bandeja del sistema: solo la cabeza."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.save()
    painter.scale(lado / 100.0, lado / 100.0)

    # la cabeza con orejas ocupa x 17..83, y 6..64 en coordenadas lógicas
    escala = 94 / 66.0
    painter.scale(escala, escala)
    painter.translate(3 / escala - 17, 9 / escala - 6)

    _orejas(painter)
    _cabeza(painter)
    _ojos(painter, (0, 0), 0.0, "idle")
    _hocico(painter, "idle")
    painter.restore()
