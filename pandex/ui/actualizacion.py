"""Ventana «Buscar actualizaciones»: consulta GitHub y, si quieres, actualiza Pandex.

La consulta y la copia corren en un hilo aparte: la mascota y la ventana responden
mientras tanto. Nada se descarga hasta que pulsas «Actualizar ahora».
"""

from PyQt6.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from .. import actualizar
from ..log import get_logger
from . import tema

log = get_logger("pandex.ui.actualizacion")

# hilos vivos: si cierras la ventana mientras consulta, el hilo termina tranquilo
# en vez de destruirse a medias junto con ella
_vivos = set()


class _Hilo(QThread):
    aviso = pyqtSignal(str)
    listo = pyqtSignal(object)
    fallo = pyqtSignal(str)

    def __init__(self, funcion):
        super().__init__()
        self._funcion = funcion
        _vivos.add(self)
        self.finished.connect(lambda: _vivos.discard(self))

    def run(self):
        try:
            self.listo.emit(self._funcion(self.aviso.emit))
        except actualizar.ErrorActualizacion as exc:
            self.fallo.emit(str(exc))
        except Exception as exc:  # que nunca tumbe la app
            log.exception("la actualización falló")
            self.fallo.emit(f"Algo salió mal: {exc}")


class DialogoActualizacion(QDialog):
    """``reiniciar`` es la función de la app que cierra Pandex y lo vuelve a abrir."""

    def __init__(self, reiniciar, parent=None):
        super().__init__(parent)
        self._reiniciar = reiniciar
        self._hilo = None
        self.setWindowTitle("Actualizar Pandex")
        self.setMinimumWidth(460)

        self.titulo = QLabel("Buscando actualizaciones…")
        self.titulo.setProperty("rol", "titulo")
        self.detalle = QLabel(f"Tienes la versión {actualizar.version_local()}.")
        self.detalle.setProperty("rol", "suave")
        self.detalle.setWordWrap(True)
        self.detalle.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.detalle.setOpenExternalLinks(True)

        self.barra = QProgressBar()
        self.barra.setRange(0, 0)  # indeterminada
        self.barra.setFixedHeight(6)

        self.novedades = QTextBrowser()
        self.novedades.setOpenExternalLinks(True)
        self.novedades.setMinimumHeight(170)
        self.novedades.hide()

        self.cerrar = QPushButton("Cerrar")
        self.cerrar.clicked.connect(self.reject)
        self.principal = QPushButton("Actualizar ahora")
        self.principal.setProperty("rol", "primario")
        self.principal.hide()

        botones = QHBoxLayout()
        pagina = QPushButton("Ver en GitHub")
        pagina.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(actualizar.URL_PAGINA)))
        botones.addWidget(pagina)
        botones.addStretch()
        botones.addWidget(self.cerrar)
        botones.addWidget(self.principal)

        caja = QVBoxLayout(self)
        caja.setContentsMargins(24, 22, 24, 18)
        caja.setSpacing(10)
        caja.addWidget(self.titulo)
        caja.addWidget(self.detalle)
        caja.addWidget(self.barra)
        caja.addWidget(self.novedades, 1)
        caja.addSpacing(6)
        caja.addLayout(botones)

        self._correr(lambda _aviso: actualizar.buscar(), self._al_buscar)

    def showEvent(self, evento):
        super().showEvent(evento)
        tema.preparar_dialogo(self)

    # ---------- pasos ----------

    def _correr(self, funcion, al_terminar):
        self.barra.show()
        self._hilo = _Hilo(funcion)
        self._hilo.aviso.connect(self.detalle.setText)
        self._hilo.listo.connect(al_terminar)
        self._hilo.fallo.connect(self._al_fallar)
        self._hilo.start()

    def _al_buscar(self, info):
        self.barra.hide()
        if not info["hay_nueva"]:
            self.titulo.setText("Estás al día")
            self.detalle.setText(f"Tienes la versión más reciente ({info['local']}).")
            return
        self.titulo.setText(f"Pandex {info['remota']} está disponible")
        como = ("con git (tu carpeta es un clon)" if actualizar.modo() == "git"
                else "bajando la versión nueva de GitHub")
        self.detalle.setText(
            f"Tienes la {info['local']}. Se actualiza {como}; tu configuración, tus cursos, "
            "el registro y tus tareas propias no se tocan.")
        if info["novedades"]:
            self.novedades.setMarkdown(info["novedades"])
            self.novedades.show()
        self.principal.show()
        self.principal.setDefault(True)
        self.principal.clicked.connect(self._actualizar)
        self.adjustSize()

    def _actualizar(self):
        self.principal.setEnabled(False)
        self.cerrar.setEnabled(False)
        self.titulo.setText("Actualizando…")
        self._correr(lambda aviso: actualizar.aplicar(avisar=aviso), self._al_actualizar)

    def _al_actualizar(self, resultado):
        self.barra.hide()
        self.cerrar.setEnabled(True)
        self.titulo.setText("¡Listo!")
        texto = "Pandex se actualizó. Reinícialo para usar la versión nueva."
        if resultado.get("respaldo"):
            texto += f"<br><small>Copia de lo reemplazado: {resultado['respaldo']}</small>"
        self.detalle.setText(texto)
        self.principal.clicked.disconnect()
        self.principal.setText("Reiniciar Pandex")
        self.principal.setEnabled(True)
        self.principal.clicked.connect(self._reiniciar_ya)

    def _reiniciar_ya(self):
        self.accept()
        self._reiniciar()

    def _al_fallar(self, mensaje):
        self.barra.hide()
        self.cerrar.setEnabled(True)
        self.principal.setEnabled(True)
        self.titulo.setText("No se pudo completar")
        self.detalle.setText(f"<span style='color:{tema.hex_('error')}'>{mensaje}</span>")

    def reject(self):
        if self._hilo and self._hilo.isRunning() and not self.cerrar.isEnabled():
            return  # mientras copia archivos, no se cierra a medias
        super().reject()

    def closeEvent(self, evento):
        if self._hilo and self._hilo.isRunning() and not self.cerrar.isEnabled():
            evento.ignore()
            return
        super().closeEvent(evento)
