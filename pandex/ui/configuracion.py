"""Ventana «Configuración»: apariencia de la mascota, comportamiento y horario de cada tarea."""

import re

from PyQt6.QtCore import QLocale, QSize, Qt, QTime, QUrl
from PyQt6.QtGui import QDesktopServices, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
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
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from .. import __version__, accesos, personaje_nuevo
from . import iconos, logo, personajes, tema

HORARIOS = (("manual", "Solo cuando lo pida"), ("diario", "Todos los días"),
            ("semana", "De lunes a viernes"), ("cron", "Personalizado (cron)"))
ESPANOL = QLocale(QLocale.Language.Spanish, QLocale.Country.Peru)  # «7:00 p. m.»
_SIMPLE = re.compile(r"^(\d{1,2}) (\d{1,2}) \* \* (\*|1-5)$")


def leer_horario(cron):
    """``"0 19 * * 1-5"`` → ``("semana", QTime(19, 0))``; lo que no es simple, ``"cron"``."""
    if not cron:
        return "manual", QTime(19, 0)
    m = _SIMPLE.match(cron.strip())
    if m and int(m[1]) < 60 and int(m[2]) < 24:
        return ("diario" if m[3] == "*" else "semana"), QTime(int(m[2]), int(m[1]))
    return "cron", QTime(19, 0)


def armar_horario(tipo, hora, texto=""):
    if tipo == "diario":
        return f"{hora.minute()} {hora.hour()} * * *"
    if tipo == "semana":
        return f"{hora.minute()} {hora.hour()} * * 1-5"
    if tipo == "cron":
        return texto.strip() or None
    return None


class Horario(QWidget):
    """Cuándo corre sola una tarea, sin tener que saber cron."""

    def __init__(self, cron, parent=None):
        super().__init__(parent)
        tipo, hora = leer_horario(cron)
        self.tipo = QComboBox()
        for clave, texto in HORARIOS:
            self.tipo.addItem(texto, clave)
        self.tipo.setCurrentIndex(self.tipo.findData(tipo))
        self.hora = QTimeEdit(hora)
        self.hora.setLocale(ESPANOL)
        self.hora.setDisplayFormat("h:mm ap")
        self.a_las = QLabel("a las")
        self.cron = QLineEdit(cron or "")
        self.cron.setPlaceholderText("minuto hora día mes día-semana · ej. 0 19 * * 1-5")
        fila = QHBoxLayout(self)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(8)
        fila.addWidget(self.tipo)
        fila.addWidget(self.a_las)
        fila.addWidget(self.hora)
        fila.addWidget(self.cron, 1)
        fila.addStretch()
        self.tipo.currentIndexChanged.connect(self._mostrar)
        self._mostrar()

    def _mostrar(self, *_):
        tipo = self.tipo.currentData()
        con_hora = tipo in ("diario", "semana")
        self.a_las.setVisible(con_hora)
        self.hora.setVisible(con_hora)
        self.cron.setVisible(tipo == "cron")

    def valor(self):
        return armar_horario(self.tipo.currentData(), self.hora.time(), self.cron.text())


class VistaPrevia(QWidget):
    """La mascota tal como se verá. Se pinta solo cuando cambias algo."""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.personaje = config.mascota.get("personaje", personajes.POR_DEFECTO)
        self.opacidad = float(config.mascota.get("opacidad", 1.0))
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
        self.resize(720, 560)

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
        form.addRow("Personaje", self.personaje)
        # el ícono de la app: la cara del personaje elegido, u otro fijo
        self.logo = QComboBox()
        self._llenar_combos(m.get("personaje", personajes.POR_DEFECTO),
                            m.get("logo") or logo.SIGUE_AL_PERSONAJE)
        self.personaje.currentIndexChanged.connect(self._personaje_cambiado)
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
        caja.addSpacing(14)
        caja.addWidget(self._tarjeta_personaje_propio())
        caja.addStretch()
        self._personaje_cambiado()
        return pagina

    def _tarjeta_personaje_propio(self):
        tarjeta = _tarjeta()
        caja = QVBoxLayout(tarjeta)
        caja.setContentsMargins(16, 12, 16, 12)
        caja.setSpacing(6)
        caja.addWidget(QLabel("<b>Tu propio personaje</b>"))
        ayuda = QLabel("Una imagen PNG, GIF o JPG. Si tiene varias poses en fila, van en este orden: "
                       "normal, trabajando, feliz y error. El fondo liso se quita solo.")
        ayuda.setProperty("rol", "suave")
        ayuda.setWordWrap(True)
        caja.addWidget(ayuda)
        self.aviso_propio = QLabel()
        self.aviso_propio.setWordWrap(True)
        self.aviso_propio.hide()
        caja.addWidget(self.aviso_propio)
        botones = QHBoxLayout()
        botones.setSpacing(10)
        anadir = QPushButton(iconos.icono("mas"), "Añadir personaje…")
        anadir.clicked.connect(self._anadir_personaje)
        self.quitar_propio = QPushButton("Quitar")
        self.quitar_propio.setToolTip("Quita el personaje elegido arriba (solo los que añadiste tú)")
        self.quitar_propio.clicked.connect(self._quitar_personaje)
        botones.addWidget(anadir)
        botones.addWidget(self.quitar_propio)
        botones.addStretch()
        caja.addLayout(botones)
        return tarjeta

    def _llenar_combos(self, personaje, logo_elegido):
        for combo in (self.personaje, self.logo):
            combo.blockSignals(True)
            combo.clear()
        self.logo.addItem("Igual que el personaje", logo.SIGUE_AL_PERSONAJE)
        for p in personajes.catalogo().values():
            texto = f"{p.nombre} (tuyo)" if p.propio else p.nombre
            self.personaje.addItem(texto, p.id)
            self.logo.addItem(texto, p.id)
        self.personaje.setCurrentIndex(max(0, self.personaje.findData(personaje)))
        self.logo.setCurrentIndex(max(0, self.logo.findData(logo_elegido)))
        for combo in (self.personaje, self.logo):
            combo.blockSignals(False)

    def _avisar_propio(self, texto, tipo="exito"):
        self.aviso_propio.setText(texto)
        self.aviso_propio.setStyleSheet(f"color: {tema.hex_(tipo)};")
        self.aviso_propio.show()

    def _anadir_personaje(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Elige la imagen de tu personaje", "",
            "Imágenes (*.png *.gif *.webp *.jpg *.jpeg)")
        if not ruta:
            return
        nombre, ok = QInputDialog.getText(self, "Añadir personaje", "¿Cómo se llama?",
                                          text=personaje_nuevo.nombre_desde_archivo(ruta))
        if not ok or not nombre.strip():
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            ident, poses = personaje_nuevo.importar(ruta, nombre, ocupados=personajes.catalogo())
            personajes.recargar()
            logo.guardar_ico(ident)
        except personaje_nuevo.ErrorPersonaje as exc:
            QApplication.restoreOverrideCursor()
            self._avisar_propio(str(exc), "error")
            return
        except Exception as exc:  # una imagen rara no debe cerrar la ventana
            QApplication.restoreOverrideCursor()
            self._avisar_propio(f"No pude añadirlo: {exc}", "error")
            return
        QApplication.restoreOverrideCursor()
        self._llenar_combos(ident, self.logo.currentData())
        self._personaje_cambiado()
        detalle = ("la misma imagen para todos los estados" if poses == 1
                   else f"{poses} poses: " + ", ".join(("normal", "trabajando", "feliz", "error")[:poses]))
        self._avisar_propio(f"✓ Añadí «{nombre.strip()}» ({detalle}). Pulsa Guardar para usarlo.")

    def _quitar_personaje(self):
        p = personajes.catalogo().get(self.personaje.currentData())
        if p is None or not p.propio:
            return
        r = QMessageBox.question(self, "Quitar personaje", f"¿Quito a «{p.nombre}»? Se borra su imagen "
                                 "de Pandex (tu archivo original no se toca).")
        if r != QMessageBox.StandardButton.Yes:
            return
        try:
            personaje_nuevo.quitar(p.id)
        except (OSError, personaje_nuevo.ErrorPersonaje) as exc:
            self._avisar_propio(f"No pude quitarlo: {exc}", "error")
            return
        personajes.recargar()
        logo_actual = self.logo.currentData()
        self._llenar_combos(personajes.POR_DEFECTO,
                            logo.SIGUE_AL_PERSONAJE if logo_actual == p.id else logo_actual)
        self._personaje_cambiado()
        self._avisar_propio(f"Quité a «{p.nombre}».")

    def _personaje_cambiado(self, _indice=None):
        self.vista.poner(self.personaje.currentData())
        self._mostrar_logo()
        p = personajes.catalogo().get(self.personaje.currentData())
        self.quitar_propio.setEnabled(bool(p and p.propio))

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
        caja.addLayout(_titulo("Tareas", "Actívalas y elige si corren solas. Pandex tiene que "
                                         "estar abierto a esa hora."))
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
            if not getattr(tarea, "programable", True):
                # pide algo antes de empezar (p. ej. qué archivos): no tiene sentido a una hora fija
                cron = None
                nota = QLabel("Se usa desde el menú: cada vez eliges qué hacer.")
                nota.setProperty("rol", "suave")
                interno.addWidget(nota)
            else:
                cron = Horario(opciones.get("schedule") or tarea.schedule)
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
            if cron is not None:
                opciones["schedule"] = cron.valor()

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

