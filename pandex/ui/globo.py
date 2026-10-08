"""Globo de diálogo: una tarjeta sobre la mascota que aparece y se desvanece sola.

Las únicas animaciones son la entrada (150 ms) y la salida (250 ms); el resto del
tiempo no hay nada corriendo. Los avances de una tarea actualizan el mismo globo
en su sitio, sin volver a animarlo.
"""

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFontMetrics, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from . import tema

ANCHO_MAX = 250
ANCHO_MIN = 120
MARGEN = 12          # relleno interior
SOMBRA = 8           # espacio alrededor para la sombra
COLA = 8
RADIO = 12
BARRA = 3            # barra de progreso

TIPOS = ("info", "exito", "error", "progreso")


def tipo_de(texto):
    if texto.startswith("⚠"):
        return "error"
    if texto.startswith("✓"):
        return "exito"
    return "info"


class Globo(QWidget):
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
        self._tipo = "info"
        self._avance = None  # (hechos, total) mientras hay progreso
        self._fuente = tema.fuente(9.5)
        self._rect_texto = QRectF()
        self._cola_x = None
        self._abajo = False

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._desvanecer)

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.finished.connect(self._al_terminar_fade)

    # ---------- API ----------

    def decir(self, texto, segundos=5, tipo=None):
        self._texto = str(texto)
        self._tipo = tipo if tipo in TIPOS else tipo_de(self._texto)
        self._avance = None
        self._mostrar(segundos)

    def progreso(self, texto, hechos, total, segundos=8):
        """Avance de una tarea: si el globo ya está visible, solo cambia su contenido."""
        self._texto = str(texto)
        self._tipo = "progreso"
        self._avance = (hechos, total) if total else None
        if self.isVisible() and self.windowOpacity() >= 0.99 and self._fade.state() != QPropertyAnimation.State.Running:
            self._medir()
            self.update()
            self._timer.start(int(segundos * 1000))
        else:
            self._mostrar(segundos)

    def ocultar_ya(self):
        self._timer.stop()
        self._fade.stop()
        self.hide()

    def colocar(self, x, y, cola_x=None, abajo=False):
        """Lo ubica; ``cola_x`` es dónde apunta la cola (relativo al globo)."""
        self._cola_x = cola_x
        if abajo != self._abajo:
            self._abajo = abajo
            self.update()
        self.move(x, y)

    # ---------- interno ----------

    def _mostrar(self, segundos):
        self._medir()
        self._fade.stop()
        if not self.isVisible() or self.windowOpacity() < 0.99:
            self.setWindowOpacity(0.0)
            self.show()
            self._animar(1.0, 150, QEasingCurve.Type.OutCubic)
        self.update()
        self._timer.start(max(1200, int(segundos * 1000)))

    def _animar(self, hasta, ms, curva):
        self._fade.stop()
        self._fade.setDuration(ms)
        self._fade.setEasingCurve(curva)
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(hasta)
        self._fade.start()

    def _medir(self):
        metrica = QFontMetrics(self._fuente)
        disponible = ANCHO_MAX - 2 * (MARGEN + SOMBRA) - 6
        rect = metrica.boundingRect(
            0, 0, disponible, 1000,
            int(Qt.TextFlag.TextWordWrap) | int(Qt.AlignmentFlag.AlignLeft),
            self._texto,
        )
        ancho_texto = max(ANCHO_MIN - 2 * (MARGEN + SOMBRA), rect.width())
        extra = (BARRA + 8) if self._avance else 0
        ancho = ancho_texto + 2 * (MARGEN + SOMBRA) + 6
        alto = rect.height() + 2 * MARGEN + extra + 2 * SOMBRA + COLA
        self.resize(int(ancho), int(alto))
        self._rect_texto = QRectF(0, 0, ancho_texto + 1, rect.height())

    def _desvanecer(self):
        self._animar(0.0, 250, QEasingCurve.Type.InCubic)

    def _al_terminar_fade(self):
        if self.windowOpacity() <= 0.01:
            self.hide()

    def _forma(self, cuerpo):
        ruta = QPainterPath()
        ruta.addRoundedRect(cuerpo, RADIO, RADIO)
        cx = self._cola_x if self._cola_x is not None else self.width() / 2
        cx = max(cuerpo.left() + RADIO + 8, min(cx, cuerpo.right() - RADIO - 8))
        cola = QPainterPath()
        if self._abajo:
            cola.moveTo(cx - 7, cuerpo.top() + 1)
            cola.lineTo(cx, cuerpo.top() - COLA)
            cola.lineTo(cx + 7, cuerpo.top() + 1)
        else:
            cola.moveTo(cx - 7, cuerpo.bottom() - 1)
            cola.lineTo(cx, cuerpo.bottom() + COLA)
            cola.lineTo(cx + 7, cuerpo.bottom() - 1)
        cola.closeSubpath()
        return ruta.united(cola)

    def paintEvent(self, _evento):
        c = tema.colores()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        arriba = SOMBRA + (COLA if self._abajo else 0)
        cuerpo = QRectF(SOMBRA, arriba, self.width() - 2 * SOMBRA, self.height() - 2 * SOMBRA - COLA)
        forma = self._forma(cuerpo)

        # sombra suave: unas pocas capas translúcidas (solo se pinta al cambiar el texto)
        painter.setPen(Qt.PenStyle.NoPen)
        alfa = 26 if tema.es_oscuro() else 9
        for i in range(4):
            painter.setBrush(QColor(0, 0, 0, alfa))
            capa = QPainterPath()
            capa.addRoundedRect(cuerpo.adjusted(-4 + i, -2 + i, 4 - i, 5 - i), RADIO + 4 - i, RADIO + 4 - i)
            painter.drawPath(capa)

        painter.setPen(QPen(QColor(c["borde"]), 1))
        painter.setBrush(QBrush(QColor(c["superficie"])))
        painter.drawPath(forma)

        # punto de color del tipo de mensaje
        acento = {"exito": c["exito"], "error": c["error"], "progreso": c["terracota"]}.get(self._tipo, c["acento"])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(acento))
        punto_y = cuerpo.top() + MARGEN + QFontMetrics(self._fuente).height() / 2
        painter.drawEllipse(QRectF(cuerpo.left() + MARGEN - 1, punto_y - 3, 6, 6))

        x_texto = cuerpo.left() + MARGEN + 11
        rect = self._rect_texto.translated(x_texto, cuerpo.top() + MARGEN)
        painter.setPen(QColor(c["texto"]))
        painter.setFont(self._fuente)
        painter.drawText(rect, int(Qt.TextFlag.TextWordWrap) | int(Qt.AlignmentFlag.AlignLeft), self._texto)

        if self._avance:
            hechos, total = self._avance
            pista = QRectF(x_texto, rect.bottom() + 8, cuerpo.right() - MARGEN - x_texto, BARRA)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(c["superficie_2"]))
            painter.drawRoundedRect(pista, BARRA / 2, BARRA / 2)
            lleno = QRectF(pista)
            lleno.setWidth(max(BARRA, pista.width() * min(1.0, hechos / max(1, total))))
            painter.setBrush(QColor(acento))
            painter.drawRoundedRect(lleno, BARRA / 2, BARRA / 2)
