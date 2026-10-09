"""Ventana «Configuración»: apariencia de la mascota, comportamiento y horario de cada tarea."""

from PyQt6.QtCore import QSize, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import __version__, accesos
from ..config import _es_de_fabrica
from . import iconos, logo, personajes, tema
from .sprites import Sprites

PROPIO = ("pixel", "Sprite sheet propio (config.json)")


def opciones_de_personaje(mascota):
    """Los personajes de ``assets/personajes/`` y, si configuraste uno, el tuyo."""
    opciones = personajes.lista()
    if not _es_de_fabrica(mascota.get("spritesheet")):
        opciones.append(PROPIO)
    return opciones


class VistaPrevia(QWidget):
    """La mascota tal como se verá. Se pinta solo cuando cambias algo."""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.personaje = config.mascota.get("personaje", personajes.POR_DEFECTO)
        self.opacidad = float(config.mascota.get("opacidad", 1.0))
        self._sprites = None
        self.setFixedSize(150, 150)

    def poner(self, personaje=None, opacidad=None):
        if personaje is not None:
            self.personaje = personaje
        if opacidad is not None:
            self.opacidad = opacidad
        self.update()

    def paintEvent(self, _evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(tema.color("superficie_2"))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 16, 16)
        p.setOpacity(self.opacidad)
        lado = 120
        if self.personaje == "pixel":
            if self._sprites is None:
                self._sprites = Sprites(self.config.mascota.get("spritesheet"))
            if self._sprites.ok:
                pix = self._sprites.frame("idle", 0, lado, lado)
                if pix is not None:
                    p.drawPixmap((self.width() - pix.width()) // 2, (self.height() - pix.height()) // 2, pix)
                    return
        pix = personajes.imagen(self.personaje, "idle", 126, self.devicePixelRatioF())
        ancho = round(pix.width() / pix.devicePixelRatio())
        alto = round(pix.height() / pix.devicePixelRatio())
        p.drawPixmap((self.width() - ancho) // 2, (self.height() - alto) // 2, pix)


def _tarjeta():
    marco = QFrame()
    marco.setProperty("rol", "tarjeta")
    return marco


def _titulo(texto, subtitulo=None):
    caja = QVBoxLayout()
    caja.setSpacing(2)
    t = QLabel(texto)
    t.setProperty("rol", "titulo")
    caja.addWidget(t)
    if subtitulo:
        s = QLabel(subtitulo)
        s.setProperty("rol", "suave")
        s.setWordWrap(True)
        caja.addWidget(s)
    caja.addSpacing(10)
    return caja


class DialogoConfiguracion(QDialog):
    def __init__(self, config, tareas, parent=None, al_buscar_actualizaciones=None):
        super().__init__(parent)
        self.config = config
        self.tareas = tareas
        self._al_buscar = al_buscar_actualizaciones
        self.setWindowTitle("Configuración de Pandex")
        self.resize(720, 520)

        self.navegacion = QListWidget()
        self.navegacion.setObjectName("navegacion")
        self.navegacion.setFixedWidth(180)
        self.navegacion.setIconSize(QSize(16, 16))
        self.paginas = QStackedWidget()
        for nombre, icono, pagina in (
            ("Apariencia", "mostrar", self._pagina_apariencia()),
            ("Comportamiento", "engranaje", self._pagina_comportamiento()),
            ("Tareas", "tarea", self._pagina_tareas()),
            ("Acerca de", "hola", self._pagina_acerca()),
        ):
            QListWidgetItem(iconos.icono(icono), nombre, self.navegacion)
            self.paginas.addWidget(pagina)
        self.navegacion.currentRowChanged.connect(self.paginas.setCurrentIndex)
        self.navegacion.setCurrentRow(0)

        lateral = QVBoxLayout()
        lateral.setContentsMargins(14, 18, 8, 14)
        marca = QLabel("Pandex")
        marca.setProperty("rol", "titulo")
        lateral.addWidget(marca)
        lateral.addSpacing(10)
        lateral.addWidget(self.navegacion, 1)

        guardar = QPushButton("Guardar")
        guardar.setProperty("rol", "primario")
        guardar.setDefault(True)
        guardar.clicked.connect(self._guardar)
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self.reject)
        botones = QHBoxLayout()
        botones.setSpacing(10)
        botones.addStretch()
        botones.addWidget(cancelar)
        botones.addWidget(guardar)

        derecha = QVBoxLayout()
        derecha.setContentsMargins(18, 18, 22, 16)
        derecha.setSpacing(12)  # si no, hereda el 0 de la ventana y todo queda pegado
        derecha.addWidget(self.paginas, 1)
        derecha.addLayout(botones)

        separador = QFrame()
        separador.setFixedWidth(1)
        separador.setStyleSheet(f"background: {tema.hex_('borde')};")

        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        lado = QWidget()
        lado.setObjectName("lateral")
        lado.setStyleSheet(f"QWidget#lateral {{ background: {tema.hex_('superficie_2')}; }}")
        lado.setLayout(lateral)
        raiz.addWidget(lado)
        raiz.addWidget(separador)
        raiz.addLayout(derecha, 1)

    def showEvent(self, evento):
        super().showEvent(evento)
        tema.preparar_dialogo(self)

    # ---------- páginas ----------

    def _pagina_apariencia(self):
        m = self.config.mascota
        pagina = QWidget()
        caja = QVBoxLayout(pagina)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.addLayout(_titulo("Apariencia", "Cómo se ve tu mascota en el escritorio."))

        fila = QHBoxLayout()
        self.vista = VistaPrevia(self.config)
        fila.addWidget(self.vista, 0, Qt.AlignmentFlag.AlignTop)
        fila.addSpacing(16)

        form = QFormLayout()
        form.setVerticalSpacing(12)
        self.nombre = QLineEdit(m.get("nombre", "Pandex"))
        form.addRow("Nombre", self.nombre)

        self.personaje = QComboBox()
        for clave, texto in opciones_de_personaje(m):
            self.personaje.addItem(texto, clave)
        self.personaje.setCurrentIndex(max(0, self.personaje.findData(m.get("personaje", personajes.POR_DEFECTO))))
        self.personaje.currentIndexChanged.connect(self._personaje_cambiado)
        form.addRow("Personaje", self.personaje)

        # el ícono de la app: la cara del personaje elegido, u otro fijo
        self.logo = QComboBox()
        self.logo.addItem("Igual que el personaje", logo.SIGUE_AL_PERSONAJE)
        for clave, texto in personajes.lista():
            self.logo.addItem(texto, clave)
        self.logo.setCurrentIndex(max(0, self.logo.findData(m.get("logo") or logo.SIGUE_AL_PERSONAJE)))
        self.logo.currentIndexChanged.connect(self._mostrar_logo)
        self.logo_vista = QLabel()
        self.logo_vista.setFixedSize(36, 36)
        fila_logo = QHBoxLayout()
        fila_logo.setSpacing(10)
        fila_logo.addWidget(self.logo_vista)
        fila_logo.addWidget(self.logo, 1)
        form.addRow("Logo", fila_logo)
        self._mostrar_logo()

        self.tamano, fila_tamano = self._deslizador(60, 400, int(m.get("tamano", 120)), " px")
        form.addRow("Tamaño", fila_tamano)
        self.opacidad, fila_opacidad = self._deslizador(20, 100, round(float(m.get("opacidad", 1.0)) * 100), " %")
        self.opacidad.valueChanged.connect(lambda v: self.vista.poner(opacidad=v / 100))
        form.addRow("Opacidad", fila_opacidad)
        fila.addLayout(form, 1)
        caja.addLayout(fila)
        caja.addStretch()
        return pagina

    def _personaje_cambiado(self, _indice=None):
        self.vista.poner(self.personaje.currentData())
        self._mostrar_logo()

    def _logo_elegido(self):
        return logo.elegido({"logo": self.logo.currentData(), "personaje": self.personaje.currentData()})

    def _mostrar_logo(self, _indice=None):
        self.logo_vista.setPixmap(logo.pixmap(36, self.devicePixelRatioF(), self._logo_elegido()))

    def _deslizador(self, minimo, maximo, valor, sufijo):
        deslizador = QSlider(Qt.Orientation.Horizontal)
        deslizador.setRange(minimo, maximo)
        deslizador.setValue(valor)
        etiqueta = QLabel(f"{valor}{sufijo}")
        etiqueta.setProperty("rol", "suave")
        etiqueta.setMinimumWidth(52)
        etiqueta.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        deslizador.valueChanged.connect(lambda v: etiqueta.setText(f"{v}{sufijo}"))
        fila = QHBoxLayout()
        fila.addWidget(deslizador, 1)
        fila.addWidget(etiqueta)
        return deslizador, fila

    def _pagina_comportamiento(self):
        m = self.config.mascota
        pagina = QWidget()
        caja = QVBoxLayout(pagina)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.addLayout(_titulo("Comportamiento", "Cómo te avisa y dónde vive."))

        tarjeta = _tarjeta()
        interno = QVBoxLayout(tarjeta)
        interno.setContentsMargins(16, 14, 16, 14)
        interno.setSpacing(10)
        self.globo = QCheckBox("Mostrar el globo de diálogo")
        self.globo.setChecked(bool(m.get("globo_activo", True)))
        interno.addWidget(self.globo)
        fila = QHBoxLayout()
        fila.addSpacing(26)
        fila.addWidget(QLabel("El globo dura"))
        self.globo_segundos = QSpinBox()
        self.globo_segundos.setRange(2, 30)
        self.globo_segundos.setSuffix(" s")
        self.globo_segundos.setValue(int(m.get("globo_segundos", 5)))
        self.globo.toggled.connect(self.globo_segundos.setEnabled)
        self.globo_segundos.setEnabled(self.globo.isChecked())
        fila.addWidget(self.globo_segundos)
        fila.addStretch()
        interno.addLayout(fila)

        self.encima = QCheckBox("Siempre encima de las demás ventanas")
        self.encima.setChecked(bool(m.get("siempre_encima", True)))
        interno.addWidget(self.encima)
        self.inicio = QCheckBox("Arrancar con Windows")
        self.inicio.setChecked(accesos.arranca_con_windows())
        interno.addWidget(self.inicio)
        self.avisar_nuevas = QCheckBox("Avisarme cuando haya una versión nueva (revisa una vez al día)")
        self.avisar_nuevas.setChecked(bool(self.config.datos.get("buscar_actualizaciones", True)))
        interno.addWidget(self.avisar_nuevas)
        caja.addWidget(tarjeta)

        caja.addSpacing(10)
        acceso = _tarjeta()
        fila = QHBoxLayout(acceso)
        fila.setContentsMargins(16, 12, 16, 12)
        texto = QLabel("<b>Acceso directo</b><br>Un ícono en tu Escritorio, con el logo que "
                       "elegiste: doble clic y aparece la mascota.")
        texto.setWordWrap(True)
        fila.addWidget(texto, 1)
        crear = QPushButton(iconos.icono("descargar"), "Crear en el Escritorio")
        crear.clicked.connect(self._crear_acceso)
        fila.addWidget(crear)
        caja.addWidget(acceso)
        caja.addStretch()
        return pagina

    def _pagina_tareas(self):
        pagina = QWidget()
        caja = QVBoxLayout(pagina)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.addLayout(_titulo("Tareas", "Actívalas o dales un horario (formato cron). "
                                         "Vacío = solo cuando la pidas desde el menú."))
        self.filas = {}
        if not self.tareas:
            vacio = QLabel("No hay tareas en la carpeta tasks/.")
            vacio.setProperty("rol", "suave")
            caja.addWidget(vacio)
            caja.addStretch()
            return pagina

        lista = QWidget()
        filas = QVBoxLayout(lista)
        filas.setContentsMargins(0, 0, 6, 0)
        filas.setSpacing(10)
        for tarea in self.tareas:
            opciones = self.config.tarea(tarea.id)
            tarjeta = _tarjeta()
            interno = QVBoxLayout(tarjeta)
            interno.setContentsMargins(16, 12, 16, 12)
            cabecera = QHBoxLayout()
            nombre = QLabel(f"<b>{tarea.nombre}</b>")
            cabecera.addWidget(nombre, 1)
            activa = QCheckBox("Activa")
            activa.setChecked(bool(opciones.get("activa", True)))
            cabecera.addWidget(activa)
            interno.addLayout(cabecera)
            if tarea.descripcion:
                descripcion = QLabel(tarea.descripcion)
                descripcion.setProperty("rol", "suave")
                descripcion.setWordWrap(True)
                interno.addWidget(descripcion)
            cron = QLineEdit(opciones.get("schedule") or (tarea.schedule or ""))
            cron.setPlaceholderText("Horario: vacío = solo manual  ·  ej. 0 19 * * 1-5")
            interno.addWidget(cron)
            filas.addWidget(tarjeta)
            self.filas[tarea.id] = (activa, cron)
        filas.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(lista)
        scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }")
        caja.addWidget(scroll, 1)
        return pagina

    def _pagina_acerca(self):
        pagina = QWidget()
        caja = QVBoxLayout(pagina)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.addLayout(_titulo("Acerca de"))

        fila = QHBoxLayout()
        logo_ = QLabel()
        logo_.setFixedSize(72, 72)
        logo_.setPixmap(logo.pixmap(72, self.devicePixelRatioF()))
        fila.addWidget(logo_)
        fila.addSpacing(12)
        texto = QLabel(
            f"<b>Pandex {__version__}</b><br>Una mascota que ordena tus cursos de Canvas "
            "y convierte tu material a Markdown. Todo en tu PC, gratis y sin IA.")
        texto.setWordWrap(True)
        fila.addWidget(texto, 1)
        caja.addLayout(fila)
        caja.addSpacing(14)

        botones = QHBoxLayout()
        actualizar = QPushButton(iconos.icono("descargar"), "Buscar actualizaciones")
        actualizar.clicked.connect(self._buscar_actualizaciones)
        actualizar.setEnabled(self._al_buscar is not None)
        github = QPushButton("Ver en GitHub")
        github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/frankrubio/pandex")))
        botones.addWidget(actualizar)
        botones.addWidget(github)
        botones.addStretch()
        caja.addLayout(botones)
        caja.addStretch()
        return pagina

    def _crear_acceso(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            ruta = accesos.crear_en_escritorio(personajes.ruta_icono(self._logo_elegido()))
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Acceso directo", f"No pude crearlo:\n{exc}")
            return
        QApplication.restoreOverrideCursor()
        QMessageBox.information(self, "Acceso directo", f"Listo: «Pandex» está en tu Escritorio.\n{ruta}")

    def _buscar_actualizaciones(self):
        if self._al_buscar:
            self._al_buscar()

    # ---------- guardar ----------

    def _guardar(self):
        m = self.config.mascota
        m["nombre"] = self.nombre.text().strip() or "Pandex"
        m["personaje"] = self.personaje.currentData()
        m["logo"] = self.logo.currentData()
        m["tamano"] = self.tamano.value()
        m["opacidad"] = round(self.opacidad.value() / 100, 2)
        m["globo_activo"] = self.globo.isChecked()
        m["globo_segundos"] = self.globo_segundos.value()
        m["siempre_encima"] = self.encima.isChecked()
        self.config.datos["buscar_actualizaciones"] = self.avisar_nuevas.isChecked()

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

