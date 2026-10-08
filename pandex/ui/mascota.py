"""La mascota: ventana sin marco, transparente, que se arrastra y habla.

Es **estática** a propósito: cada estado (reposo, feliz, trabajando, error) es una
imagen que se pinta una vez y queda en caché. No hay temporizadores de animación;
la ventana solo se vuelve a dibujar cuando cambia el estado o el tamaño. En reposo
no consume CPU.

Personajes (``mascota.personaje``): ``"rusty"`` (por defecto, el panda rojo en pixel
art de ``ui/rusty.py``), ``"vectorial"`` (el panda robot de ``ui/dibujo.py``) o
``"pixel"`` (un sprite sheet, ``ui/sprites.py``).
"""

import random

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

from . import dibujo, rusty
from .globo import Globo
from .sprites import Sprites

ESTADOS = dibujo.ESTADOS


def pantalla_de(widget):
    """La pantalla donde está el widget (no siempre la principal)."""
    centro = widget.geometry().center()
    return QGuiApplication.screenAt(centro) or widget.screen() or QApplication.primaryScreen()


class Mascota(QWidget):
    menu_pedido = pyqtSignal(QPoint)

    def __init__(self, config):
        super().__init__(None)
        self.config = config
        self._estado = "idle"
        self._arrastrando = False
        self._offset = QPoint()
        self._movio = False

        self.globo = Globo()
        self._cargar_personaje()
        self._construir_ventana()
        self._restaurar_posicion()

        # vuelve sola al reposo tras una reacción (un único disparo, no un bucle)
        self._fin_estado = QTimer(self)
        self._fin_estado.setSingleShot(True)
        self._fin_estado.timeout.connect(lambda: self.set_estado("idle"))

    # ---------- construcción ----------

    def _cargar_personaje(self):
        m = self.config.mascota
        self.sprites = None
        self.personaje = m.get("personaje", "rusty")
        if self.personaje == "pixel":
            sprites = Sprites(m.get("spritesheet"))
            if sprites.ok:
                self.sprites = sprites

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
        if self.sprites:
            return self.sprites.tamano_ventana(lado)
        if self.personaje == "rusty":
            return rusty.tamano(lado)  # múltiplo exacto de la cuadrícula: píxeles parejos
        return lado, lado

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
        self._cargar_personaje()
        self.resize(*self._tamano())
        self.setWindowOpacity(float(self.config.mascota.get("opacidad", 1.0)))
        self.setWindowTitle(self.config.mascota.get("nombre", "Pandex"))
        encima = self.config.mascota.get("siempre_encima", True)
        if bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint) != encima:
            visible = self.isVisible()
            self._construir_ventana()
            if visible:
                self.show()
        self.update()

    # ---------- estado y globo ----------

    @property
    def estado(self):
        return self._estado

    def set_estado(self, estado, segundos=None):
        """idle | feliz | trabajando | error. Con ``segundos``, vuelve sola al reposo."""
        if estado not in ESTADOS:
            estado = "idle"
        if segundos:
            self._fin_estado.start(int(segundos * 1000))
        else:
            self._fin_estado.stop()
        if estado != self._estado:
            self._estado = estado
            self.update()  # un solo repintado: la imagen ya está en caché

    def decir(self, texto, tipo=None, segundos=None):
        if not self.config.mascota.get("globo_activo", True):
            return
        self.globo.decir(texto, segundos or self.config.mascota.get("globo_segundos", 5), tipo)
        self._colocar_globo()

    def progreso(self, texto, hechos, total):
        """Actualiza el globo en su sitio, sin volver a animarlo."""
        if not self.config.mascota.get("globo_activo", True):
            return
        self.globo.progreso(texto, hechos, total)
        self._colocar_globo()

    def _colocar_globo(self):
        if not self.globo.isVisible():
            return
        area = pantalla_de(self).availableGeometry()
        x = self.x() + self.width() // 2 - self.globo.width() // 2
        y = self.y() - self.globo.height() + 4
        x = max(area.left() + 6, min(x, area.right() - self.globo.width() - 6))
        abajo = y < area.top() + 6
        if abajo:
            y = self.y() + self.height() - 4
        self.globo.colocar(x, y, self.x() + self.width() // 2 - x, abajo)

    # ---------- pintado ----------

    def paintEvent(self, _evento):
        painter = QPainter(self)
        dpr = self.devicePixelRatioF()
        if self.sprites:
            pix = self.sprites.frame(self._estado, 0.0, self.width(), self.height())
            if pix is not None:
                painter.drawPixmap((self.width() - pix.width()) // 2,
                                   (self.height() - pix.height()) // 2, pix)
                return
        if self.personaje == "rusty":
            pix = rusty.imagen(self._estado, self.height(), dpr)
            painter.drawPixmap(round((self.width() - pix.width() / dpr) / 2),
                               round((self.height() - pix.height() / dpr) / 2), pix)
            return
        painter.drawPixmap(0, 0, dibujo.imagen(self._estado, self.width(), self.height(), dpr))

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
