"""La mascota: ventana sin marco, transparente, que se arrastra y habla.

Dibuja el personaje desde un sprite sheet (``ui/sprites.py``). Si no hay ninguno,
usa el panda vectorial de ``ui/dibujo.py``. Quieta no consume CPU: el
temporizador de animación solo corre durante las reacciones cortas.
"""

import math
import random
import time

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

from . import dibujo
from .globo import Globo
from .sprites import Sprites

TICK_MS = 60


class Mascota(QWidget):
    menu_pedido = pyqtSignal(QPoint)

    def __init__(self, config):
        super().__init__(None)
        self.config = config
        self._estado = "idle"
        self._estado_hasta = 0.0
        self._t = 0.0
        self._parpadeo = 0.0
        self._prox_parpadeo = time.monotonic() + random.uniform(2.5, 6.0)
        self._mirada = (0.0, 0.0)
        self._arrastrando = False
        self._offset = QPoint()
        self._movio = False

        self.globo = Globo()
        self.sprites = Sprites(config.mascota.get("spritesheet"))
        self._construir_ventana()
        self._restaurar_posicion()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._fin_estado = QTimer(self)
        self._fin_estado.setSingleShot(True)
        self._fin_estado.timeout.connect(self._volver_a_reposo)
        self._actualizar_timer()

    # ---------- construcción ----------

    def _construir_ventana(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowSystemMenuHint
        if self.config.mascota.get("siempre_encima", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.resize(*self._tamano())
        self.setWindowOpacity(float(self.config.mascota.get("opacidad", 1.0)))
        self.setWindowTitle(self.config.mascota.get("nombre", "Pandex"))

    def _tamano(self):
        """Con sprite sheet, la ventana toma la proporción del personaje."""
        lado = int(self.config.mascota.get("tamano", 120))
        return self.sprites.tamano_ventana(lado) if self.sprites.ok else (lado, lado)

    def _restaurar_posicion(self):
        guardada = self.config.mascota.get("posicion")
        if guardada and len(guardada) == 2:
            punto = QPoint(int(guardada[0]), int(guardada[1]))
            if self._visible_en_pantalla(punto):
                self.move(punto)
                return
        area = QApplication.primaryScreen().availableGeometry()
        self.move(area.right() - self.width() - 40, area.bottom() - self.height() - 40)

    def _visible_en_pantalla(self, punto):
        centro = QPoint(punto.x() + self.width() // 2, punto.y() + self.height() // 2)
        return any(p.availableGeometry().contains(centro) for p in QApplication.screens())

    def recargar_apariencia(self):
        self.sprites = Sprites(self.config.mascota.get("spritesheet"))
        self.resize(*self._tamano())
        self.setWindowOpacity(float(self.config.mascota.get("opacidad", 1.0)))
        encima = self.config.mascota.get("siempre_encima", True)
        if bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint) != encima:
            visible = self.isVisible()
            self._construir_ventana()
            if visible:
                self.show()
        self._actualizar_timer()
        self.update()

    # ---------- estado y globo ----------

    def set_estado(self, estado, segundos=None):
        """idle | feliz | trabajando | error. Con ``segundos``, vuelve sola al reposo."""
        self._estado = estado
        self._estado_hasta = time.monotonic() + segundos if segundos else 0.0
        if segundos:
            self._fin_estado.start(int(segundos * 1000))
        else:
            self._fin_estado.stop()
        self._actualizar_timer()
        self.update()

    def _volver_a_reposo(self):
        self._estado = "idle"
        self._estado_hasta = 0.0
        self._actualizar_timer()
        self.update()

    def _necesita_animar(self):
        if not self.config.mascota.get("animacion", True) or not self.isVisible():
            return False
        if self.sprites.ok:
            # reacciones cortas (saltito al saludar, temblor al fallar) o un sheet
            # con varias poses para este estado; si no, la imagen queda fija
            reaccion = self._estado in ("feliz", "error") and bool(self._estado_hasta)
            return reaccion or self.sprites.cuadros(self._estado_dibujado()) > 1
        return True  # el dibujo vectorial respira, parpadea y sigue el cursor

    def _actualizar_timer(self):
        if self._necesita_animar():
            if not self._timer.isActive():
                self._timer.start(TICK_MS)
        else:
            self._timer.stop()

    def showEvent(self, evento):
        super().showEvent(evento)
        self._actualizar_timer()

    def hideEvent(self, evento):
        super().hideEvent(evento)
        self._timer.stop()

    def decir(self, texto):
        if not self.config.mascota.get("globo_activo", True):
            return
        self.globo.decir(texto, self.config.mascota.get("globo_segundos", 5))
        self._colocar_globo()

    def _colocar_globo(self):
        if not self.globo.isVisible():
            return
        x = self.x() + self.width() // 2 - self.globo.width() // 2
        y = self.y() - self.globo.height() + 6
        area = QApplication.primaryScreen().availableGeometry()
        x = max(area.left() + 4, min(x, area.right() - self.globo.width() - 4))
        if y < area.top() + 4:
            y = self.y() + self.height() - 6
        self.globo.move(x, y)

    # ---------- animación ----------

    def _tick(self):
        if not self._necesita_animar():
            self._timer.stop()
            self.update()  # último cuadro, ya en reposo
            return

        ahora = time.monotonic()
        self._t += TICK_MS / 1000.0
        if ahora >= self._prox_parpadeo:
            self._parpadeo = min(1.0, self._parpadeo + 0.34)
            if self._parpadeo >= 1.0:
                self._prox_parpadeo = ahora + random.uniform(2.5, 6.5)
        elif self._parpadeo > 0:
            self._parpadeo = max(0.0, self._parpadeo - 0.34)

        sigue = self.config.mascota.get("ojos_siguen_cursor", True)
        self._mirada = self._calcular_mirada() if sigue else (0.0, 0.0)
        self.update()

    def _calcular_mirada(self):
        cursor = QCursor.pos()
        centro = self.geometry().center()
        alcance = max(180.0, self.width() * 2.2)
        dx = (cursor.x() - centro.x()) / alcance
        dy = (cursor.y() - centro.y()) / alcance
        return max(-1.0, min(1.0, dx)), max(-1.0, min(1.0, dy))

    def _movimiento(self):
        """Solo las reacciones mueven al sprite; en reposo queda fijo."""
        if not self._estado_hasta or not self.config.mascota.get("animacion", True):
            return 0, 0
        if self._estado == "error":
            return round(math.sin(self._t * 24) * 2), 0
        if self._estado == "feliz":
            return 0, -round(abs(math.sin(self._t * 5.5)) * 6)
        return 0, 0

    def _estado_dibujado(self):
        """En reposo, el parpadeo sustituye al cuadro normal un instante."""
        if self._estado == "idle" and self._parpadeo > 0.5 and self.sprites.tiene("parpadeo"):
            return "parpadeo"
        return self._estado

    # ---------- pintado ----------

    def paintEvent(self, _evento):
        painter = QPainter(self)
        if self.sprites.ok:
            pix = self.sprites.frame(self._estado_dibujado(), self._t, self.width(), self.height())
            if pix is not None:
                dx, dy = self._movimiento()
                painter.drawPixmap((self.width() - pix.width()) // 2 + dx,
                                   (self.height() - pix.height()) // 2 + dy, pix)
                return

        velocidad = 3.2 if self._estado == "trabajando" else 1.7
        dibujo.dibujar_panda(
            painter, self.width(), self.height(), estado=self._estado, mirada=self._mirada,
            parpadeo=self._parpadeo, respiracion=math.sin(self._t * velocidad),
        )

    # ---------- interacción ----------

    def mousePressEvent(self, evento):
        if evento.button() == Qt.MouseButton.LeftButton:
            self._arrastrando = True
            self._movio = False
            self._offset = evento.globalPosition().toPoint() - self.pos()
            evento.accept()

    def mouseMoveEvent(self, evento):
        if self._arrastrando:
            nueva = evento.globalPosition().toPoint() - self._offset
            if (nueva - self.pos()).manhattanLength() > 2:
                self._movio = True
            self.move(nueva)
            self._colocar_globo()
            evento.accept()

    def mouseReleaseEvent(self, evento):
        if evento.button() != Qt.MouseButton.LeftButton:
            return
        self._arrastrando = False
        if self._movio:
            self.config.mascota["posicion"] = [self.x(), self.y()]
            self.config.guardar()
        else:
            self._saludar()
        evento.accept()

    def _saludar(self):
        if self._estado == "trabajando":
            self.decir("Estoy en algo, ya te aviso.")
            return
        self.set_estado("feliz", 1.8)
        self.decir(random.choice(self.config.mascota.get("frases_click") or ["¡Hola!"]))

    def contextMenuEvent(self, evento):
        self.menu_pedido.emit(evento.globalPos())
        evento.accept()

    def moveEvent(self, evento):
        super().moveEvent(evento)
        self._colocar_globo()

    def closeEvent(self, evento):
        self.globo.ocultar_ya()
        super().closeEvent(evento)
