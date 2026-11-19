"""Carga y validación segura de extensiones personales y publicadas."""

import json
import importlib.util
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from .log import get_logger

log = get_logger("pandex.plugins")

ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")
PERMISOS = frozenset({
    "red.departamento",
    "red.google",
    "red.proveedor_ia",
    "datos.tareas",
    "calendario.leer",
    "calendario.escribir",
    "ia.delegar",
    "avisos.locales",
    "almacenamiento.plugin",
})
MAX_PAQUETE = 100 * 1024 * 1024


class ErrorManifest(ValueError):
    pass


class ErrorPaquete(ValueError):
    pass


def _ruta_segura(carpeta, nombre):
    base = carpeta.resolve()
    destino = (base / nombre).resolve()
    if base not in destino.parents and destino != base:
        raise ErrorManifest("La entrada del plugin sale de su carpeta")
    return destino


def leer_manifest(carpeta):
    """Lee y valida manifest.json sin ejecutar código del paquete."""
    carpeta = Path(carpeta)
    ruta = carpeta / "manifest.json"
    if not ruta.is_file():
        raise ErrorManifest("Falta manifest.json")
    try:
        data = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ErrorManifest(f"manifest.json no es válido: {exc}") from exc

    for clave in ("id", "nombre", "version", "entrada", "licencia"):
        if not isinstance(data.get(clave), str) or not data[clave].strip():
            raise ErrorManifest(f"Falta o está vacío '{clave}'")
    if not ID_RE.fullmatch(data["id"]):
        raise ErrorManifest("id debe usar letras minúsculas ASCII, números y _")
    if not VERSION_RE.fullmatch(data["version"]):
        raise ErrorManifest("version debe usar semántica x.y.z")

    entrada = data["entrada"]
    if not isinstance(entrada, str) or not entrada.lower().endswith(".py"):
        raise ErrorManifest("entrada debe ser un archivo Python")
    try:
        ruta_entrada = _ruta_segura(carpeta, entrada)
    except ErrorManifest as exc:
        raise ErrorManifest(str(exc)) from exc
    if not ruta_entrada.is_file():
        raise ErrorManifest("El archivo de entrada no existe")

    permisos = data.get("permisos", [])
    if not isinstance(permisos, list) or not all(isinstance(p, str) for p in permisos):
        raise ErrorManifest("permisos debe ser una lista")
    desconocidos = set(permisos) - PERMISOS
    if desconocidos:
        raise ErrorManifest("Permisos no reconocidos: " + ", ".join(sorted(desconocidos)))
    data["permisos"] = list(dict.fromkeys(permisos))
    return data


def instalar_zip(ruta_zip, destino):
    """Extrae un paquete con límites y sin rutas de escape."""
    ruta_zip = Path(ruta_zip)
    destino = Path(destino)
    try:
        with zipfile.ZipFile(ruta_zip) as zf:
            archivos = zf.infolist()
            total = sum(a.file_size for a in archivos)
            if total > MAX_PAQUETE:
                raise ErrorPaquete("El paquete pesa más de 100 MB")
            destino.mkdir(parents=True, exist_ok=True)
            base = destino.resolve()
            for archivo in archivos:
                nombre = archivo.filename.replace("\\", "/")
                if nombre.startswith("/") or ".." in Path(nombre).parts:
                    raise ErrorPaquete("El paquete contiene una ruta insegura")
                destino_archivo = (base / nombre).resolve()
                if base not in destino_archivo.parents and destino_archivo != base:
                    raise ErrorPaquete("El paquete contiene una ruta insegura")
                if archivo.is_dir():
                    destino_archivo.mkdir(parents=True, exist_ok=True)
                else:
                    destino_archivo.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(archivo) as origen, destino_archivo.open("wb") as salida:
                        while True:
                            bloque = origen.read(1024 * 1024)
                            if not bloque:
                                break
                            salida.write(bloque)
    except zipfile.BadZipFile as exc:
        raise ErrorPaquete("El archivo no es un ZIP válido") from exc

    return destino


def instalar_personal(ruta_zip, carpeta):
    """Instala un ZIP personal validado en una carpeta separada por id."""
    carpeta = Path(carpeta)
    with tempfile.TemporaryDirectory(prefix="pandex-plugin-") as tmp:
        temporal = Path(tmp) / "contenido"
        instalar_zip(ruta_zip, temporal)
        manifest = leer_manifest(temporal)
        destino = carpeta / manifest["id"]
        carpeta.mkdir(parents=True, exist_ok=True)
        if destino.exists():
            raise ErrorPaquete("Ya existe un plugin personal con ese id")
        shutil.copytree(temporal, destino)
    log.info("plugin personal instalado: %s", manifest["id"])
    return destino


def revisar_personal(ruta_zip):
    """Valida un ZIP personal y devuelve el manifiesto sin instalarlo."""
    with tempfile.TemporaryDirectory(prefix="pandex-plugin-review-") as tmp:
        temporal = Path(tmp) / "contenido"
        instalar_zip(ruta_zip, temporal)
        return leer_manifest(temporal)


def descubrir_personales(carpeta):
    """Carga manifiestos personales sin exponer plugin roto al resto de Pandex."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    encontradas = []
    vistos = set()
    for directorio in sorted(p for p in carpeta.iterdir() if p.is_dir()):
        try:
            manifest = leer_manifest(directorio)
            if manifest["id"] in vistos:
                log.warning("plugin personal duplicado '%s'", manifest["id"])
                continue
            archivo = _ruta_segura(directorio, manifest["entrada"])
            nombre = f"pandex_plugin_personal_{manifest['id']}"
            spec = importlib.util.spec_from_file_location(nombre, archivo)
            modulo = importlib.util.module_from_spec(spec)
            sys.modules[nombre] = modulo
            spec.loader.exec_module(modulo)
            clase = getattr(modulo, "Task", None)
            if clase is None:
                raise ErrorManifest("El plugin no define la clase Task")
            tarea = clase()
            if getattr(tarea, "id", None) != manifest["id"]:
                raise ErrorManifest("El id de Task no coincide con manifest.json")
            tarea.nombre = getattr(tarea, "nombre", None) or manifest["nombre"]
            tarea.descripcion = getattr(tarea, "descripcion", None) or manifest.get("descripcion", "")
            tarea.schedule = getattr(tarea, "schedule", None)
            tarea.icono = getattr(tarea, "icono", None) or "tarea"
            tarea.plugin_personal = True
            tarea.plugin_manifest = manifest
            vistos.add(manifest["id"])
            encontradas.append(tarea)
        except Exception as exc:
            log.error("no pude cargar el plugin personal %s: %s", directorio.name, exc)
    return encontradas


def sembrar_conectores(carpeta):
    """Crea los plugins personales de Calendar e IA sin guardar credenciales en Git."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    contenidos = {
        "calendar_google": (
            {
                "id": "calendar_google",
                "nombre": "Google Calendar",
                "version": "1.0.0",
                "entrada": "calendar_google.py",
                "descripcion": "Consulta Google Calendar y crea eventos solo con autorización.",
                "licencia": "MIT",
                "permisos": ["red.google", "calendario.leer", "calendario.escribir", "almacenamiento.plugin"],
            },
            "from pandex.calendar_google import consultar_eventos\n\n"
            "class Task:\n"
            "    id = 'calendar_google'\n"
            "    nombre = 'Google Calendar'\n"
            "    descripcion = 'Consulta eventos de Google Calendar.'\n"
            "    schedule = '*/30 * * * *'\n"
            "    def run(self, ctx):\n"
            "        try:\n"
            "            eventos = consultar_eventos()\n"
            "            return {'ok': True, 'resumen': f'Encontré {len(eventos)} evento(s).'}\n"
            "        except Exception as exc:\n"
            "            return {'ok': False, 'resumen': str(exc)}\n",
        ),
        "ia": (
            {
                "id": "ia",
                "nombre": "Conectar una IA",
                "version": "1.0.0",
                "entrada": "ia.py",
                "descripcion": "Delega tareas a OpenCode, Antigravity u otra IA local.",
                "licencia": "MIT",
                "permisos": ["red.proveedor_ia", "ia.delegar", "almacenamiento.plugin"],
            },
            "from PyQt6.QtWidgets import QInputDialog\n"
            "from pandex.ia import AdaptadorLocal\n\n"
            "class Task:\n"
            "    id = 'ia'\n"
            "    nombre = 'Delegar a una IA'\n"
            "    descripcion = 'Envía una tarea a la IA conectada.'\n"
            "    def preparar(self, ctx):\n"
            "        texto, ok = QInputDialog.getText(None, 'Delegar tarea', '¿Qué quieres que haga la IA?')\n"
            "        return texto if ok and texto.strip() else None\n"
            "    def run(self, ctx):\n"
            "        from pathlib import Path\n"
            "        from pandex import ia\n"
            "        from pandex.rutas import PLUGINS_PERSONALES\n"
            "        estado = ia.leer_estado(Path(PLUGINS_PERSONALES) / 'ia')\n"
            "        proveedor = estado.get('proveedor', 'opencode')\n"
            "        ejecutable = estado.get('ejecutable', proveedor)\n"
            "        resultado = AdaptadorLocal(proveedor, ejecutable).responder(ctx.entrada)\n"
            "        if not resultado.ok:\n"
            "            return {'ok': False, 'resumen': resultado.error}\n"
            "        return {'ok': True, 'resumen': 'La IA respondió.', 'informe': resultado.texto}\n",
        ),
    }
    sembrados = []
    for id_plugin, (manifest, entrada) in contenidos.items():
        destino = carpeta / id_plugin
        destino.mkdir(parents=True, exist_ok=True)
        if not (destino / "manifest.json").exists():
            (destino / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        if not (destino / "calendar_google.py").exists() and id_plugin == "calendar_google":
            (destino / "calendar_google.py").write_text(entrada, encoding="utf-8")
        if not (destino / "ia.py").exists() and id_plugin == "ia":
            (destino / "ia.py").write_text(entrada, encoding="utf-8")
        sembrados.append(destino)
    return sembrados
