"""Ventana «Configuración»: apariencia de la mascota y horario de cada tarea."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from .. import accesos


class DialogoConfiguracion(QDialog):
    def __init__(self, config, tareas, parent=None):
        super().__init__(parent)
        self.config = config
        self.tareas = tareas
        self.setWindowTitle("Configuración de Pandex")
        self.setMinimumWidth(420)

        raiz = QVBoxLayout(self)
        raiz.addWidget(self._grupo_mascota())
        raiz.addWidget(self._grupo_tareas())
        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self._guardar)
        botones.rejected.connect(self.reject)
        raiz.addWidget(botones)

    def _grupo_mascota(self):
        m = self.config.mascota
        caja = QGroupBox("Mascota")
        form = QFormLayout(caja)

        self.nombre = QLineEdit(m.get("nombre", "Pandex"))
        form.addRow("Nombre:", self.nombre)

        self.tamano = QSpinBox()
        self.tamano.setRange(60, 400)
        self.tamano.setSuffix(" px")
        self.tamano.setValue(int(m.get("tamano", 120)))
        form.addRow("Alto:", self.tamano)

        self.opacidad = QDoubleSpinBox()
        self.opacidad.setRange(0.2, 1.0)
        self.opacidad.setSingleStep(0.05)
        self.opacidad.setValue(float(m.get("opacidad", 1.0)))
        form.addRow("Opacidad:", self.opacidad)

        self.globo = QCheckBox("Mostrar globo de diálogo")
        self.globo.setChecked(bool(m.get("globo_activo", True)))
        form.addRow(self.globo)

        self.animacion = QCheckBox("Animaciones (saltito al saludar, temblor al fallar)")
        self.animacion.setChecked(bool(m.get("animacion", True)))
        form.addRow(self.animacion)

        self.encima = QCheckBox("Siempre encima de las demás ventanas")
        self.encima.setChecked(bool(m.get("siempre_encima", True)))
        form.addRow(self.encima)

        self.inicio = QCheckBox("Arrancar con Windows")
        self.inicio.setChecked(accesos.arranca_con_windows())
        form.addRow(self.inicio)
        return caja

    def _grupo_tareas(self):
        caja = QGroupBox("Tareas")
        form = QFormLayout(caja)
        self.filas = {}
        if not self.tareas:
            form.addRow(QLabel("No hay tareas en la carpeta tasks/."))
            return caja

        for tarea in self.tareas:
            opciones = self.config.tarea(tarea.id)
            activa = QCheckBox("Activa")
            activa.setChecked(bool(opciones.get("activa", True)))
            cron = QLineEdit(opciones.get("schedule") or (tarea.schedule or ""))
            cron.setPlaceholderText("vacío = solo manual   ·   ej: 0 19 * * 1-5")
            etiqueta = QLabel(f"<b>{tarea.nombre}</b><br><small>{tarea.descripcion}</small>")
            etiqueta.setTextFormat(Qt.TextFormat.RichText)
            form.addRow(etiqueta, activa)
            form.addRow("Horario (cron):", cron)
            self.filas[tarea.id] = (activa, cron)
        return caja

    def _guardar(self):
        m = self.config.mascota
        m["nombre"] = self.nombre.text().strip() or "Pandex"
        m["tamano"] = self.tamano.value()
        m["opacidad"] = round(self.opacidad.value(), 2)
        m["globo_activo"] = self.globo.isChecked()
        m["animacion"] = self.animacion.isChecked()
        m["siempre_encima"] = self.encima.isChecked()

        for task_id, (activa, cron) in self.filas.items():
            opciones = self.config.tarea(task_id)
            opciones["activa"] = activa.isChecked()
            opciones["schedule"] = cron.text().strip() or None

        if self.inicio.isChecked() != accesos.arranca_con_windows():
            try:
                if self.inicio.isChecked():
                    accesos.activar_arranque()
                else:
                    accesos.desactivar_arranque()
            except Exception as exc:
                QMessageBox.warning(self, "Arranque con Windows", f"No pude cambiarlo:\n{exc}")
        self.config.datos["arrancar_con_windows"] = accesos.arranca_con_windows()

        self.config.guardar()
        self.accept()
