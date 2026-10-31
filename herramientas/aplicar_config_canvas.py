"""Mezcla un archivo con parámetros de Canvas en tu ``config.json`` (spec 008, EST-07).

Para quien ya tiene su configuración de Canvas escrita en un archivo (cursos, calendario,
estilo de carpetas…) y no quiere repetir el asistente ni editar ``config.json`` a mano.

    python herramientas/aplicar_config_canvas.py mi_canvas.json

Cierra Pandex antes: guarda su propia configuración al salir y pisaría el cambio.
Solo toca ``tareas → sync_canvas``: lo que el archivo trae reemplaza lo que había (las listas,
como ``cursos``, se reemplazan enteras) y lo que no trae se queda. Antes deja una copia
``config.json.antes-AAAAMMDD-HHMMSS`` al lado. Si el archivo no es un JSON válido, no toca nada.
"""

import copy
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from pandex.rutas import CONFIG_FILE  # noqa: E402


class ErrorConfig(Exception):
    """Algo que se le puede decir al usuario tal cual."""


def _leer(ruta, que):
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise ErrorConfig(f"No pude leer {que} ({ruta}): {exc.strerror or exc}") from exc
    except ValueError as exc:
        raise ErrorConfig(f"{que} ({ruta}) no es un JSON válido: {exc}") from exc
    if not isinstance(datos, dict):
        raise ErrorConfig(f"{que} ({ruta}) debe ser un objeto JSON: {{ ... }}")
    return datos


def aplicar(archivo, config=CONFIG_FILE):
    """Mezcla ``archivo`` en ``config`` (tareas → sync_canvas). Devuelve la copia de respaldo o None."""
    nuevo = _leer(archivo, "El archivo")
    config = Path(config)
    existia = config.exists()
    actual = _leer(config, "Tu config.json") if existia else {}

    mezclado = copy.deepcopy(actual)
    canvas = mezclado.setdefault("tareas", {}).setdefault("sync_canvas", {})
    canvas.update(nuevo)

    respaldo = None
    if existia:
        respaldo = config.with_name(f"{config.name}.antes-{datetime.now():%Y%m%d-%H%M%S}")
        shutil.copy2(config, respaldo)
    config.parent.mkdir(parents=True, exist_ok=True)
    temporal = config.with_name(config.name + ".tmp")
    temporal.write_text(json.dumps(mezclado, ensure_ascii=False, indent=2), encoding="utf-8")
    temporal.replace(config)
    return respaldo


def main(argumentos=None):
    argumentos = sys.argv[1:] if argumentos is None else argumentos
    if len(argumentos) != 1:
        print("Uso: python herramientas/aplicar_config_canvas.py mi_canvas.json")
        return 2
    try:
        respaldo = aplicar(argumentos[0])
    except ErrorConfig as exc:
        print(f"No toqué nada. {exc}")
        return 1
    print(f"Listo: apliqué {argumentos[0]} a {CONFIG_FILE}.")
    if respaldo:
        print(f"Tu configuración anterior quedó en {respaldo}.")
    print("Abre Pandex y haz clic derecho → Sincronizar Canvas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
