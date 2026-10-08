"""La aplicación: une la mascota, el menú, la bandeja, el ejecutor y el reloj.

Flujo de una tarea::

    menú / reloj ─► Ejecutor.ejecutar(tarea) ─► [preparar(ctx) en la UI]
                 ─► hilo: tarea.run(ctx) ─► resultado ─► globo + ventana de informe
"""

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QMessageBox, QSystemTrayIcon

from . import tareas as plugins
from .config import Config
from .ejecutor import Ejecutor
from .log import get_logger
from .programador import Programador
from .rutas import ICONO
from .tareas import TaskContext
from .ui import dibujo
from .ui.configuracion import DialogoConfiguracion
from .ui.informe import DialogoInforme
from .ui.mascota import Mascota
from .ui.visor_registro import VisorRegistro

log = get_logger("pandex.app")


class PandexApp(QObject):
    _disparo_programado = pyqtSignal(str)

    def __init__(self, qapp):
        super().__init__()
        self.qapp = qapp
        self.config = Config()
        self.tareas = plugins.descubrir()
        self._dialogos = []

        self.mascota = Mascota(self.config)
        self.mascota.menu_pedido.connect(self._abrir_menu)

        self.ejecutor = Ejecutor(self.config)
        self.ejecutor.iniciada.connect(self._tarea_iniciada)
        self.ejecutor.decir.connect(self.mascota.decir)
        self.ejecutor.progreso.connect(self._tarea_progreso)
        self.ejecutor.terminada.connect(self._tarea_terminada)

        # el reloj corre en otro hilo: la señal trae el disparo de vuelta a la UI
        self.programador = Programador(self.config, self._disparo_programado.emit)
        self._disparo_programado.connect(self._ejecutar_por_id, Qt.ConnectionType.QueuedConnection)
        self.programador.montar(self.tareas)
        self.programador.iniciar()

        self._crear_bandeja()

    # ---------- arranque ----------

    def iniciar(self):
        self.mascota.show()
        self.mascota.raise_()
        nombre = self.config.mascota.get("nombre", "Pandex")
        self.mascota.decir(f"¡Hola! Soy {nombre}. Tengo {len(self.tareas)} tarea(s) listas.")
        log.info("Pandex iniciado con %d tarea(s)", len(self.tareas))
        QTimer.singleShot(1500, self._primera_vez)

    def _primera_vez(self):
        """Abre el asistente de las tareas que aún no se configuraron (una sola vez)."""
        for tarea in self.tareas:
            params = self.config.tarea(tarea.id)
            necesita = getattr(tarea, "necesita_configurar", None)
            if not callable(necesita) or params.get("asistente_visto") or not params.get("activa", True):
                continue
            try:
                if not necesita(params):
                    continue
            except Exception:
                log.exception("necesita_configurar de %s falló", tarea.id)
                continue
            params["asistente_visto"] = True
            self.config.guardar()
            self.mascota.decir(f"Antes de empezar, configuremos «{tarea.nombre}».")
            self._configurar(tarea)
            return  # un asistente por arranque es suficiente

    # ---------- bandeja ----------

    def _icono(self, lado=64):
        if ICONO.exists():
            return QIcon(str(ICONO))
        pix = QPixmap(lado, lado)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        dibujo.icono_bandeja(painter, lado)
        painter.end()
        return QIcon(pix)

    def _crear_bandeja(self):
        self.bandeja = QSystemTrayIcon(self._icono(), self.qapp)
        self.bandeja.setToolTip(self.config.mascota.get("nombre", "Pandex"))
        self.bandeja.activated.connect(self._click_bandeja)
        # hay que guardar la referencia: setContextMenu no toma posesión del menú
        self._menu_bandeja = self._construir_menu(parent=None)
        self.bandeja.setContextMenu(self._menu_bandeja)
        self.bandeja.show()

    def _click_bandeja(self, razon):
        if razon in (QSystemTrayIcon.ActivationReason.Trigger,
                     QSystemTrayIcon.ActivationReason.DoubleClick):
            self._mostrar_mascota()

    def _mostrar_mascota(self):
        self.mascota.show()
        self.mascota.raise_()
        self.mascota.activateWindow()

    def asomarse(self):
        """Doble clic en el acceso directo con Pandex ya abierto: aparece y saluda."""
        self._mostrar_mascota()
        self.mascota.set_estado("feliz", 1.8)
        self.mascota.decir("¡Aquí estoy! Ya estaba abierto.")

    # ---------- menú ----------

    def _construir_menu(self, parent):
        menu = QMenu(parent)
        for tarea in self.tareas:
            accion = QAction(tarea.nombre, menu)
            accion.setToolTip(tarea.descripcion)
            accion.triggered.connect(lambda _c=False, t=tarea: self.ejecutor.ejecutar(t))
            menu.addAction(accion)
        if not self.tareas:
            vacio = QAction("No hay tareas en tasks/", menu)
            vacio.setEnabled(False)
            menu.addAction(vacio)

        configurables = [t for t in self.tareas if callable(getattr(t, "configurar", None))]
        if configurables:
            menu.addSeparator()
            for tarea in configurables:
                texto = getattr(tarea, "configurar_texto", None) or f"Configurar «{tarea.nombre}»…"
                menu.addAction(QAction(texto, menu, triggered=lambda _c=False, t=tarea: self._configurar(t)))

        menu.addSeparator()
        menu.addAction(QAction("Recargar tareas", menu, triggered=self._recargar_tareas))
        menu.addAction(QAction("Configuración", menu, triggered=self._abrir_configuracion))
        menu.addAction(QAction("Ver registro", menu, triggered=self._abrir_registro))
        menu.addSeparator()
        menu.addAction(QAction("Ocultar", menu, triggered=self.mascota.hide))
        menu.addAction(QAction("Mostrar", menu, triggered=self._mostrar_mascota))
        menu.addSeparator()
        menu.addAction(QAction("Salir", menu, triggered=self.salir))
        return menu

    def _abrir_menu(self, punto_global):
        self._construir_menu(self.mascota).exec(punto_global)

    # ---------- tareas ----------

    def _ejecutar_por_id(self, task_id):
        tarea = next((t for t in self.tareas if t.id == task_id), None)
        if tarea is None:
            log.warning("el reloj pidió '%s' pero esa tarea ya no existe", task_id)
            return
        log.info("disparo programado de %s", task_id)
        self.ejecutor.ejecutar(tarea)

    def _configurar(self, tarea):
        if self.ejecutor.ocupado:
            self.mascota.decir("Espera a que termine lo que estoy haciendo.")
            return
        ctx = TaskContext(tarea.id, self.config, self.mascota.decir)
        try:
            entrada = tarea.configurar(ctx)
        except Exception:
            log.exception("configurar de %s falló", tarea.id)
            self.mascota.decir("No pude abrir la configuración. Mira el registro.")
            return
        self.programador.montar(self.tareas)  # el asistente puede haber puesto un horario
        if entrada is not None:
            self.ejecutor.ejecutar(tarea, entrada)

    def _nombre_de(self, task_id):
        return next((t.nombre for t in self.tareas if t.id == task_id), task_id)

    def _tarea_iniciada(self, task_id):
        self.mascota.set_estado("trabajando")
        self.mascota.decir(f"Empecé: {self._nombre_de(task_id)}")

    def _tarea_progreso(self, hechos, total):
        if total > 0:
            self.mascota.decir(f"Voy {hechos}/{total}…")

    def _tarea_terminada(self, task_id, resultado):
        ok = resultado["ok"]
        self.mascota.set_estado("feliz" if ok else "error", 4)
        resumen = resultado["resumen"] or ("Listo." if ok else "Algo falló.")
        self.mascota.decir(resumen if ok else f"⚠ {resumen}")

        if resultado.get("informe"):
            dlg = DialogoInforme(self._nombre_de(task_id), resultado["informe"], resultado.get("carpeta"))
            self._dialogos.append(dlg)
            dlg.finished.connect(lambda _r, d=dlg: self._dialogos.remove(d))
            dlg.show()
            dlg.raise_()
            dlg.activateWindow()

    def _recargar_tareas(self):
        self.tareas = plugins.descubrir()
        self.programador.montar(self.tareas)
        self._menu_bandeja = self._construir_menu(parent=None)
        self.bandeja.setContextMenu(self._menu_bandeja)
        self.mascota.decir(f"Recargué: {len(self.tareas)} tarea(s).")

    # ---------- diálogos ----------

    def _abrir_configuracion(self):
        dlg = DialogoConfiguracion(self.config, self.tareas)
        if dlg.exec():
            self.mascota.recargar_apariencia()
            self.programador.montar(self.tareas)
            self.bandeja.setIcon(self._icono())
            self.bandeja.setToolTip(self.config.mascota.get("nombre", "Pandex"))
            self.mascota.decir("Configuración guardada.")

    def _abrir_registro(self):
        VisorRegistro().exec()

    # ---------- salida ----------

    def salir(self):
        if self.ejecutor.ocupado:
            respuesta = QMessageBox.question(
                None, "Salir", "Hay una tarea corriendo. ¿Salir igual?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return
        log.info("cerrando Pandex")
        self.programador.detener()
        self.mascota.globo.ocultar_ya()
        self.bandeja.hide()
        self.qapp.quit()
