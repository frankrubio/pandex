"""Ejecuta solas las tareas que tienen horario (expresión cron)."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .log import get_logger

log = get_logger("pandex.programador")


class Programador:
    """Lee ``schedule`` de cada tarea activa (config.json manda sobre el código)."""

    def __init__(self, config, disparar):
        self.config = config
        self.disparar = disparar
        self._sched = BackgroundScheduler(daemon=True)

    def montar(self, tareas):
        self._sched.remove_all_jobs()
        for tarea in tareas:
            opciones = self.config.tarea(tarea.id)
            if not opciones.get("activa", True):
                continue
            cron = opciones.get("schedule", tarea.schedule)
            if not cron:
                continue
            try:
                self._sched.add_job(
                    self.disparar, CronTrigger.from_crontab(cron), args=[tarea.id],
                    id=tarea.id, replace_existing=True, misfire_grace_time=3600, coalesce=True,
                )
                log.info("tarea %s programada con cron '%s'", tarea.id, cron)
            except Exception as exc:
                log.error("cron inválido '%s' en %s: %s", cron, tarea.id, exc)

    def iniciar(self):
        if not self._sched.running:
            self._sched.start()

    def detener(self):
        if self._sched.running:
            self._sched.shutdown(wait=False)
