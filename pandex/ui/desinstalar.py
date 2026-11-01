"""Ventana «Desinstalar Pandex…»: la lista exacta de lo que se quita, y confirmar.

La lógica está en ``pandex/desinstalar.py`` (la misma que usan ``desinstalar.sh`` y
``desinstalar.bat``). Al terminar, Pandex se cierra; la carpeta del proyecto se borra a mano.
"""

import subprocess

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from .. import desinstalar
from ..rutas import RAIZ, WINDOWS
from . import tema
from .actualizacion import _Hilo


def _borrar_venv_al_salir():
    """En Windows el ``.venv`` está en uso mientras Pandex corre: lo borra cmd unos segundos después.

    Espera con ``ping`` y no con ``timeout``: sin consola (DETACHED_PROCESS), ``timeout``
    termina al instante y el ``.venv`` se borraría mientras Pandex aún lo usa.
    """
    venv = RAIZ / ".venv"
    if not venv.exists():
        return
    subprocess.Popen(
        ["cmd", "/c", f'ping -n 6 127.0.0.1 >nul & rmdir /s /q "{venv}"'],
        creationflags=getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0),
        close_fds=True,
    )


class DialogoDesinstalar(QDialog):
    def __init__(self, al_terminar=None, parent=None):
        super().__init__(parent)
        self._al_terminar = al_terminar
        self._hilo = None
        self.setWindowTitle("Desinstalar Pandex")
        self.setMinimumWidth(520)

        self.titulo = QLabel("¿Desinstalar Pandex?")
        self.titulo.setProperty("rol", "titulo")
        explicacion = QLabel("Se quita todo lo que Pandex creó en tu PC. <b>Tu carpeta de cursos no se "
                             "toca</b>, ni tus archivos de OneDrive.")
        explicacion.setWordWrap(True)
        self.conservar = QCheckBox("Conservar mi configuración (config.json) para reinstalar después")
        self.conservar.setChecked(True)
        self.conservar.toggled.connect(self._mostrar_lista)
        self.lista = QTextBrowser()
        self.lista.setMinimumHeight(180)

        self.cancelar = QPushButton("Cancelar")
        self.cancelar.clicked.connect(self.reject)
        self.principal = QPushButton("Desinstalar")
        self.principal.setProperty("rol", "primario")
        self.principal.clicked.connect(self._desinstalar)
        botones = QHBoxLayout()
        botones.addStretch()
        botones.addWidget(self.cancelar)
        botones.addWidget(self.principal)

        caja = QVBoxLayout(self)
        caja.setContentsMargins(24, 22, 24, 18)
        caja.setSpacing(10)
        caja.addWidget(self.titulo)
        caja.addWidget(explicacion)
        caja.addWidget(self.lista, 1)
        caja.addWidget(self.conservar)
        caja.addSpacing(6)
        caja.addLayout(botones)
        self._mostrar_lista()

    def showEvent(self, evento):
        super().showEvent(evento)
        tema.preparar_dialogo(self)

    def pasos(self):
        # en Linux el .venv se puede borrar aunque esté en uso; en Windows lo borra cmd al salir
        return desinstalar.plan(RAIZ, self.conservar.isChecked(), con_venv=not WINDOWS)

    def _mostrar_lista(self, *_):
        partes = []
        for paso in self.pasos():
            rutas = "".join(f"<br><small>{r}</small>" for r in paso.rutas)
            partes.append(f"• {paso.nombre}{rutas}")
        if WINDOWS and (RAIZ / ".venv").exists():
            partes.append(f"• Entorno de Python de Pandex (.venv)<br><small>{RAIZ / '.venv'}</small>")
        self.lista.setHtml("<br>".join(partes) or "No encontré nada que quitar.")

    def _desinstalar(self):
        pasos = self.pasos()
        self.principal.setEnabled(False)
        self.cancelar.setEnabled(False)
        self.conservar.setEnabled(False)
        self.titulo.setText("Desinstalando…")
        self._hilo = _Hilo(lambda _aviso: desinstalar.ejecutar(pasos))
        self._hilo.listo.connect(self._al_desinstalar)
        self._hilo.fallo.connect(lambda texto: self._al_desinstalar([], texto))
        self._hilo.start()

    def _al_desinstalar(self, quedan, error=None):
        if WINDOWS:
            _borrar_venv_al_salir()
        self.titulo.setText("Pandex se desinstaló")
        lineas = []
        if quedan:
            lineas.append("No pude borrar (bórralo a mano):")
            lineas += [f"• {r}" for r in quedan]
        if error:
            lineas.append(error)
        lineas.append(desinstalar.como_borrar_la_carpeta(RAIZ))
        self.lista.setHtml("<br>".join(lineas))
        self.principal.setText("Cerrar Pandex")
        self.principal.setEnabled(True)
        self.principal.clicked.disconnect()
        self.principal.clicked.connect(self._cerrar_pandex)

    def _cerrar_pandex(self):
        self.accept()
        if self._al_terminar:
            self._al_terminar()

    def reject(self):
        if self._hilo is not None:
            return  # ya se desinstaló (o está en eso): solo queda cerrar Pandex
        super().reject()
