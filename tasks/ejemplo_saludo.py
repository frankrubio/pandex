"""Saludar: te saluda y te dice la hora. También es el ejemplo para crear tareas.

Con solo dejar un .py en ``tasks/``, Pandex lo encuentra al arrancar (o con
«Recargar tareas» en el menú) y lo agrega al menú y al reloj. Copia este archivo
como punto de partida; la guía completa está en ``docs/crear-tareas.md``.

Solo se ve con «Mostrar opciones para programadores» (Configuración → Comportamiento).
Al copiarlo, borra ``solo_programador`` para que tu tarea se vea siempre.
"""

from datetime import datetime

from pandex import horas


class Task:
    id = "ejemplo_saludo"
    nombre = "Saludar"
    icono = "hola"
    descripcion = "Te saluda y te dice la hora. También es el ejemplo para crear tareas."
    schedule = None  # None = solo manual. Ej: "0 19 * * 1-5" = 7:00 p. m. de lunes a viernes
    solo_programador = True  # es un ejemplo: no lo ve quien solo estudia

    def run(self, ctx):
        ahora = datetime.now()
        return {"ok": True, "resumen": f"¡{horas.saludo(ahora)}! Son las {horas.de(ahora)} "
                                      f"del {horas.fecha_larga(ahora)}."}
