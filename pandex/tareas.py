"""El contrato de los plug-ins: cómo se descubren las tareas y qué reciben.

Una tarea es un archivo ``tasks/<algo>.py`` con una clase ``Task``::

    class Task:
        id = "mi_tarea"                 # único; también es su clave en config.json
        nombre = "Mi tarea"             # lo que se ve en el menú
        descripcion = "Qué hace"        # tooltip y Configuración
        schedule = None                 # cron opcional, p. ej. "0 19 * * 1-5"
        icono = "tarea"                 # opcional: el ícono del menú (ver pandex/ui/iconos.py)
        programable = True              # opcional: False si no tiene sentido darle un horario

        def run(self, ctx):             # corre en un hilo aparte: nada de ventanas aquí
            return {"ok": True, "resumen": "Listo."}

Ganchos opcionales, todos corren en el hilo de la interfaz (pueden abrir diálogos):

``preparar(ctx)``
    Antes de cada ejecución manual. Devuelve lo que ``run`` recibirá en
    ``ctx.entrada``, o ``None`` para cancelar.
``necesita_configurar(params) -> bool``
    Si devuelve True, Pandex abre ``configurar`` al arrancar (solo la primera vez).
``configurar(ctx)``
    Un asistente de configuración. Devuelve una ``entrada`` para ejecutar la
    tarea enseguida, o ``None``. Aparece en el menú como ``configurar_texto``.

``run`` puede devolver además ``"detalle"`` (líneas para el log), ``"informe"``
(texto que se muestra en una ventana al terminar) y ``"carpeta"`` (botón
«Abrir carpeta» de esa ventana).
"""

import importlib.util
import sys
import traceback

from .log import get_logger
from .rutas import TASKS_DIR

log = get_logger("pandex.tareas")


def descubrir(carpeta=TASKS_DIR):
    """Carga cada ``tasks/*.py`` y devuelve una instancia de su ``Task``.

    Un archivo roto se salta con un aviso en el log: nunca tumba la app. Los que
    empiezan con ``_`` se ignoran (sirven para desactivar una tarea sin borrarla).
    """
    carpeta.mkdir(parents=True, exist_ok=True)
    encontradas, vistos = [], set()

    for archivo in sorted(carpeta.glob("*.py")):
        if archivo.name.startswith("_"):
            continue
        try:
            clase = getattr(_importar(archivo), "Task", None)
            if clase is None:
                log.warning("%s no define una clase Task, se salta", archivo.name)
                continue
            tarea = clase()
            if not getattr(tarea, "id", None) or not callable(getattr(tarea, "run", None)):
                log.warning("%s: la clase Task necesita 'id' y 'run(ctx)'", archivo.name)
                continue
            if tarea.id in vistos:
                log.warning("id duplicado '%s' en %s, se salta", tarea.id, archivo.name)
                continue
            tarea.nombre = getattr(tarea, "nombre", None) or tarea.id
            tarea.descripcion = getattr(tarea, "descripcion", "")
            tarea.schedule = getattr(tarea, "schedule", None)
            tarea.icono = getattr(tarea, "icono", None) or "tarea"
            vistos.add(tarea.id)
            encontradas.append(tarea)
            log.info("tarea cargada: %s (%s)", tarea.id, archivo.name)
        except Exception:
            log.error("no pude cargar %s:\n%s", archivo.name, traceback.format_exc())

    return encontradas


def _importar(archivo):
    nombre = f"pandex_tasks_{archivo.stem}"
    spec = importlib.util.spec_from_file_location(nombre, archivo)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = modulo
    spec.loader.exec_module(modulo)
    return modulo


class TaskContext:
    """Lo que recibe una tarea en ``run(ctx)`` y en sus ganchos.

    ===================  ===========================================================
    ``ctx.log(msg)``     escribe en ``logs/pandex.log`` (nivel opcional: "warning"…)
    ``ctx.decir(txt)``   muestra el globo de diálogo
    ``ctx.progreso(n,t)``avisa el avance (se ve en el globo)
    ``ctx.params``       dict propio de la tarea (``config.json → tareas → id``)
    ``ctx.config``       dict completo de config.json
    ``ctx.guardar()``    persiste en config.json lo que cambiaste en ``ctx.params``
    ``ctx.entrada``      lo que devolvió ``preparar``/``configurar``; si no, None
    ===================  ===========================================================
    """

    def __init__(self, task_id, config, decir_cb=None, progreso_cb=None, entrada=None):
        self.task_id = task_id
        self.config = config.datos
        self.params = config.tarea(task_id)
        self.entrada = entrada
        self._config = config
        self._decir_cb = decir_cb or (lambda _texto: None)
        self._progreso_cb = progreso_cb or (lambda _n, _t: None)
        self._log = get_logger(f"pandex.tarea.{task_id}")

    def log(self, msg, nivel="info"):
        getattr(self._log, nivel, self._log.info)(msg)

    def decir(self, texto):
        self.log(f"globo: {texto}")
        self._decir_cb(texto)

    def progreso(self, n, total):
        self._progreso_cb(int(n), int(total))

    def guardar(self):
        self._config.guardar()
