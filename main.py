"""Punto de entrada de Pandex.

    .venv\\Scripts\\pythonw.exe main.py          (Windows, sin consola; es lo que usa el acceso directo)
    .venv\\Scripts\\python.exe  main.py --test   (abre y se cierra a los 3 s: prueba de humo)
    .venv/bin/python main.py                     (Linux)
    main.py --pendientes                         (lo lanza el sistema a la hora de una tarea: si hay
                                                  algo pendiente lo hace y se cierra; si no, sale enseguida)
"""

import getpass
import os
import sys

ID_APP = "Pandex.Mascota"
CANAL = f"Pandex-{getpass.getuser()}"


def identidad_en_windows():
    """Sin esto la barra de tareas agrupa a Pandex bajo el ícono de Python."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ID_APP)
    except (AttributeError, OSError):
        pass


def preparar_linux():
    """En Wayland una ventana no puede moverse ni quedar siempre encima: la mascota necesita
    ambas cosas, así que se abre por XWayland (``xcb``) salvo que el usuario elija otra.
    Sin pantalla (p. ej. lanzado por el sistema antes de iniciar sesión) trabaja invisible."""
    if not sys.platform.startswith("linux"):
        return
    if os.environ.get("WAYLAND_DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    elif not os.environ.get("DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def hay_pendientes():
    """Sin cargar Qt (milisegundos): ¿alguna tarea programada se quedó sin correr?"""
    from pandex import pendientes

    try:
        return bool(pendientes.vencidas())
    except Exception:
        return True  # ante la duda, que Pandex lo revise con calma


def avisar_al_que_ya_corre(mensaje=b"asomate"):
    """Si Pandex ya está abierto, le pasa el mensaje y devuelve True."""
    from PyQt6.QtNetwork import QLocalSocket

    socket = QLocalSocket()
    socket.connectToServer(CANAL)
    if not socket.waitForConnected(300):
        return False
    socket.write(mensaje)
    socket.flush()
    socket.waitForBytesWritten(300)
    socket.disconnectFromServer()
    return True


def escuchar(app):
    """Deja un canal abierto para que un segundo doble clic (o el sistema) lo encuentre."""
    from PyQt6.QtNetwork import QLocalServer

    QLocalServer.removeServer(CANAL)  # uno viejo, si Pandex se cerró de golpe
    servidor = QLocalServer(app)
    servidor.listen(CANAL)

    def atender():
        while servidor.hasPendingConnections():
            conexion = servidor.nextPendingConnection()
            conexion.waitForReadyRead(300)
            mensaje = bytes(conexion.readAll())
            conexion.disconnectFromServer()
            if mensaje == b"pendientes":
                app._ponerse_al_dia()
            else:
                app.asomarse()

    servidor.newConnection.connect(atender)
    return servidor


def main():
    pendientes = "--pendientes" in sys.argv
    if pendientes and not hay_pendientes():
        return 0  # lo despertó el sistema y no hay nada que hacer: ni abre la ventana

    identidad_en_windows()
    preparar_linux()
    from PyQt6.QtCore import QLibraryInfo, QTimer, QTranslator
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication

    qapp = QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)
    qapp.setApplicationName("Pandex")
    qapp.setDesktopFileName("pandex")  # une la ventana con pandex.desktop (ícono y agrupación en Linux)
    # «Cerrar», «Guardar», «Cancelar»… en vez de Close/Save/Cancel
    traductor = QTranslator(qapp)
    if traductor.load("qtbase_es", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        qapp.installTranslator(traductor)

    from pandex.rutas import ICONO

    if ICONO.exists():
        qapp.setWindowIcon(QIcon(str(ICONO)))

    if avisar_al_que_ya_corre(b"pendientes" if pendientes else b"asomate"):
        return 0  # un solo panda: el que ya estaba se asoma (o hace lo pendiente)

    from pandex.app import PandexApp
    from pandex.ui import tema

    tema.aplicar(qapp)
    app = PandexApp(qapp, salir_al_terminar=pendientes)
    tema.seguir_al_sistema(qapp, app.tema_cambiado)
    app.servidor = escuchar(app)
    app.iniciar()
    if "--test" in sys.argv:
        QTimer.singleShot(3000, app.salir)
    return qapp.exec()


if __name__ == "__main__":
    sys.exit(main())
