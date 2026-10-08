"""``config.json``: tus preferencias, con valores por defecto de respaldo.

El archivo es personal (rutas de tu PC, tus cursos) y no se sube a GitHub. Si no
existe, se crea con los valores de abajo; cada tarea guarda lo suyo en
``tareas.<id_de_la_tarea>``.
"""

import copy
import json

from .rutas import CONFIG_FILE

VERSION_CONFIG = 2

# el sprite pixel art: personaje alternativo («personaje": "pixel")
SPRITE_PIXEL = {
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
}

DEFAULTS = {
    "version_config": VERSION_CONFIG,
    "mascota": {
        "nombre": "Pandex",
        # "rusty" (panda rojo pixel art), "vectorial" (panda robot) o "pixel" (sprite sheet)
        "personaje": "rusty",
        "tamano": 120,
        "opacidad": 1.0,
        "spritesheet": SPRITE_PIXEL,
        "globo_activo": True,
        "globo_segundos": 5,
        "posicion": None,
        "siempre_encima": True,
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


# opciones de la mascota animada de la versión 1, que ya no existen
_OBSOLETAS = ("animacion", "ojos_siguen_cursor")


def migrar(datos):
    """Pone al día un ``config.json`` de una versión anterior. Devuelve True si cambió algo.

    v1 → v2: el ``spritesheet`` se guardaba completo en tu config.json, así que un
    cambio de personaje nunca te llegaba. Ahora, si es el de fábrica, se quita (manda
    el valor por defecto) y pasas a Rusty; si pusiste uno tuyo, se respeta.
    """
    version = int(datos.get("version_config", 1) or 1)
    if version >= VERSION_CONFIG:
        return False
    mascota = datos.setdefault("mascota", {})
    sprite = mascota.get("spritesheet")
    if sprite and sprite != SPRITE_PIXEL:
        mascota.setdefault("personaje", "pixel")  # un personaje propio: se queda
    else:
        mascota.pop("spritesheet", None)
        mascota["personaje"] = "rusty"
    for clave in _OBSOLETAS:
        mascota.pop(clave, None)
    datos["version_config"] = VERSION_CONFIG
    return True


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
                guardado = json.load(fh)
            migrado = migrar(guardado)
            self.datos = _mezclar(DEFAULTS, guardado)
            if migrado:
                self.guardar()
        else:
            self.guardar()

    def guardar(self):
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.ruta.with_suffix(".json.tmp")
        datos = self.datos
        if datos.get("mascota", {}).get("spritesheet") == SPRITE_PIXEL:
            # el de fábrica no se guarda: así una actualización del personaje sí te llega
            datos = {**datos, "mascota": {k: v for k, v in datos["mascota"].items() if k != "spritesheet"}}
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(datos, fh, indent=2, ensure_ascii=False)
        tmp.replace(self.ruta)

    @property
    def mascota(self):
        return self.datos["mascota"]

    def tarea(self, task_id):
        """Las opciones de una tarea (se crean vacías si aún no existen)."""
        return self.datos.setdefault("tareas", {}).setdefault(task_id, {})
