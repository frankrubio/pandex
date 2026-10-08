"""El panda robot de Pandex, dibujado con QPainter.

Es una imagen **estática**: cada estado (reposo, feliz, trabajando, error) se pinta una
sola vez por tamaño y se guarda en caché (``imagen()``). Mientras no cambie el estado,
la mascota no vuelve a dibujar nada ni gasta CPU.

Todo se dibuja en una caja lógica de 100×100 y luego se escala, así se ve nítido a
80 px o a 300 px. El logo de la app (``logo()``) reutiliza la misma cabeza.
"""

from functools import lru_cache

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)

# paleta del personaje: no cambia con el tema, para que el panda sea siempre el mismo
GRAFITO = QColor("#2B2A28")
GRAFITO_LUZ = QColor("#45433F")
MARFIL = QColor("#FDFCF8")
MARFIL_SOMBRA = QColor("#E7E2D4")
CONTORNO = QColor("#2B2A28")
AZUL = QColor("#3B6EA8")
AZUL_OSCURO = QColor("#244A75")
AZUL_CLARO = QColor("#6F9BD0")
LED = QColor("#8FD3FF")
TERRACOTA = QColor("#D97757")
VERDE = QColor("#3FB37A")
ROJO = QColor("#E05252")
SOMBRA = QColor(20, 18, 15, 46)

ESTADOS = ("idle", "feliz", "trabajando", "error")


def _luz_de(estado):
    return {"trabajando": TERRACOTA, "feliz": VERDE, "error": ROJO}.get(estado, AZUL_CLARO)


def _redondeado(x, y, w, h, r):
    ruta = QPainterPath()
    ruta.addRoundedRect(QRectF(x, y, w, h), r, r)
    return ruta


# --------------------------------------------------------------------------
# el personaje completo
# --------------------------------------------------------------------------


def dibujar_panda(painter, ancho, alto, estado="idle"):
    """Pinta el panda en un rectángulo de ``ancho``×``alto`` (estado: idle|feliz|trabajando|error)."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.save()
    lado = min(ancho, alto)
    painter.translate((ancho - lado) / 2, (alto - lado) / 2)
    painter.scale(lado / 100.0, lado / 100.0)

    _sombra(painter)
    _pies(painter)
    _cuerpo(painter, estado)
    _brazos(painter, estado)
    _antena(painter, estado)
    _cabeza(painter, estado)
    painter.restore()


@lru_cache(maxsize=16)
def _imagen(estado, ancho, alto, dpr):
    img = QImage(round(ancho * dpr), round(alto * dpr), QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    painter.scale(dpr, dpr)
    dibujar_panda(painter, ancho, alto, estado)
    painter.end()
    pix = QPixmap.fromImage(img)
    pix.setDevicePixelRatio(dpr)
    return pix


def imagen(estado, ancho, alto, dpr=1.0):
    """El panda ya pintado (``QPixmap``), en caché por estado, tamaño y escala de pantalla."""
    if estado not in ESTADOS:
        estado = "idle"
    return _imagen(estado, int(ancho), int(alto), round(float(dpr), 2))


def _sombra(p):
    grad = QRadialGradient(QPointF(50, 96), 26)
    grad.setColorAt(0.0, SOMBRA)
    grad.setColorAt(1.0, QColor(20, 18, 15, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(grad))
    p.save()
    p.translate(50, 96)
    p.scale(1.0, 0.16)
    p.drawEllipse(QPointF(0, 0), 26, 26)
    p.restore()


def _pies(p):
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(GRAFITO))
    for x in (33.5, 52.5):
        p.drawPath(_redondeado(x, 86, 14, 9.5, 4.7))
    p.setBrush(QBrush(GRAFITO_LUZ))
    for x in (36, 55):
        p.drawPath(_redondeado(x, 87.2, 9, 2.6, 1.3))


def _cuerpo(p, estado):
    grad = QLinearGradient(0, 58, 0, 92)
    grad.setColorAt(0.0, MARFIL)
    grad.setColorAt(1.0, MARFIL_SOMBRA)
    p.setPen(QPen(CONTORNO, 1.6))
    p.setBrush(QBrush(grad))
    p.drawPath(_redondeado(29, 58, 42, 33, 15))

    # pantalla del pecho
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(GRAFITO))
    p.drawPath(_redondeado(39, 66, 22, 15, 4.5))
    luz = _luz_de(estado)
    pen = QPen(luz, 1.7, cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    ruta = QPainterPath()
    if estado == "feliz":            # ✓
        ruta.moveTo(44.5, 73.8)
        ruta.lineTo(48.5, 77.2)
        ruta.lineTo(55.5, 70)
    elif estado == "error":          # !
        p.drawLine(QPointF(50, 69.5), QPointF(50, 75))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(luz))
        p.drawEllipse(QPointF(50, 78), 1.1, 1.1)
        return
    elif estado == "trabajando":     # · · ·
        p.setPen(Qt.PenStyle.NoPen)
        for i, x in enumerate((44, 50, 56)):
            c = QColor(luz)
            c.setAlpha((110, 180, 255)[i])
            p.setBrush(QBrush(c))
            p.drawEllipse(QPointF(x, 73.5), 1.7, 1.7)
        return
    else:                            # >_
        ruta.moveTo(43.5, 70.5)
        ruta.lineTo(47, 73.5)
        ruta.lineTo(43.5, 76.5)
        p.drawLine(QPointF(49.5, 76.5), QPointF(56, 76.5))
    p.drawPath(ruta)


def _brazos(p, estado):
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(GRAFITO))
    saluda = estado == "feliz"  # feliz: levanta la mano derecha
    for lado, cx in ((-1, 29), (1, 71)):
        p.save()
        p.translate(cx, 63)
        p.rotate(-120 if saluda and lado == 1 else lado * 18)
        p.drawPath(_redondeado(-5, -2, 10, 19, 5))
        p.restore()


def _antena(p, estado):
    p.setPen(QPen(GRAFITO, 1.8, cap=Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(50, 12), QPointF(50, 5))
    luz = _luz_de(estado)
    halo = QColor(luz)
    halo.setAlpha(70)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(halo))
    p.drawEllipse(QPointF(50, 4.2), 4.6, 4.6)
    p.setBrush(QBrush(luz))
    p.drawEllipse(QPointF(50, 4.2), 2.8, 2.8)


def _cabeza(p, estado, contorno=True):
    # orejas
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(GRAFITO))
    for cx in (25, 75):
        p.drawEllipse(QPointF(cx, 17), 10, 10)
    p.setBrush(QBrush(AZUL))
    for cx in (22.5, 77.5):
        p.drawEllipse(QPointF(cx, 14.5), 4, 4)
    p.setBrush(QBrush(AZUL_CLARO))
    for cx in (21.5, 76.5):
        p.drawEllipse(QPointF(cx, 13.4), 1.3, 1.3)

    # cráneo
    grad = QLinearGradient(0, 10, 0, 62)
    grad.setColorAt(0.0, MARFIL)
    grad.setColorAt(1.0, MARFIL_SOMBRA)
    p.setPen(QPen(CONTORNO, 1.6) if contorno else Qt.PenStyle.NoPen)
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(QRectF(15, 10, 70, 53), 27, 25)

    # placa azul de la frente
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(AZUL))
    p.drawPath(_redondeado(41, 14, 18, 4.2, 2.1))

    _ojos(p, estado)
    _hocico(p, estado)


def _ojos(p, estado):
    # manchas de panda, levemente inclinadas
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(GRAFITO))
    for cx, giro in ((35, -14), (65, 14)):
        p.save()
        p.translate(cx, 37)
        p.rotate(giro)
        p.drawEllipse(QPointF(0, 0), 10.5, 12.2)
        p.restore()

    luz = ROJO if estado == "error" else LED
    pen = QPen(luz, 2.4, cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin)
    for cx in (35.5, 64.5):
        if estado == "feliz":                # ^ ^
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            ruta = QPainterPath()
            ruta.moveTo(cx - 4.2, 39.5)
            ruta.quadTo(cx, 32.5, cx + 4.2, 39.5)
            p.drawPath(ruta)
        elif estado == "error":              # × ×
            p.setPen(pen)
            p.drawLine(QPointF(cx - 3.3, 34), QPointF(cx + 3.3, 40.6))
            p.drawLine(QPointF(cx + 3.3, 34), QPointF(cx - 3.3, 40.6))
        elif estado == "trabajando":         # concentrado: ojos rasgados
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(luz))
            p.drawPath(_redondeado(cx - 4.6, 35.4, 9.2, 3.6, 1.8))
        else:                                # LED redondo con brillo
            halo = QColor(luz)
            halo.setAlpha(60)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(halo))
            p.drawEllipse(QPointF(cx, 37.5), 6.2, 6.6)
            p.setBrush(QBrush(luz))
            p.drawEllipse(QPointF(cx, 37.5), 4.3, 4.7)
            p.setBrush(QBrush(QColor("#FFFFFF")))
            p.drawEllipse(QPointF(cx + 1.5, 35.6), 1.4, 1.5)

    if estado != "error":  # mejillas
        rubor = QColor(TERRACOTA)
        rubor.setAlpha(70)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(rubor))
        for cx in (23, 77):
            p.drawEllipse(QPointF(cx, 49.5), 4.2, 2.6)


def _hocico(p, estado):
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(GRAFITO))
    nariz = QPainterPath()
    nariz.moveTo(46.2, 47.6)
    nariz.quadTo(50, 46.4, 53.8, 47.6)
    nariz.quadTo(52.5, 51.4, 50, 51.6)
    nariz.quadTo(47.5, 51.4, 46.2, 47.6)
    p.drawPath(nariz)

    p.setPen(QPen(GRAFITO, 1.6, cap=Qt.PenCapStyle.RoundCap))
    p.setBrush(Qt.BrushStyle.NoBrush)
    boca = QPainterPath()
    if estado == "feliz":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(GRAFITO))
        boca.moveTo(45.5, 53.6)
        boca.quadTo(50, 53, 54.5, 53.6)
        boca.quadTo(50, 60.5, 45.5, 53.6)
        p.drawPath(boca)
        return
    if estado == "error":
        boca.moveTo(46, 57)
        boca.quadTo(50, 53.6, 54, 57)
    elif estado == "trabajando":
        boca.moveTo(47.5, 55.4)
        boca.lineTo(52.5, 55.4)
    else:
        boca.moveTo(46, 54)
        boca.quadTo(48, 56.2, 50, 54.2)
        boca.quadTo(52, 56.2, 54, 54)
    p.drawPath(boca)


# --------------------------------------------------------------------------
# logo e ícono
# --------------------------------------------------------------------------


def logo(painter, lado, mini=None):
    """El logo: la cabeza del panda sobre un squircle azul.

    ``mini`` (por defecto, a 32 px o menos) quita los detalles que a ese tamaño
    solo serían ruido: así se lee bien en la bandeja de Windows.
    """
    if mini is None:
        mini = lado <= 32
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.save()
    painter.scale(lado / 100.0, lado / 100.0)

    fondo = QLinearGradient(0, 0, 0, 100)
    fondo.setColorAt(0.0, QColor("#4A7FBA"))
    fondo.setColorAt(1.0, AZUL_OSCURO)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(fondo))
    painter.drawRoundedRect(QRectF(2, 2, 96, 96), 24, 24)
    if not mini:  # brillo sutil arriba
        brillo = QLinearGradient(0, 2, 0, 50)
        brillo.setColorAt(0.0, QColor(255, 255, 255, 40))
        brillo.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(brillo))
        painter.drawRoundedRect(QRectF(2, 2, 96, 48), 24, 24)

    painter.save()
    if mini:
        painter.translate(50, 54)
        painter.scale(1.18, 1.18)
        painter.translate(-50, -36.5)
        _cabeza_mini(painter)
    else:
        painter.translate(50, 55)
        painter.scale(1.05, 1.05)
        painter.translate(-50, -36.5)
        _cabeza(painter, "idle", contorno=False)
    painter.restore()
    painter.restore()


def _cabeza_mini(p):
    """Cabeza simplificada: orejas, cráneo, manchas y ojos. Nada de 1 px."""
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(GRAFITO))
    for cx in (24, 76):
        p.drawEllipse(QPointF(cx, 16), 11, 11)
    p.setBrush(QBrush(MARFIL))
    p.drawRoundedRect(QRectF(14, 9, 72, 54), 28, 26)
    p.setBrush(QBrush(GRAFITO))
    for cx, giro in ((35, -14), (65, 14)):
        p.save()
        p.translate(cx, 37)
        p.rotate(giro)
        p.drawEllipse(QPointF(0, 0), 11.5, 13)
        p.restore()
    p.setBrush(QBrush(LED))
    for cx in (36, 64):
        p.drawEllipse(QPointF(cx, 37.5), 5, 5.4)
    p.setBrush(QBrush(GRAFITO))
    p.drawEllipse(QPointF(50, 50), 4.2, 3)


def pixmap_logo(lado, dpr=1.0):
    """El logo listo para un ``QLabel`` o un asistente."""
    pix = QPixmap(round(lado * dpr), round(lado * dpr))
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.scale(dpr, dpr)
    logo(p, lado)
    p.end()
    pix.setDevicePixelRatio(dpr)
    return pix


def icono_bandeja(painter, lado):
    """Respaldo para la bandeja si falta ``assets/pandex.ico``."""
    logo(painter, lado)
