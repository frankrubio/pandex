"""Tarea de ejemplo: copia este archivo para crear una función nueva.

Con solo dejar un .py en ``tasks/``, Pandex lo encuentra al arrancar (o con
«Recargar tareas» en el menú) y lo agrega al menú y al reloj. La guía completa
está en ``docs/crear-tareas.md``.
"""

import time
from datetime import datetime


class Task:
    id = "ejemplo_saludo"
    nombre = "Saludar (ejemplo)"
    icono = "hola"
    descripcion = "Tarea de prueba: cuenta hasta 3 y saluda"
    schedule = None  # None = solo manual. Ej: "0 19 * * 1-5" = 19:00 de lunes a viernes

    def run(self, ctx):
        ctx.log("arrancó la tarea de ejemplo")
        total = 3
        for i in range(1, total + 1):
            ctx.progreso(i, total)  # el globo dice «Voy 1/3…»
            time.sleep(0.6)
        return {"ok": True, "resumen": f"Todo bien por aquí, son las {datetime.now():%H:%M}."}
