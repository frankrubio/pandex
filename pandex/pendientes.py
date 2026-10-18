"""¿Qué tarea programada se perdió? Para ponerse al día al encender la PC.

Si una tarea tenía que correr a las 7:00 p. m. y la PC estaba apagada (o suspendida, o
Pandex cerrado), corre apenas se pueda: al abrir Pandex o cuando el sistema lo despierta
(``pandex/despertador.py``). Solo una vez, aunque se hayan perdido varias.

Sin Qt: ``main.py --pendientes`` lo usa para decidir, en milisegundos, si vale la pena
abrir Pandex o no.
"""

import json
from datetime import datetime, timedelta

from .log import get_logger
from .rutas import CONFIG_FILE, DATOS

log = get_logger("pandex.pendientes")

ARCHIVO = DATOS / "ultimas_ejecuciones.json"


_DIAS = ("sun", "mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _dia_semana(campo):
    """Cron cuenta 0 = domingo; APScheduler, 0 = lunes. Con nombres no hay confusión:
    ``"1-5"`` → ``"mon-fri"`` (de lunes a viernes, no de martes a sábado)."""
    import re

    def nombre(m):
        return _DIAS[int(m.group(0))] if int(m.group(0)) <= 7 else m.group(0)

    if "/" in campo:
        return campo  # «*/2»: pasos, se deja igual
    return re.sub(r"\d+", nombre, campo)


def disparador(cron):
    """Un ``CronTrigger`` de APScheduler que entiende el cron como lo escribe todo el mundo."""
    from apscheduler.triggers.cron import CronTrigger

    partes = cron.split()
    if len(partes) != 5:
        raise ValueError(f"se esperaban 5 campos: {cron!r}")
    minuto, hora, dia, mes, semana = partes
    return CronTrigger(minute=minuto, hour=hora, day=dia, month=mes, day_of_week=_dia_semana(semana))


def _leer():
    try:
        datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def _escribir(datos):
    ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
    temporal = ARCHIVO.with_suffix(".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    temporal.replace(ARCHIVO)


def _ahora():
    return datetime.now().astimezone()


def horarios(config_datos, por_defecto=None):
    """``{task_id: cron}`` de las tareas activas con horario. ``por_defecto`` es el
    ``schedule`` del código de cada tarea (``config.json`` manda)."""
    por_defecto = por_defecto or {}
    tareas = (config_datos or {}).get("tareas", {}) or {}
    salida = {}
    for task_id in set(tareas) | set(por_defecto):
        opciones = tareas.get(task_id, {}) or {}
        if not opciones.get("activa", True):
            continue
        cron = opciones.get("schedule", por_defecto.get(task_id))
        if cron:
            salida[task_id] = cron
    return salida


def leer_config():
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def marcar(task_id, cron=None, cuando=None):
    """Anota que la tarea ya corrió (al terminar, salga bien o mal: así no se repite en bucle)."""
    datos = _leer()
    datos[task_id] = {"ultima": (cuando or _ahora()).isoformat(timespec="seconds"), "cron": cron}
    _escribir(datos)


def vencidas(config_datos=None, ahora=None, por_defecto=None):
    """Las tareas cuyo último horario ya pasó y no corrieron desde entonces, en orden.

    La primera vez que ve un horario (o si lo cambiaste) solo anota «desde ahora»: nunca
    corre algo por un horario que todavía no existía.
    """
    config_datos = leer_config() if config_datos is None else config_datos
    ahora = ahora or _ahora()
    registro = _leer()
    cambios, salida = False, []
    for task_id, cron in sorted(horarios(config_datos, por_defecto).items()):
        previo = registro.get(task_id) or {}
        if previo.get("cron") != cron or "ultima" not in previo:
            registro[task_id] = {"ultima": ahora.isoformat(timespec="seconds"), "cron": cron}
            cambios = True
            continue
        try:
            ultima = datetime.fromisoformat(previo["ultima"])
            disparo = disparador(cron).get_next_fire_time(None, ultima + timedelta(seconds=1))
        except (ValueError, TypeError) as exc:
            log.warning("horario inválido en %s (%s): %s", task_id, cron, exc)
            continue
        if disparo is not None and disparo <= ahora:
            salida.append(task_id)
    if cambios:
        _escribir(registro)
    return salida
