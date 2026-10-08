"""Globo de diálogo: aparece sobre la mascota y se desvanece solo."""

from PyQt6.QtCore import QPropertyAnimation, QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

FONDO = QColor("#FFFFFF")
BORDE = QColor("#306998")
TEXTO = QColor("#22303F")

ANCHO_MAX = 230
MARGEN = 12
COLA = 9


class Globo(QWidget):
    """Globo de diálogo que aparece sobre la mascota y se desvanece solo."""

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._texto = ""
        self._fuente = QFont("Segoe UI", 9)
        self._rect_texto = QRectF()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._desvanecer)

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(400)
        self._fade.finished.connect(self._al_terminar_fade)

    def decir(self, texto, segundos=5):
        self._texto = str(texto)
        self._medir()
        self._fade.stop()
        self.setWindowOpacity(1.0)
        self.update()
        self.show()
        self._timer.start(max(1200, int(segundos * 1000)))

    def ocultar_ya(self):
        self._timer.stop()
        self._fade.stop()
        self.hide()

    def _medir(self):
        metrica = self.fontMetrics()
        disponible = ANCHO_MAX - MARGEN * 2
        rect = metrica.boundingRect(
            0, 0, disponible, 1000,
            int(Qt.TextFlag.TextWordWrap) | int(Qt.AlignmentFlag.AlignLeft),
            self._texto,
        )
        self._rect_texto = QRectF(MARGEN, MARGEN, disponible, rect.height())
        self.resize(ANCHO_MAX, int(rect.height()) + MARGEN * 2 + COLA)

    def _desvanecer(self):
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    def _al_terminar_fade(self):
        if self.windowOpacity() <= 0.01:
            self.hide()

    def paintEvent(self, _evento):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        cuerpo = QRectF(1, 1, self.width() - 2, self.height() - COLA - 2)
        ruta = QPainterPath()
        ruta.addRoundedRect(cuerpo, 10, 10)

        cx = self.width() / 2
        cola = QPainterPath()
        cola.moveTo(cx - 8, cuerpo.bottom() - 1)
        cola.lineTo(cx, cuerpo.bottom() + COLA)
        cola.lineTo(cx + 8, cuerpo.bottom() - 1)
        cola.closeSubpath()
        ruta = ruta.united(cola)

        painter.setPen(QPen(BORDE, 1.6))
        painter.setBrush(QBrush(FONDO))
        painter.drawPath(ruta)

        painter.setPen(QPen(TEXTO))
        painter.setFont(self._fuente)
        painter.drawText(
            self._rect_texto.toRect(),
            int(Qt.TextFlag.TextWordWrap) | int(Qt.AlignmentFlag.AlignLeft),
            self._texto,
        )
