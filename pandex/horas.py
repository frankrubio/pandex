"""Horas y fechas como se dicen en Perú: en formato de 12 horas («7:05 p. m.»).

Solo para lo que ve el usuario. El registro y los nombres de archivo internos
siguen en 24 horas, que se ordenan bien.
"""

from datetime import datetime

DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre")


def hora(h, m=0):
    """``hora(19, 5)`` → ``"7:05 p. m."``; ``hora(0, 30)`` → ``"12:30 a. m."``."""
    h, m = int(h), int(m)
    return f"{(h % 12) or 12}:{m:02d} {'a. m.' if h < 12 else 'p. m.'}"


def de(momento):
    """La hora de un ``datetime`` (o ``time``)."""
    return hora(momento.hour, momento.minute)


def fecha_hora(momento):
    """``09/10 7:05 p. m.``"""
    return f"{momento:%d/%m} {de(momento)}"


def fecha_larga(momento):
    """``jueves 9 de octubre``"""
    return f"{DIAS[momento.weekday()]} {momento.day} de {MESES[momento.month - 1]}"


def saludo(momento=None):
    """Buenos días / Buenas tardes / Buenas noches, según la hora."""
    h = (momento or datetime.now()).hour
    if 5 <= h < 12:
        return "Buenos días"
    return "Buenas tardes" if 12 <= h < 19 else "Buenas noches"
