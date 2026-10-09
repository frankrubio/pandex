"""Ventana «Ver registro»: las últimas líneas de ``logs/pandex.log``, con filtro."""

import re

from PyQt6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from ..rutas import LOG_FILE
from . import iconos, tema

LINEAS = 400

_MARCA = re.compile(r"^\d{4}-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2}),\d{3} ")


def legible(linea):
    """``2026-10-08 19:56:01,123 [INFO]…`` → ``08/10 7:56:01 p. m. [INFO]…``"""
    m = _MARCA.match(linea)
    if not m:
        return linea
    mes, dia, h, mi, s = m.groups()
    h = int(h)
    return f"{dia}/{mes} {(h % 12) or 12}:{mi}:{s} {'a. m.' if h < 12 else 'p. m.'} {linea[m.end():]}"


class _Colores(QSyntaxHighlighter):
    """Avisos y errores resaltados; solo colorea lo que está en pantalla."""

    def __init__(self, documento):
        super().__init__(documento)
        self._formatos = {}
        for nivel, nombre in (("[WARNING]", "aviso"), ("[ERROR]", "error"), ("[CRITICAL]", "error")):
            f = QTextCharFormat()
            f.setForeground(QColor(tema.hex_(nombre)))
            self._formatos[nivel] = f
        self._suave = QTextCharFormat()
        self._suave.setForeground(QColor(tema.hex_("texto_suave")))

    def highlightBlock(self, texto):
        if len(texto) > 19 and texto[4] == "-":  # la fecha al inicio, más tenue
            self.setFormat(0, 19, self._suave)
        for nivel, formato in self._formatos.items():
            i = texto.find(nivel)
            if i >= 0:
                self.setFormat(i, len(texto) - i, formato)
                return


class VisorRegistro(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Registro de Pandex")
        self.resize(820, 500)
        self._lineas = []

        titulo = QLabel("Registro")
        titulo.setProperty("rol", "titulo")
        ayuda = QLabel("Qué hizo Pandex y por qué. Útil si algo falla.")
        ayuda.setProperty("rol", "suave")

        self.filtro = QLineEdit()
        self.filtro.setPlaceholderText("Filtrar…  (p. ej. canvas, error, el nombre de un archivo)")
        self.filtro.setClearButtonEnabled(True)
        self.filtro.textChanged.connect(self._mostrar)
        self.solo_problemas = QCheckBox("Solo avisos y errores")
        self.solo_problemas.toggled.connect(self._mostrar)
        filtros = QHBoxLayout()
        filtros.addWidget(self.filtro, 1)
        filtros.addWidget(self.solo_problemas)

        self.texto = QPlainTextEdit(readOnly=True)
        self.texto.setFont(tema.fuente_mono(9))
        self.texto.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._colores = _Colores(self.texto.document())

        recargar = QPushButton(iconos.icono("recargar"), "Recargar")
        recargar.clicked.connect(self.cargar)
        cerrar = QPushButton("Cerrar")
        cerrar.setProperty("rol", "primario")
        cerrar.clicked.connect(self.reject)
        botones = QHBoxLayout()
        botones.addWidget(recargar)
        botones.addStretch()
        botones.addWidget(cerrar)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 16)
        layout.setSpacing(10)
        layout.addWidget(titulo)
        layout.addWidget(ayuda)
        layout.addLayout(filtros)
        layout.addWidget(self.texto, 1)
        layout.addLayout(botones)
        self.cargar()

    def showEvent(self, evento):
        super().showEvent(evento)
        tema.preparar_dialogo(self)

    def cargar(self):
        if not LOG_FILE.exists():
            self._lineas = []
            self.texto.setPlainText("Todavía no hay registro.")
            return
        with open(LOG_FILE, encoding="utf-8", errors="replace") as fh:
            self._lineas = fh.read().splitlines()[-LINEAS:]
        self._mostrar()

    def _mostrar(self, *_):
        buscado = self.filtro.text().strip().lower()
        problemas = self.solo_problemas.isChecked()
        lineas = [l for l in self._lineas
                  if (not buscado or buscado in l.lower())
                  and (not problemas or "[WARNING]" in l or "[ERROR]" in l or "[CRITICAL]" in l)]
        self.texto.setPlainText("\n".join(map(legible, lineas)) if lineas else "Nada coincide con el filtro.")
        barra = self.texto.verticalScrollBar()
        barra.setValue(barra.maximum())
