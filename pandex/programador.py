"""Ejecuta solas las tareas que tienen horario (expresión cron).

APScheduler (y su hilo) solo se cargan si alguna tarea tiene horario: sin horarios,
Pandex no carga la librería ni deja un hilo extra corriendo.
"""

from .log import get_logger

log = get_logger("pandex.programador")


class Programador:
    """Lee ``schedule`` de cada tarea activa (config.json manda sobre el código)."""

    def __init__(self, config, disparar):
        self.config = config
        self.disparar = disparar
        self._sched = None
        self._iniciado = False

    def _horarios(self, tareas):
        for tarea in tareas:
            opciones = self.config.tarea(tarea.id)
            if not opciones.get("activa", True):
                continue
            cron = opciones.get("schedule", tarea.schedule)
            if cron:
                yield tarea.id, cron

    def montar(self, tareas):
        horarios = list(self._horarios(tareas))
        if self._sched is not None:
            self._sched.remove_all_jobs()
        if not horarios:
            return
        if self._sched is None:
            from apscheduler.schedulers.background import BackgroundScheduler

            self._sched = BackgroundScheduler(daemon=True)
        from apscheduler.triggers.cron import CronTrigger

        for task_id, cron in horarios:
            try:
                self._sched.add_job(
                    self.disparar, CronTrigger.from_crontab(cron), args=[task_id],
                    id=task_id, replace_existing=True, misfire_grace_time=3600, coalesce=True,
                )
                log.info("tarea %s programada con cron '%s'", task_id, cron)
            except Exception as exc:
                log.error("cron inválido '%s' en %s: %s", cron, task_id, exc)
        if self._iniciado and not self._sched.running:
            self._sched.start()

    def iniciar(self):
        self._iniciado = True
        if self._sched is not None and not self._sched.running:
            self._sched.start()

    def detener(self):
        self._iniciado = False
        if self._sched is not None and self._sched.running:
            self._sched.shutdown(wait=False)
