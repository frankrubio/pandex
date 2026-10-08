"""Memoria local de la sincronización: qué archivo de Canvas ya está en tu disco.

Vive en ``%LOCALAPPDATA%\\Pandex\\historial_canvas.json``, fuera de OneDrive y del
repositorio. Es solo un atajo para no volver a preguntarle a Canvas lo que ya se
resolvió: si el archivo anotado ya no existe, se revisa desde cero.

Guarda tres cosas:

- ``archivos``: id de Canvas -> ruta en disco (y tamaño)
- ``sin_listado``: cursos donde Canvas negó el listado de archivos (se reintenta
  cada 30 días en vez de en cada corrida)
- ``omitidos``: archivos que decidiste no bajar en la descarga inicial
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from ..rutas import DATOS

RUTA = DATOS / "historial_canvas.json"
LEGADO = DATOS / "registro_canvas.json"  # nombre de las primeras versiones
REINTENTAR_LISTADO_DIAS = 30


class Historial:
    VERSION = 1

    def __init__(self, ruta=None):
        self.ruta = Path(ruta or RUTA)
        if ruta is None and not self.ruta.exists() and LEGADO.exists():
            LEGADO.replace(self.ruta)
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            datos = {}
        if datos.get("version") != self.VERSION:
            datos = {}
        self.archivos = datos.get("archivos", {})
        self.sin_listado = datos.get("sin_listado", {})
        self.omitidos = datos.get("omitidos", {})
        self.cambios = False

    # ---------- archivos en disco ----------

    def conocido(self, file_id):
        """La ruta donde está ese archivo, si sigue existiendo; si no, None."""
        entrada = self.archivos.get(str(file_id))
        if entrada:
            ruta = Path(entrada["ruta"])
            if ruta.exists():
                return ruta
        return None

    def anotar(self, file_id, ruta, tamano=None):
        self.archivos[str(file_id)] = {"ruta": str(ruta), "tamano": tamano}
        self.cambios = True

    # ---------- descarga inicial ----------

    def omitido(self, file_id):
        return str(file_id) in self.omitidos

    def omitir(self, file_id):
        self.omitidos[str(file_id)] = datetime.now().isoformat(timespec="seconds")
        self.cambios = True

    # ---------- listados negados ----------

    def listado_prohibido(self, curso_id):
        cuando = self.sin_listado.get(str(curso_id))
        if not cuando:
            return False
        try:
            fecha = datetime.fromisoformat(cuando)
        except ValueError:
            return False
        return datetime.now() - fecha < timedelta(days=REINTENTAR_LISTADO_DIAS)

    def prohibir_listado(self, curso_id):
        self.sin_listado[str(curso_id)] = datetime.now().isoformat(timespec="seconds")
        self.cambios = True

    # ---------- disco ----------

    def guardar(self):
        if not self.cambios:
            return
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.ruta.with_suffix(".tmp")
        datos = {"version": self.VERSION, "archivos": self.archivos,
                 "sin_listado": self.sin_listado, "omitidos": self.omitidos}
        tmp.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.ruta)
        self.cambios = False
