"""``config.json``: tus preferencias, con valores por defecto de respaldo.

El archivo es personal (rutas de tu PC, tus cursos) y no se sube a GitHub. Si no
existe, se crea con los valores de abajo; cada tarea guarda lo suyo en
``tareas.<id_de_la_tarea>``.
"""

import copy
import json
import os
from datetime import datetime

from .log import get_logger
from .rutas import CONFIG_FILE, DATOS

log = get_logger("pandex.config")

VERSION_CONFIG = 4

# la última configuración que se leyó bien: de ahí se recupera si config.json se daña (ROB-02)
COPIA_BUENA = DATOS / "config-ultima-buena.json"
DANADOS_QUE_QUEDAN = 3

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
    # muestra en el menú el ejemplo «Saludar» y «Recargar tareas» (spec 005, IU-19)
    "modo_programador": False,
    "tareas": {},
}


def _mezclar(base, extra):
    """Lo guardado manda sobre los valores de fábrica. Un valor que debería ser un objeto y no
    lo es (un archivo tocado a mano o dañado) se ignora: queda el de fábrica."""
    salida = copy.deepcopy(base)
    for clave, valor in extra.items():
        if isinstance(salida.get(clave), dict):
            if isinstance(valor, dict):
                salida[clave] = _mezclar(salida[clave], valor)
        else:
            salida[clave] = valor
    return salida


def _marca():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _leer(ruta):
    """El contenido de un ``config.json``, o None si no es un objeto JSON."""
    try:
        with open(ruta, encoding="utf-8") as fh:
            datos = json.load(fh)
    except (ValueError, OSError):
        return None
    return datos if isinstance(datos, dict) else None


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
    """config.json cargado en memoria. ``guardar()`` lo escribe de forma atómica.

    Si el archivo está dañado, Pandex abre igual (ROB-02): ``recuperada`` dice de dónde salió la
    configuración (``"copia"``: la última buena; ``"fabrica"``: no había copia) o None si todo
    estaba bien. ``copia`` es dónde se guarda esa última buena; solo el ``config.json`` de
    verdad la tiene por defecto.
    """

    def __init__(self, ruta=CONFIG_FILE, copia=...):
        self.ruta = ruta
        self.copia = (COPIA_BUENA if ruta == CONFIG_FILE else None) if copia is ... else copia
        self.datos = copy.deepcopy(DEFAULTS)
        self.nueva = not self.ruta.exists()
        self.recuperada = None
        self.cargar()

    def cargar(self):
        if not self.ruta.exists():
            self.guardar()
            return
        guardado = _leer(self.ruta)
        if guardado is None:
            guardado = self._recuperar()
        else:
            self._copiar_la_buena()
        for clave, de_fabrica in DEFAULTS.items():  # una sección de otro tipo no sirve: la de fábrica
            if isinstance(de_fabrica, dict) and clave in guardado and not isinstance(guardado[clave], dict):
                del guardado[clave]
        migrado = migrar(guardado)
        self.datos = _mezclar(DEFAULTS, guardado)
        tareas = self.datos["tareas"]
        for task_id in [t for t, opciones in tareas.items() if not isinstance(opciones, dict)]:
            del tareas[task_id]
        if migrado or self.recuperada:
            self.guardar()

    def _recuperar(self):
        """``config.json`` no se puede leer: se aparta y se usa la última copia buena, si hay."""
        if self.copia is not None:
            try:
                self.copia.parent.mkdir(parents=True, exist_ok=True)
                apartado = self.copia.with_name(f"config-danado-{_marca()}.json")
                os.replace(self.ruta, apartado)
                from .limpieza import limitar

                limitar(self.copia.parent, "config-danado-*.json", DANADOS_QUE_QUEDAN)  # P3: con límite
            except OSError as exc:
                log.warning("no pude apartar el config.json dañado: %s", exc)
        buena = _leer(self.copia) if self.copia is not None and self.copia.exists() else None
        self.recuperada = "copia" if buena is not None else "fabrica"
        log.error("config.json estaba dañado: %s", "recuperé la última copia buena" if buena is not None
                  else "no había copia, empiezo con los valores de fábrica")
        return buena if buena is not None else {}

    def _copiar_la_buena(self):
        """Guarda lo que se acaba de leer bien, solo si cambió (un archivo de pocos KB)."""
        if self.copia is None:
            return
        try:
            actual = self.ruta.read_bytes()
            if self.copia.exists() and self.copia.read_bytes() == actual:
                return
            self.copia.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.copia.with_name(self.copia.name + ".tmp")
            tmp.write_bytes(actual)
            os.replace(tmp, self.copia)
        except OSError as exc:
            log.warning("no pude guardar la copia de la configuración: %s", exc)

    def guardar(self):
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.ruta.with_suffix(".json.tmp")
        datos = self.datos
        if _es_de_fabrica(datos.get("mascota", {}).get("spritesheet")):
            # el de fábrica no se guarda: así una actualización del personaje sí te llega
            datos = {**datos, "mascota": {k: v for k, v in datos["mascota"].items() if k != "spritesheet"}}
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(datos, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())  # ROB-03: un corte de luz no deja el archivo vacío
        tmp.replace(self.ruta)

    @property
    def mascota(self):
        return self.datos["mascota"]

    def tarea(self, task_id):
        """Las opciones de una tarea (se crean vacías si aún no existen)."""
        tareas = self.datos.setdefault("tareas", {})
        if not isinstance(tareas.get(task_id), dict):
            tareas[task_id] = {}
        return tareas[task_id]
