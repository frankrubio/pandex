"""``config.json``: tus preferencias, con valores por defecto de respaldo.

El archivo es personal (rutas de tu PC, tus cursos) y no se sube a GitHub. Si no
existe, se crea con los valores de abajo; cada tarea guarda lo suyo en
``tareas.<id_de_la_tarea>``.
"""

import copy
import json

from .rutas import CONFIG_FILE

VERSION_CONFIG = 4

# el panda robot pixel art que las versiones 1.x y 2.x guardaban en config.json
# («spritesheet»); hoy es el personaje «panda_clasico». Sirve para reconocerlo al migrar.
PANDA_VIEJO = "assets/panda_robot/spritesheet.png"

DEFAULTS = {
    "version_config": VERSION_CONFIG,
    "mascota": {
        "nombre": "Pandex",
        # "rusty", "bmo", "robot", "panda_clasico" o uno que añadiste (ver ui/personajes.py)
        "personaje": "rusty",
        # ícono de la app: "personaje" (la cara del personaje elegido) o el id de otro
        "logo": "personaje",
        # si el personaje trae movimientos, se mueve mientras trabaja o reacciona
        "animar": True,
        "tamano": 120,
        "opacidad": 1.0,
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
    # una consulta pequeña a GitHub al día; si hay versión nueva, Rusty avisa
    "buscar_actualizaciones": True,
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


def _es_de_fabrica(sprite):
    """True si el sprite es el panda robot que trae Pandex (o no hay ninguno).

    Se mira solo el archivo: un config.json de una versión anterior puede tener el
    mismo dibujo con otros tamaños o animaciones, y sigue siendo el de fábrica.
    """
    if not sprite:
        return True
    archivo = str(sprite.get("archivo") or "").replace("\\", "/").lower()
    while archivo.startswith("./"):
        archivo = archivo[2:]
    return archivo in ("", PANDA_VIEJO)


def migrar(datos):
    """Pone al día un ``config.json`` de una versión anterior. Devuelve True si cambió algo.

    El ``spritesheet`` se guardaba completo en tu config.json, así que un cambio de
    personaje nunca te llegaba. Si es el de fábrica, se quita (manda el valor por
    defecto) y pasas a Rusty; si pusiste uno tuyo (otro archivo), se respeta.

    v2 → v3: la v2 comparaba el bloque entero y dejaba en el panda viejo a quien
    tenía el de fábrica con otros valores; aquí se corrige.

    v3 → v4: los personajes pasan a ``assets/personajes/``. El panda robot dibujado
    («vectorial») ya no existe: pasa a Rusty. Quien eligió el panda pixel art en la 2.x
    («pixel» con el sprite de fábrica) pasa a «panda_clasico», que es el mismo dibujo.
    Un sprite sheet propio («pixel» con otro archivo) ya no se lee desde config.json:
    pasa a Rusty y el bloque se conserva para que puedas añadirlo como personaje
    (Configuración → Apariencia → Añadir personaje).
    """
    version = int(datos.get("version_config", 1) or 1)
    if version >= VERSION_CONFIG:
        return False
    mascota = datos.setdefault("mascota", {})
    sprite = mascota.get("spritesheet")
    personaje = mascota.get("personaje")
    if _es_de_fabrica(sprite):
        if version < 2 or (version < 3 and personaje in (None, "pixel")):
            mascota["personaje"] = "rusty"
        elif personaje == "pixel":
            mascota["personaje"] = "panda_clasico"
        mascota.pop("spritesheet", None)
    if mascota.get("personaje") in ("vectorial", "pixel", None):
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
        if _es_de_fabrica(datos.get("mascota", {}).get("spritesheet")):
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
