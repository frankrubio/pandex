"""Comprimir una carpeta para subirla a un drive: un .zip y, si quieres, PDFs más livianos.

Un .zip solo ahorra en lo que no viene comprimido (texto, .md, código, .csv…). PDF,
Word, PowerPoint, imágenes y videos ya vienen comprimidos: ahí el .zip casi no ayuda.
Lo que sí baja mucho el peso de un curso son los PDF escaneados o con imágenes grandes:
Ghostscript los rehace a calidad de pantalla (150 ppp). Se usa solo si está instalado
y solo se queda la versión nueva si de verdad pesa menos. Tus archivos no se tocan:
todo va dentro del .zip.
"""

import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from .log import get_logger

log = get_logger("pandex.comprimir")

# ya vienen comprimidos: se guardan tal cual (más rápido y pesa igual)
YA_COMPRIMIDOS = {
    ".zip", ".rar", ".7z", ".gz", ".xz", ".bz2", ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".mp3", ".mp4", ".m4a", ".mkv", ".mov", ".avi", ".webm", ".docx", ".pptx", ".xlsx",
    ".odt", ".odp", ".ods", ".epub",
}


def ghostscript():
    """La ruta de Ghostscript, o None."""
    for nombre in ("gs", "gswin64c", "gswin32c"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    return None


def reducir_pdf(origen, destino, gs=None):
    """Rehace el PDF a calidad de pantalla. True si quedó más liviano (y está en ``destino``)."""
    gs = gs or ghostscript()
    if gs is None:
        return False
    try:
        r = subprocess.run(
            [gs, "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.5", "-dPDFSETTINGS=/ebook",
             "-dNOPAUSE", "-dQUIET", "-dBATCH", f"-sOutputFile={destino}", str(origen)],
            capture_output=True, timeout=600, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("Ghostscript falló con %s: %s", origen, exc)
        return False
    if r.returncode != 0 or not Path(destino).is_file():
        return False
    return Path(destino).stat().st_size < Path(origen).stat().st_size


def destino_para(carpeta):
    """``Curso`` → ``Curso.zip`` al lado; si existe, ``Curso (2).zip``…"""
    carpeta = Path(carpeta)
    zip_ = carpeta.with_name(carpeta.name + ".zip")
    n = 2
    while zip_.exists():
        zip_ = carpeta.with_name(f"{carpeta.name} ({n}).zip")
        n += 1
    return zip_


def comprimir(carpeta, destino=None, pdfs=False, progreso=None):
    """Crea el .zip de ``carpeta``. Devuelve ``{"zip", "antes", "despues", "pdfs"}``."""
    carpeta = Path(carpeta)
    destino = Path(destino) if destino else destino_para(carpeta)
    archivos = sorted(p for p in carpeta.rglob("*") if p.is_file() and p != destino)
    gs = ghostscript() if pdfs else None
    antes, reducidos = 0, 0
    temporal = destino.with_name(destino.name + ".parcial")
    try:
        with tempfile.TemporaryDirectory() as tmp, \
                zipfile.ZipFile(temporal, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for i, archivo in enumerate(archivos, 1):
                antes += archivo.stat().st_size
                nombre = archivo.relative_to(carpeta.parent).as_posix()
                fuente = archivo
                if gs and archivo.suffix.lower() == ".pdf":
                    liviano = Path(tmp) / "reducido.pdf"
                    if reducir_pdf(archivo, liviano, gs):
                        fuente, reducidos = liviano, reducidos + 1
                metodo = zipfile.ZIP_STORED if archivo.suffix.lower() in YA_COMPRIMIDOS else zipfile.ZIP_DEFLATED
                zf.write(fuente, nombre, compress_type=metodo)
                if progreso:
                    progreso(i, len(archivos))
        os.replace(temporal, destino)
    finally:
        temporal.unlink(missing_ok=True)
    return {"zip": destino, "antes": antes, "despues": destino.stat().st_size,
            "pdfs": reducidos, "archivos": len(archivos)}


def tamano(n):
    for unidad in ("B", "KB", "MB", "GB"):
        if n < 1024 or unidad == "GB":
            return f"{n:.0f} {unidad}" if unidad == "B" else f"{n:.1f} {unidad}"
        n /= 1024
