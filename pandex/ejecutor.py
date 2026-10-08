"""Corre una tarea a la vez en un hilo aparte, para que la mascota nunca se congele."""

import traceback

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from .log import get_logger
from .tareas import TaskContext

log = get_logger("pandex.ejecutor")


class _Hilo(QThread):
    decir = pyqtSignal(str)
    progreso = pyqtSignal(int, int)
    terminada = pyqtSignal(str, dict)

    def __init__(self, tarea, config, entrada=None):
        super().__init__()
        self.tarea = tarea
        self.config = config
        self.entrada = entrada

    def run(self):
        ctx = TaskContext(self.tarea.id, self.config, self.decir.emit, self.progreso.emit,
                          entrada=self.entrada)
        try:
            resultado = self.tarea.run(ctx) or {}
            if not isinstance(resultado, dict):
                resultado = {"ok": True, "resumen": str(resultado)}
        except Exception as exc:
            log.error("tarea %s falló:\n%s", self.tarea.id, traceback.format_exc())
            resultado = {"ok": False, "resumen": f"Error: {exc}",
                         "detalle": traceback.format_exc().splitlines()}
        resultado.setdefault("ok", True)
        resultado.setdefault("resumen", "")
        resultado.setdefault("detalle", [])
        self.terminada.emit(self.tarea.id, resultado)


class Ejecutor(QObject):
    """Recibe pedidos de ejecución (menú o reloj) y avisa por señales."""

    iniciada = pyqtSignal(str)
    decir = pyqtSignal(str)
    progreso = pyqtSignal(int, int)
    terminada = pyqtSignal(str, dict)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._hilo = None
        self._actual = None

    @property
    def ocupado(self):
        return self._hilo is not None and self._hilo.isRunning()

    def ejecutar(self, tarea, entrada=None):
        """Lanza la tarea. Si no se da ``entrada``, se le pide a ``preparar(ctx)``."""
        if self.ocupado:
            self.decir.emit(f"Espera, sigo con «{self._actual}».")
            return False

        preparar = getattr(tarea, "preparar", None)
        if entrada is None and callable(preparar):
            ctx = TaskContext(tarea.id, self.config, self.decir.emit)
            try:
                entrada = preparar(ctx)
            except Exception:
                log.error("preparar de %s falló:\n%s", tarea.id, traceback.format_exc())
                self.decir.emit(f"No pude abrir «{tarea.nombre}». Mira el registro.")
                return False
            if entrada is None:
                log.info("tarea %s cancelada antes de empezar", tarea.id)
                return False

        log.info("ejecutando tarea %s", tarea.id)
        self._actual = tarea.nombre
        self._hilo = _Hilo(tarea, self.config, entrada)
        self._hilo.decir.connect(self.decir)
        self._hilo.progreso.connect(self.progreso)
        self._hilo.terminada.connect(self._al_terminar)
        self._hilo.finished.connect(self._limpiar)
        self.iniciada.emit(tarea.id)
        self._hilo.start()
        return True

    def _al_terminar(self, task_id, resultado):
        nivel = "info" if resultado["ok"] else "error"
        getattr(log, nivel)("tarea %s -> %s", task_id, resultado["resumen"])
        for linea in resultado["detalle"]:
            log.info("  %s | %s", task_id, linea)
        self.terminada.emit(task_id, resultado)

    def _limpiar(self):
        self._hilo = None
        self._actual = None

    def esperar(self, ms=4000):
        if self.ocupado:
            self._hilo.wait(ms)
