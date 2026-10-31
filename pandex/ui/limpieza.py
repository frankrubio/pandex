"""Ventana «Liberar espacio»: lo que sobra, con su tamaño, y un botón.

Se abre sola la primera vez que usas una versión nueva (si hay al menos 20 MB que liberar)
y cuando quieras desde Configuración → Comportamiento → Liberar espacio…
Lo de Pandex ya se limpió antes de abrirla; aquí solo se pregunta por lo de fuera.
"""

from PyQt6.QtCore import QFile
from PyQt6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .. import limpieza
from . import tema
from .actualizacion import _Hilo


def _papelera(ruta):
    """Manda a la papelera si el sistema puede (así se puede recuperar)."""
    try:
        return bool(QFile.moveToTrash(str(ruta))[0])
    except Exception:
        return False


class DialogoLiberar(QDialog):
    def __init__(self, elementos, liberado=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Liberar espacio")
        self.setMinimumWidth(500)
        self._hilo = None
        self.casillas = []

        self.titulo = QLabel()
        self.titulo.setProperty("rol", "titulo")
        caja = QVBoxLayout(self)
        caja.setContentsMargins(24, 22, 24, 18)
        caja.setSpacing(10)
        caja.addWidget(self.titulo)
        if liberado:
            hecho = QLabel(f"✓ Ya quité {limpieza.texto_tamano(liberado)} de cosas de Pandex que no se usaban.")
            hecho.setProperty("rol", "suave")
            caja.addWidget(hecho)

        for elemento in elementos:
            casilla = QCheckBox(f"{elemento.nombre} · {limpieza.texto_tamano(elemento.tamano)}")
            casilla.setChecked(elemento.marcado)
            casilla.toggled.connect(self._actualizar_titulo)
            caja.addWidget(casilla)
            if elemento.nota:
                nota = QLabel(elemento.nota)
                nota.setProperty("rol", "suave")
                nota.setWordWrap(True)
                nota.setContentsMargins(26, 0, 0, 4)
                caja.addWidget(nota)
            self.casillas.append((casilla, elemento))

        self.resultado = QLabel()
        self.resultado.setWordWrap(True)
        self.resultado.hide()
        caja.addWidget(self.resultado)

        self.cerrar = QPushButton("Ahora no" if elementos else "Cerrar")
        self.cerrar.clicked.connect(self.reject)
        self.principal = QPushButton("Liberar")
        self.principal.setProperty("rol", "primario")
        self.principal.clicked.connect(self._liberar)
        self.principal.setVisible(bool(elementos))
        botones = QHBoxLayout()
        botones.addStretch()
        botones.addWidget(self.cerrar)
        botones.addWidget(self.principal)
        caja.addSpacing(6)
        caja.addLayout(botones)
        self._actualizar_titulo()

    def showEvent(self, evento):
        super().showEvent(evento)
        tema.preparar_dialogo(self)

    def elegidos(self):
        return [e for casilla, e in self.casillas if casilla.isChecked()]

    def _actualizar_titulo(self, *_):
        if not self.casillas:
            self.titulo.setText("No hay nada más que liberar")
            return
        total = sum(e.tamano for e in self.elegidos())
        self.titulo.setText(f"Puedo liberar {limpieza.texto_tamano(total)}")
        self.principal.setEnabled(total > 0)

    def _liberar(self):
        elegidos = self.elegidos()
        self.principal.setEnabled(False)
        self.cerrar.setEnabled(False)
        for casilla, _ in self.casillas:
            casilla.setEnabled(False)
        self.titulo.setText("Liberando…")
        self._hilo = _Hilo(lambda _aviso: limpieza.liberar(elegidos, _papelera))
        self._hilo.listo.connect(self._al_terminar)
        self._hilo.fallo.connect(lambda texto: self._al_terminar((0, []), texto))
        self._hilo.start()

    def _al_terminar(self, resultado, error=None):
        liberado, fallidos = resultado
        self.titulo.setText(f"✓ Liberé {limpieza.texto_tamano(liberado)}" if liberado else "No pude liberar nada")
        lineas = []
        if fallidos:
            lineas.append("No pude borrar (quizás está en uso; ciérralo y vuelve a intentar):")
            lineas += [f"• {ruta}" for ruta in fallidos]
        if error:
            lineas.append(error)
        if lineas:
            self.resultado.setText("<br>".join(lineas))
            self.resultado.show()
        self.cerrar.setText("Cerrar")
        self.cerrar.setEnabled(True)
        self.principal.hide()

    def reject(self):
        if self._hilo and self._hilo.isRunning():
            return  # mientras borra, no se cierra a medias
        super().reject()


def revisar(parent=None, al_terminar=None, solo_si_vale_la_pena=False):
    """Limpia lo de Pandex en otro hilo y abre la ventana con lo de fuera.

    Con ``solo_si_vale_la_pena`` (al estrenar una versión), solo se abre si hay al menos
    20 MB que liberar fuera de Pandex; si no, ``al_terminar(liberado)`` recibe lo que se limpió.
    """
    hilo = _Hilo(lambda _aviso: limpieza.al_estrenar_version())

    def listo(r):
        afuera = sum(e.tamano for e in r["externos"])
        if solo_si_vale_la_pena and afuera < limpieza.MINIMO_PARA_AVISAR:
            if al_terminar:
                al_terminar(r["liberado"])
            return
        dialogo = DialogoLiberar(r["externos"], r["liberado"], parent)
        dialogo.show()
        revisar._dialogo = dialogo  # que no lo recoja el recolector mientras está abierto
        if al_terminar:
            al_terminar(0)

    hilo.listo.connect(listo)
    hilo.start()
    return hilo
