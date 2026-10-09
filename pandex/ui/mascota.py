"""La mascota: ventana sin marco, transparente, que se arrastra y habla.

En reposo es **estática**: una imagen en caché, sin temporizadores, 0 % de CPU. Si el
personaje trae movimientos (p. ej. una mascota de Codex Pets), se mueve **solo**
mientras trabaja o reacciona, con cuadros ya escalados en caché; al volver al reposo el
temporizador se apaga. Se puede desactivar en Configuración → Comportamiento.

El personaje (``mascota.personaje``) es cualquiera de ``ui/personajes.py``: los que trae
Pandex y los que añadiste tú. Por defecto, ``"rusty"``, el panda rojo.
"""

import random

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

from . import logo, personajes
from .globo import Globo

ESTADOS = personajes.ESTADOS


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
        self.al_clic = None  # función de la app; si devuelve True, el clic ya se atendió

        self.globo = Globo()
        self._cargar_personaje()
        self._construir_ventana()
        self._restaurar_posicion()

        # los cuadros de la animación del estado actual (vacío = imagen fija)
        self._cuadros = ()
        self._cuadro = 0
        self._animacion = QTimer(self)
        self._animacion.timeout.connect(self._siguiente_cuadro)

        # vuelve sola al reposo tras una reacción (un único disparo, no un bucle)
        self._fin_estado = QTimer(self)
        self._fin_estado.setSingleShot(True)
        self._fin_estado.timeout.connect(lambda: self.set_estado("idle"))

    # ---------- construcción ----------

    def _cargar_personaje(self):
        # uno que ya no existe (p. ej. lo quitaste): Rusty
        elegido = personajes.elegir(self.config.mascota.get("personaje", personajes.POR_DEFECTO))
        self.personaje = elegido.id if elegido else None

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
        """La ventana toma la proporción del personaje."""
        lado = int(self.config.mascota.get("tamano", 120))
        return personajes.tamano(self.personaje, lado)

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
        self._animar()  # otro personaje o tamaño: otros cuadros
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
            self._animar()
            self.update()  # un solo repintado: la imagen ya está en caché

    def _animar(self):
        """Prende el temporizador solo si este estado tiene movimiento; si no, lo apaga."""
        self._animacion.stop()
        self._cuadros, self._cuadro = (), 0
        if self.personaje is None or self._estado == "idle" or not self.config.mascota.get("animar", True):
            return
        ms = personajes.ritmo(self.personaje, self._estado)
        if ms:
            self._cuadros = personajes.cuadros(self.personaje, self._estado, self.height(),
                                               self.devicePixelRatioF())
            self._animacion.start(ms)

    def _siguiente_cuadro(self):
        if not self._cuadros or not self.isVisible():
            self._animacion.stop()
            return
        self._cuadro = (self._cuadro + 1) % len(self._cuadros)
        self.update()

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
        if self.personaje is None:  # sin ningún personaje instalado: al menos el logo
            lado = min(self.width(), self.height())
            painter.drawPixmap((self.width() - lado) // 2, (self.height() - lado) // 2, logo.pixmap(lado, dpr))
            return
        if self._cuadros:
            pix = self._cuadros[self._cuadro]
        else:
            pix = personajes.imagen(self.personaje, self._estado, self.height(), dpr)
        painter.drawPixmap(round((self.width() - pix.width() / dpr) / 2),
                           round((self.height() - pix.height() / dpr) / 2), pix)

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
        # la app puede reclamar el clic (p. ej. «hay una actualización: clic para instalarla»)
        if callable(self.al_clic) and self.al_clic():
            return
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
