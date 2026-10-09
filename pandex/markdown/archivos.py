"""Qué archivos se pueden convertir, dónde va cada .md y cómo se escribe.

Reglas de los .md:

- van junto al original, con el mismo nombre base (``Clase 3.pdf`` -> ``Clase 3.md``);
- si en la carpeta hay ``Clase 3.pptx`` y ``Clase 3.pdf``, se distinguen:
  ``Clase 3 (pptx).md`` y ``Clase 3 (pdf).md``;
- la primera línea lleva una marca (``<!-- Pandex: …``): solo esos .md se pueden
  reescribir al «forzar»; uno escrito por ti nunca se pisa.
"""

import os
import re
import shutil
from collections import Counter
from pathlib import Path

from ..rutas import DATOS

SOPORTADOS = {
    ".pdf": "PDF",
    ".docx": "Word",
    ".pptx": "PowerPoint",
    ".xlsx": "Excel",
    ".xls": "Excel",
    ".html": "HTML",
    ".htm": "HTML",
    ".csv": "CSV",
    ".json": "JSON",
    ".xml": "XML",
    ".epub": "EPUB",
    ".png": "imagen",
    ".jpg": "imagen",
    ".jpeg": "imagen",
}
AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".oga", ".opus", ".wma", ".amr"}
VIDEO = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv", ".m4v", ".3gp", ".mpeg", ".mpg"}
SIN_IA = AUDIO | VIDEO

TEXTO_PLANO = {".html", ".htm", ".csv", ".json", ".xml"}
CON_OCR = {".pdf", ".png", ".jpg", ".jpeg"}
# solo en estos un texto corto delata "era una imagen"; un CSV corto es solo un CSV chico
PUEDEN_SER_IMAGEN = {".pdf", ".pptx", ".docx", ".epub", ".png", ".jpg", ".jpeg"}

# carpetas que nunca tienen material de clase y sí miles de .json/.html
# (_duplicados_a_revisar: cuarentena de versiones antiguas de Pandex)
CARPETAS_OMITIDAS = {
    "node_modules", "__pycache__", "site-packages", "venv", "env",
    "$recycle.bin", "system volume information", "_duplicados_a_revisar",
}


MARCA = "<!-- Pandex:"
TEMPORAL = DATOS / "md_tmp"
ATRIBUTOS_OCULTOS = 0x2 | 0x4  # FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM
AVISO_LOTE = 100


def orden_natural(texto):
    """'Sem 2' antes que 'Sem 10'."""
    return [int(t) if t.isdigit() else t.casefold() for t in re.split(r"(\d+)", texto)]


def raices(extra=()):
    """Los puntos de partida, resueltos en cada llamada (el OneDrive puede cambiar de nombre).

    ``extra``: ``[(etiqueta, ruta)]`` que van primero, p. ej. tu carpeta de cursos de Canvas.
    """
    casa = Path(os.environ.get("USERPROFILE") or Path.home())
    salida = [(etiqueta, Path(ruta)) for etiqueta, ruta in extra if ruta and Path(ruta).is_dir()]
    try:
        onedrives = sorted(
            (d for d in casa.iterdir() if d.name.startswith("OneDrive - ") and d.is_dir()),
            key=lambda d: d.name.casefold(),
        )
    except OSError:
        onedrives = []
    for d in onedrives:
        institucion = d.name.removeprefix("OneDrive - ")
        salida.append((f"OneDrive institucional · {institucion}", d))
    # el Escritorio puede estar dentro de OneDrive (copia de seguridad de carpetas)
    escritorio = next((d for d in (casa / "Desktop", casa / "OneDrive" / "Desktop",
                                   casa / "OneDrive" / "Escritorio") if d.is_dir()), None)
    for etiqueta, ruta in (("Escritorio", escritorio), ("Descargas", casa / "Downloads"),
                           ("Documentos", casa / "Documents")):
        if ruta is not None and ruta.is_dir():
            salida.append((etiqueta, ruta))
    return salida


def _oculto(entrada):
    nombre = entrada.name
    if nombre.startswith((".", "~$", "$")) or nombre.casefold() == "desktop.ini":
        return True
    try:
        return bool(entrada.stat(follow_symlinks=False).st_file_attributes & ATRIBUTOS_OCULTOS)
    except (OSError, AttributeError):
        return False


def _es_carpeta(entrada):
    try:
        return entrada.is_dir(follow_symlinks=False) and not entrada.is_junction()
    except OSError:
        return False


def listar(carpeta):
    """(subcarpetas, convertibles, cuántos de audio/video) de UN nivel."""
    subcarpetas, archivos, sin_ia = [], [], 0
    try:
        with os.scandir(carpeta) as it:
            for e in it:
                if _oculto(e):
                    continue
                if _es_carpeta(e):
                    if e.name.casefold() not in CARPETAS_OMITIDAS:
                        subcarpetas.append(Path(e.path))
                    continue
                ext = os.path.splitext(e.name)[1].lower()
                if ext in SOPORTADOS:
                    archivos.append(Path(e.path))
                elif ext in SIN_IA:
                    sin_ia += 1
    except OSError:
        pass
    subcarpetas.sort(key=lambda p: orden_natural(p.name))
    archivos.sort(key=lambda p: orden_natural(p.name))
    return subcarpetas, archivos, sin_ia


def recorrer(carpeta, recursivo):
    """Todos los archivos (visibles) de la carpeta, y de sus subcarpetas si se pide."""
    pendientes = [Path(carpeta)]
    while pendientes:
        actual = pendientes.pop()
        hijos = []
        try:
            with os.scandir(actual) as it:
                for e in it:
                    if _oculto(e):
                        continue
                    if _es_carpeta(e):
                        if recursivo and e.name.casefold() not in CARPETAS_OMITIDAS:
                            hijos.append(Path(e.path))
                    else:
                        yield Path(e.path)
        except OSError:
            continue
        pendientes.extend(sorted(hijos, key=lambda p: orden_natural(p.name), reverse=True))


def nombres_repetidos(carpeta):
    """Nombres base que en esta carpeta tienen más de un archivo convertible.

    Los profes suben la misma clase en .pptx y .pdf: ambos darían «Clase 3.md»
    y el segundo se perdería. A esos se les agrega el tipo: «Clase 3 (pdf).md».
    """
    _, archivos, _ = listar(carpeta)
    cuenta = Counter(p.stem.casefold() for p in archivos)
    return {stem for stem, n in cuenta.items() if n > 1}


def ruta_md(archivo, repetidos=None):
    if repetidos is None:
        repetidos = nombres_repetidos(archivo.parent)
    if archivo.stem.casefold() in repetidos:
        tipo = archivo.suffix.lstrip(".").lower()
        return archivo.with_name(f"{archivo.stem} ({tipo}).md")
    return archivo.with_name(archivo.stem + ".md")


def generado_por_pandex(md):
    try:
        with open(md, encoding="utf-8", errors="replace") as fh:
            return fh.read(len(MARCA) + 4).lstrip("﻿").startswith(MARCA)
    except OSError:
        return False


def escribir_atomico(destino, contenido):
    """Escribe fuera de OneDrive y mueve al final: nunca queda un .md a medias sincronizando."""
    TEMPORAL.mkdir(parents=True, exist_ok=True)
    tmp = TEMPORAL / f"{os.getpid()}_{abs(hash(str(destino)))}.md"
    tmp.write_text(contenido, encoding="utf-8")
    try:
        os.replace(tmp, destino)
    except OSError:
        shutil.copyfile(tmp, destino)
        tmp.unlink(missing_ok=True)
