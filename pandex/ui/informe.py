"""Ventana de resumen al terminar una tarea (si ``run`` devolvió ``"informe"``)."""

import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics, QGuiApplication
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from . import iconos, tema


class DialogoInforme(QDialog):
    def __init__(self, titulo, texto, carpeta=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        encabezado = QLabel(titulo)
        encabezado.setProperty("rol", "titulo")

        self.texto = QPlainTextEdit(readOnly=True)
        self.texto.setFont(tema.fuente_mono(9.5))
        self.texto.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.texto.setPlainText(texto)

        # del tamaño del contenido: un resumen corto no deja media ventana vacía
        metrica = QFontMetrics(self.texto.font())
        lineas = texto.splitlines() or [""]
        ancho = max(metrica.horizontalAdvance(l) for l in lineas) + 90
        alto = metrica.lineSpacing() * len(lineas) + 170
        self.resize(min(max(ancho, 480), 920), min(max(alto, 240), 600))

        copiar = QPushButton(iconos.icono("documento"), "Copiar")
        copiar.clicked.connect(lambda: QGuiApplication.clipboard().setText(texto))
        cerrar = QPushButton("Cerrar")
        cerrar.setProperty("rol", "primario")
        cerrar.setDefault(True)
        cerrar.clicked.connect(self.reject)
        botones = QHBoxLayout()
        botones.addWidget(copiar)
        if carpeta and Path(carpeta).is_dir():
            abrir = QPushButton("Abrir carpeta")
            abrir.clicked.connect(lambda: os.startfile(str(carpeta)))
            botones.addWidget(abrir)
        botones.addStretch()
        botones.addWidget(cerrar)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 16)
        layout.setSpacing(12)
        layout.addWidget(encabezado)
        layout.addWidget(self.texto, 1)
        layout.addLayout(botones)

    def showEvent(self, evento):
        super().showEvent(evento)
        tema.preparar_dialogo(self)
