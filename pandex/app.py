"""La aplicación: une la mascota, el menú, la bandeja, el ejecutor y el reloj.

Flujo de una tarea::

    menú / reloj ─► Ejecutor.ejecutar(tarea) ─► [preparar(ctx) en la UI]
                 ─► hilo: tarea.run(ctx) ─► resultado ─► globo + ventana de informe
"""

import sys
import time
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QMessageBox, QSystemTrayIcon

from . import tareas as plugins
from .config import Config
from .ejecutor import Ejecutor
from .log import get_logger
from .programador import Programador
from .rutas import ICONO, RAIZ
from .tareas import TaskContext
from .ui import dibujo, iconos
from .ui.actualizacion import DialogoActualizacion
from .ui.configuracion import DialogoConfiguracion
from .ui.informe import DialogoInforme
from .ui.mascota import Mascota
from .ui.visor_registro import VisorRegistro

log = get_logger("pandex.app")

PROGRESO_CADA = 0.25  # s: el globo de avance se refresca como mucho 4 veces por segundo


class PandexApp(QObject):
    _disparo_programado = pyqtSignal(str)

    def __init__(self, qapp):
        super().__init__()
        self.qapp = qapp
        self.config = Config()
        self.tareas = plugins.descubrir()
        self._dialogos = []
        self._ultimo_progreso = 0.0
        self.servidor = None  # canal de instancia única (lo pone main.py)

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
        menu.setToolTipsVisible(True)
        # sin sombra nativa cuadrada detrás de las esquinas redondeadas
        menu.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        def accion(texto, icono, al_elegir, ayuda=None):
            a = QAction(iconos.icono(icono), texto, menu)
            a.triggered.connect(al_elegir)
            if ayuda:
                a.setToolTip(ayuda)
            menu.addAction(a)
            return a

        def seccion(texto):
            # Fusion no muestra el texto de addSection: un título deshabilitado sí se ve
            titulo = QAction(texto.upper(), menu)
            titulo.setEnabled(False)
            fuente = titulo.font()
            fuente.setPointSizeF(7.5)
            fuente.setBold(True)
            titulo.setFont(fuente)
            menu.addAction(titulo)

        seccion("Tareas")
        for tarea in self.tareas:
            accion(tarea.nombre, tarea.icono, lambda _c=False, t=tarea: self.ejecutor.ejecutar(t),
                   tarea.descripcion)
        if not self.tareas:
            vacio = QAction("No hay tareas en tasks/", menu)
            vacio.setEnabled(False)
            menu.addAction(vacio)

        configurables = [t for t in self.tareas if callable(getattr(t, "configurar", None))]
        for tarea in configurables:
            texto = getattr(tarea, "configurar_texto", None) or f"Configurar «{tarea.nombre}»…"
            accion(texto, "engranaje", lambda _c=False, t=tarea: self._configurar(t))

        menu.addSeparator()
        seccion("Pandex")
        accion("Configuración…", "engranaje", self._abrir_configuracion)
        accion("Ver registro", "lista", self._abrir_registro)
        accion("Recargar tareas", "recargar", self._recargar_tareas)
        accion("Buscar actualizaciones…", "descargar", self.buscar_actualizaciones)
        menu.addSeparator()
        if parent is None or self.mascota.isVisible():
            accion("Ocultar", "ocultar", self.mascota.hide)
        if parent is None or not self.mascota.isVisible():
            accion("Mostrar", "mostrar", self._mostrar_mascota)
        accion("Salir", "salir", self.salir)
        return menu

    def _abrir_menu(self, punto_global):
        menu = self._construir_menu(self.mascota)
        # se libera al cerrarse: antes quedaba un QMenu huérfano por cada clic derecho
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        menu.popup(punto_global)

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
        self._ultimo_progreso = 0.0
        self.mascota.set_estado("trabajando")
        self.mascota.decir(f"Empecé: {self._nombre_de(task_id)}", tipo="progreso")

    def _tarea_progreso(self, hechos, total):
        if total <= 0:
            return
        ahora = time.monotonic()
        # cientos de avances por segundo no deben repintar el globo cientos de veces
        if hechos < total and ahora - self._ultimo_progreso < PROGRESO_CADA:
            return
        self._ultimo_progreso = ahora
        self.mascota.progreso(f"Voy {hechos} de {total}…", hechos, total)

    def _tarea_terminada(self, task_id, resultado):
        ok = resultado["ok"]
        self.mascota.set_estado("feliz" if ok else "error", 4)
        resumen = resultado["resumen"] or ("Listo." if ok else "Algo falló.")
        self.mascota.decir(resumen, tipo="exito" if ok else "error")

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
        dlg = DialogoConfiguracion(self.config, self.tareas, al_buscar_actualizaciones=self.buscar_actualizaciones)
        if dlg.exec():
            self.mascota.recargar_apariencia()
            self.programador.montar(self.tareas)
            self.bandeja.setIcon(self._icono())
            self.bandeja.setToolTip(self.config.mascota.get("nombre", "Pandex"))
            self.mascota.decir("Configuración guardada.", tipo="exito")

    def _abrir_registro(self):
        VisorRegistro().exec()

    def tema_cambiado(self):
        """Windows pasó a claro/oscuro: el menú de la bandeja se rehace con los colores nuevos."""
        self._menu_bandeja = self._construir_menu(parent=None)
        self.bandeja.setContextMenu(self._menu_bandeja)
        self.mascota.globo.update()

    # ---------- actualizar ----------

    def buscar_actualizaciones(self):
        abierto = next((d for d in self._dialogos if isinstance(d, DialogoActualizacion)), None)
        if abierto:
            abierto.raise_()
            abierto.activateWindow()
            return
        dlg = DialogoActualizacion(self.reiniciar)
        self._dialogos.append(dlg)
        dlg.finished.connect(lambda _r, d=dlg: self._dialogos.remove(d))
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def reiniciar(self):
        """Cierra Pandex y lo vuelve a abrir (después de actualizar)."""
        if self.ejecutor.ocupado:
            self.mascota.decir("Termino lo que estoy haciendo y luego reinicias.", tipo="error")
            return
        if self.servidor is not None:
            self.servidor.close()  # libera el canal: si no, el nuevo creería que ya hay uno abierto
        exe = Path(sys.executable)
        if exe.with_name("pythonw.exe").exists():
            exe = exe.with_name("pythonw.exe")  # sin ventana de consola
        QProcess.startDetached(str(exe), [str(RAIZ / "main.py")], str(RAIZ))
        self._cerrar()

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
        self._cerrar()

    def _cerrar(self):
        log.info("cerrando Pandex")
        self.programador.detener()
        self.mascota.globo.ocultar_ya()
        self.bandeja.hide()
        self.qapp.quit()
