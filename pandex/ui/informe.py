"""Ventana de resumen al terminar una tarea (si ``run`` devolvió ``"informe"``)."""

import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontMetrics, QGuiApplication
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QPlainTextEdit, QPushButton, QVBoxLayout


class DialogoInforme(QDialog):
    def __init__(self, titulo, texto, carpeta=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        self.texto = QPlainTextEdit(readOnly=True)
        self.texto.setFont(QFont("Consolas", 10))
        self.texto.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.texto.setPlainText(texto)

        # del tamaño del contenido: un resumen corto no deja media ventana vacía
        metrica = QFontMetrics(self.texto.font())
        lineas = texto.splitlines() or [""]
        ancho = max(metrica.horizontalAdvance(l) for l in lineas) + 60
        alto = metrica.lineSpacing() * len(lineas) + 110
        self.resize(min(max(ancho, 460), 900), min(max(alto, 200), 560))

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        copiar = QPushButton("Copiar")
        copiar.clicked.connect(lambda: QGuiApplication.clipboard().setText(texto))
        botones.addButton(copiar, QDialogButtonBox.ButtonRole.ActionRole)
        if carpeta and Path(carpeta).is_dir():
            abrir = QPushButton("Abrir carpeta")
            abrir.clicked.connect(lambda: os.startfile(str(carpeta)))
            botones.addButton(abrir, QDialogButtonBox.ButtonRole.ActionRole)
        botones.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.texto)
        layout.addWidget(botones)
