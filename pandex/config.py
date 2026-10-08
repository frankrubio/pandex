"""``config.json``: tus preferencias, con valores por defecto de respaldo.

El archivo es personal (rutas de tu PC, tus cursos) y no se sube a GitHub. Si no
existe, se crea con los valores de abajo; cada tarea guarda lo suyo en
``tareas.<id_de_la_tarea>``.
"""

import copy
import json

from .rutas import CONFIG_FILE

DEFAULTS = {
    "mascota": {
        "nombre": "Pandex",
        "tamano": 120,
        "opacidad": 1.0,
        "spritesheet": {
            "archivo": "assets/panda_robot/spritesheet.png",
            "frame_ancho": 346,
            "frame_alto": 355,
            "recortar_margen": True,
            "suavizado": True,
            "animaciones": {
                "idle": {"frames": [[0, 0]], "fps": 1},
                "feliz": {"frames": [[0, 0]], "fps": 1},
                "trabajando": {"frames": [[0, 0]], "fps": 1},
                "error": {"frames": [[0, 0]], "fps": 1},
            },
        },
        "globo_activo": True,
        "globo_segundos": 5,
        "posicion": None,
        "siempre_encima": True,
        "animacion": True,
        "ojos_siguen_cursor": True,
        "frases_click": [
            "¿Qué tal?",
            "Clic derecho para el menú.",
            "import antigravity",
            "Listo para trabajar.",
        ],
    },
    "arrancar_con_windows": False,
    "tareas": {},
}


def _mezclar(base, extra):
    salida = copy.deepcopy(base)
    for clave, valor in extra.items():
        if isinstance(valor, dict) and isinstance(salida.get(clave), dict):
            salida[clave] = _mezclar(salida[clave], valor)
        else:
            salida[clave] = valor
    return salida


class Config:
    """config.json cargado en memoria. ``guardar()`` lo escribe de forma atómica."""

    def __init__(self, ruta=CONFIG_FILE):
        self.ruta = ruta
        self.datos = copy.deepcopy(DEFAULTS)
        self.nueva = not self.ruta.exists()
        self.cargar()

    def cargar(self):
        if self.ruta.exists():
            with open(self.ruta, encoding="utf-8") as fh:
                self.datos = _mezclar(DEFAULTS, json.load(fh))
        else:
            self.guardar()

    def guardar(self):
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.ruta.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.datos, fh, indent=2, ensure_ascii=False)
        tmp.replace(self.ruta)

    @property
    def mascota(self):
        return self.datos["mascota"]

    def tarea(self, task_id):
        """Las opciones de una tarea (se crean vacías si aún no existen)."""
        return self.datos.setdefault("tareas", {}).setdefault(task_id, {})
