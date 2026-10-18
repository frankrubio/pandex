"""Configuración → OneDrive (solo Linux): conectar, abrir y quitar cuentas de OneDrive."""

from PyQt6.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import onedrive
from ..log import get_logger
from . import iconos, tema

log = get_logger("pandex.ui.onedrive")


class _Hilo(QThread):
    enlace = pyqtSignal(str)
    listo = pyqtSignal(object)
    fallo = pyqtSignal(str)

    def __init__(self, conexion):
        super().__init__()
        self.conexion = conexion

    def run(self):
        try:
            self.listo.emit(self.conexion.ejecutar(self.enlace.emit))
        except onedrive.ErrorOneDrive as exc:
            self.fallo.emit(str(exc))
        except Exception as exc:  # que nunca tumbe la app
            log.exception("conectar OneDrive falló")
            self.fallo.emit(f"Algo salió mal: {exc}")


class DialogoConexion(QDialog):
    """Mientras inicias sesión en el navegador. Se cierra sola al terminar."""

    def __init__(self, nombre, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Conectar OneDrive")
        self.cuenta = None
        self.error = None
        texto = QLabel(f"<b>Conectando «{nombre}»</b><br>Abrí tu navegador: inicia sesión con tu "
                       "cuenta de Microsoft y pulsa <b>Aceptar</b> en el permiso. Cuando termines, "
                       "esta ventana se cierra sola.")
        texto.setWordWrap(True)
        self.enlace = QLabel()
        self.enlace.setOpenExternalLinks(True)
        self.enlace.setWordWrap(True)
        self.enlace.hide()
        nota = QLabel("Si Microsoft dice que necesitas la aprobación de un administrador, tu "
                      "universidad no deja usar apps externas con esa cuenta: usa tu cuenta "
                      "personal o pídele acceso a TI.")
        nota.setProperty("rol", "suave")
        nota.setWordWrap(True)
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self._cancelar)
        fila = QHBoxLayout()
        fila.addStretch()
        fila.addWidget(cancelar)
        caja = QVBoxLayout(self)
        for w in (texto, self.enlace, nota):
            caja.addWidget(w)
        caja.addLayout(fila)
        self.resize(460, 0)

        self.conexion = onedrive.Conexion(nombre)
        self.hilo = _Hilo(self.conexion)
        self.hilo.enlace.connect(self._mostrar_enlace)
        self.hilo.listo.connect(self._listo)
        self.hilo.fallo.connect(self._fallo)
        self.hilo.start()

    def _mostrar_enlace(self, url):
        self.enlace.setText(f"¿No se abrió? <a href=\"{url}\">Abre este enlace</a>.")
        self.enlace.show()

    def _listo(self, cuenta):
        self.cuenta = cuenta
        self.accept()

    def _fallo(self, mensaje):
        self.error = mensaje
        self.reject()

    def _cancelar(self):
        self.conexion.cancelar()

    def reject(self):
        if self.hilo.isRunning():  # Esc o la X: primero cortar rclone
            self.conexion.cancelar()
            self.hilo.wait(5000)
        super().reject()


class PaginaOneDrive(QWidget):
    """``titulo`` y ``tarjeta`` son las piezas de diseño de la ventana de configuración."""

    def __init__(self, titulo, tarjeta, parent=None):
        super().__init__(parent)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.addLayout(titulo("OneDrive", "Tu OneDrive como una carpeta más: Pandex baja, ordena "
                                          "y convierte directo ahí."))

        self.falta = QLabel(f"<b>Falta rclone</b>, el programa que conecta OneDrive en Linux. "
                            f"Instálalo en una terminal y vuelve aquí:<br><code>{onedrive.INSTALAR}</code>")
        self.falta.setWordWrap(True)
        self.falta.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        caja.addWidget(self.falta)

        marco = tarjeta()
        interno = QVBoxLayout(marco)
        interno.setContentsMargins(16, 12, 16, 12)
        interno.setSpacing(8)
        interno.addWidget(QLabel("<b>Tus cuentas</b>"))
        self.lista = QListWidget()
        self.lista.setMinimumHeight(110)
        self.lista.currentRowChanged.connect(self._habilitar)
        interno.addWidget(self.lista)
        self.aviso = QLabel()
        self.aviso.setWordWrap(True)
        self.aviso.hide()
        interno.addWidget(self.aviso)
        botones = QHBoxLayout()
        botones.setSpacing(10)
        self.conectar = QPushButton(iconos.icono("mas"), "Conectar una cuenta…")
        self.conectar.clicked.connect(self._conectar)
        self.abrir = QPushButton("Abrir carpeta")
        self.abrir.clicked.connect(self._abrir)
        self.montar = QPushButton("Volver a abrir")
        self.montar.setToolTip("Si la carpeta aparece vacía (por ejemplo, después de perder internet)")
        self.montar.clicked.connect(self._montar)
        self.quitar = QPushButton("Quitar")
        self.quitar.clicked.connect(self._quitar)
        for b in (self.conectar, self.abrir, self.montar, self.quitar):
            botones.addWidget(b)
        botones.addStretch()
        interno.addLayout(botones)
        caja.addWidget(marco)

        ayuda = QLabel("Puedes conectar tu cuenta personal y la de la universidad. La personal queda en "
                       "<code>~/OneDrive</code> y las demás en <code>~/OneDrive - Nombre</code>, como en "
                       "Windows. Después elige esa carpeta en «Configurar Canvas…». Lo que Pandex guarda "
                       "se sube solo, en segundo plano.")
        ayuda.setProperty("rol", "suave")
        ayuda.setWordWrap(True)
        caja.addWidget(ayuda)
        caja.addStretch()
        self.refrescar()

    # ---------- estado ----------

    def refrescar(self):
        hay = onedrive.disponible()
        self.falta.setVisible(not hay)
        self.conectar.setEnabled(hay)
        self.lista.clear()
        for cuenta in onedrive.cuentas():
            estado = "✓ abierta" if onedrive.montada(cuenta) else "sin abrir"
            tipo = "personal" if cuenta.tipo == "personal" else "trabajo o universidad"
            item = QListWidgetItem(f"{cuenta.nombre}  ·  {tipo}  ·  {estado}\n{cuenta.carpeta}")
            item.setData(Qt.ItemDataRole.UserRole, cuenta)
            self.lista.addItem(item)
        if self.lista.count():
            self.lista.setCurrentRow(0)
        self._habilitar()

    def _elegida(self):
        item = self.lista.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _habilitar(self, *_):
        hay = self._elegida() is not None
        for b in (self.abrir, self.montar, self.quitar):
            b.setEnabled(hay)

    def _avisar(self, texto, tipo="exito"):
        self.aviso.setText(texto)
        self.aviso.setStyleSheet(f"color: {tema.hex_(tipo)};")
        self.aviso.show()

    # ---------- acciones ----------

    def _conectar(self):
        sugerido = "Personal" if any(c.tipo != "personal" for c in onedrive.cuentas()) else "UTEC"
        nombre, ok = QInputDialog.getText(self, "Conectar OneDrive",
                                          "¿Cómo llamamos a esta cuenta? (por ejemplo UTEC o Personal)",
                                          text=sugerido)
        if not ok or not nombre.strip():
            return
        dialogo = DialogoConexion(nombre, self)
        dialogo.exec()
        self.refrescar()
        if dialogo.cuenta is not None:
            self._avisar(f"✓ Listo: tu OneDrive «{dialogo.cuenta.nombre}» está en {dialogo.cuenta.carpeta}.")
        elif dialogo.error:
            self._avisar(dialogo.error, "error")

    def _abrir(self):
        cuenta = self._elegida()
        if cuenta is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(cuenta.carpeta))

    def _montar(self):
        cuenta = self._elegida()
        if cuenta is None:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            onedrive.montar(cuenta)
            self._avisar(f"✓ «{cuenta.nombre}» está abierta.")
        except (onedrive.ErrorOneDrive, OSError) as exc:
            self._avisar(str(exc), "error")
        finally:
            QApplication.restoreOverrideCursor()
        self.refrescar()

    def _quitar(self):
        cuenta = self._elegida()
        if cuenta is None:
            return
        r = QMessageBox.question(
            self, "Quitar OneDrive",
            f"¿Desconecto «{cuenta.nombre}»? Tus archivos siguen en OneDrive; solo dejarán de verse "
            "en esta PC.\n\nSi Pandex acaba de guardar archivos ahí, espera un minuto a que terminen "
            "de subir.")
        if r != QMessageBox.StandardButton.Yes:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            onedrive.quitar(cuenta)
            self._avisar(f"Desconecté «{cuenta.nombre}».")
        except OSError as exc:
            self._avisar(f"No pude quitarla: {exc}", "error")
        finally:
            QApplication.restoreOverrideCursor()
        self.refrescar()
