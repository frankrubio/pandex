"""Punto de entrada de Pandex.

    .venv\\Scripts\\pythonw.exe main.py          (sin consola; es lo que usa el acceso directo)
    .venv\\Scripts\\python.exe  main.py --test   (abre y se cierra a los 3 s: prueba de humo)
"""

import ctypes
import getpass
import sys

from PyQt6.QtCore import QLibraryInfo, QTimer, QTranslator
from PyQt6.QtGui import QIcon
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication

from pandex.app import PandexApp
from pandex.rutas import ICONO
from pandex.ui import tema

ID_APP = "Pandex.Mascota"
CANAL = f"Pandex-{getpass.getuser()}"


def identidad_en_windows():
    """Sin esto la barra de tareas agrupa a Pandex bajo el ícono de Python."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ID_APP)
    except (AttributeError, OSError):
        pass


def avisar_al_que_ya_corre():
    """Si Pandex ya está abierto, le pide que se asome y devuelve True."""
    socket = QLocalSocket()
    socket.connectToServer(CANAL)
    if not socket.waitForConnected(300):
        return False
    socket.write(b"asomate")
    socket.flush()
    socket.waitForBytesWritten(300)
    socket.disconnectFromServer()
    return True


def escuchar(app):
    """Deja un canal abierto para que un segundo doble clic lo encuentre."""
    QLocalServer.removeServer(CANAL)  # uno viejo, si Pandex se cerró de golpe
    servidor = QLocalServer(app)
    servidor.listen(CANAL)

    def atender():
        while servidor.hasPendingConnections():
            servidor.nextPendingConnection().disconnectFromServer()
            app.asomarse()

    servidor.newConnection.connect(atender)
    return servidor


def main():
    identidad_en_windows()
    qapp = QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)
    qapp.setApplicationName("Pandex")
    # «Cerrar», «Guardar», «Cancelar»… en vez de Close/Save/Cancel
    traductor = QTranslator(qapp)
    if traductor.load("qtbase_es", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        qapp.installTranslator(traductor)
    if ICONO.exists():
        qapp.setWindowIcon(QIcon(str(ICONO)))

    if avisar_al_que_ya_corre():
        return 0  # un solo panda: el que ya estaba se asoma

    tema.aplicar(qapp)
    app = PandexApp(qapp)
    tema.seguir_al_sistema(qapp, app.tema_cambiado)
    app.servidor = escuchar(app)
    app.iniciar()
    if "--test" in sys.argv:
        QTimer.singleShot(3000, app.salir)
    return qapp.exec()


if __name__ == "__main__":
    sys.exit(main())
