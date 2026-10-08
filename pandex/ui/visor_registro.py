"""Ventana «Ver registro»: las últimas líneas de ``logs/pandex.log``."""

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QPlainTextEdit, QPushButton, QVBoxLayout

from ..rutas import LOG_FILE

LINEAS = 400


class VisorRegistro(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Registro de Pandex")
        self.resize(760, 460)

        self.texto = QPlainTextEdit(readOnly=True)
        self.texto.setFont(QFont("Consolas", 9))
        self.texto.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        recargar = QPushButton("Recargar")
        recargar.clicked.connect(self.cargar)
        botones.addButton(recargar, QDialogButtonBox.ButtonRole.ActionRole)
        botones.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.texto)
        layout.addWidget(botones)
        self.cargar()

    def cargar(self):
        if not LOG_FILE.exists():
            self.texto.setPlainText("Todavía no hay registro.")
            return
        with open(LOG_FILE, encoding="utf-8", errors="replace") as fh:
            self.texto.setPlainText("".join(fh.readlines()[-LINEAS:]))
        barra = self.texto.verticalScrollBar()
        barra.setValue(barra.maximum())
