"""Añadir un personaje propio a partir de una imagen (Configuración → Apariencia).

Formatos: PNG, GIF, WEBP o JPG. Pandex entiende tres casos:

- **Una imagen sola**: el mismo dibujo para todos los estados.
- **Una tira horizontal de poses del mismo tamaño** (como Rusty): la 1.ª es la normal,
  la 2.ª «trabajando», la 3.ª «feliz» y la 4.ª «error». Si faltan, se usa la normal;
  si sobran, se ignoran.
- **Un GIF animado**: cada cuadro es una pose, en ese mismo orden (la mascota no se
  anima: usa una pose fija por estado).

Si la imagen no tiene transparencia y el fondo es de un solo color (blanco, por
ejemplo), se quita solo. El resultado queda en ``%LOCALAPPDATA%\\Pandex\\personajes``,
así sobrevive a las actualizaciones. Pillow se carga solo aquí.
"""

import json
import re
import shutil
import unicodedata
from pathlib import Path

from .rutas import PERSONAJES_PROPIOS

EXTENSIONES = (".png", ".gif", ".webp", ".jpg", ".jpeg")
ESTADOS = ("idle", "trabajando", "feliz", "error")
MAX_POSES = 12
ALTO_MAX = 416       # más alto no se nota en pantalla y solo ocupa memoria
MARGEN = 2
TOLERANCIA = 40      # qué tan parecido al color de las esquinas cuenta como fondo


class ErrorPersonaje(Exception):
    """Algo que el usuario tiene que saber, con un mensaje para mostrarle."""


def nombre_desde_archivo(ruta):
    """``mi_gato-feliz.png`` → ``Mi gato feliz``."""
    texto = re.sub(r"[_\-]+", " ", Path(ruta).stem).strip()
    return texto[:1].upper() + texto[1:] if texto else "Mi personaje"


def id_para(nombre, ocupados):
    """Un id de carpeta a partir del nombre, sin tildes ni símbolos y sin repetirse."""
    base = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "_", base.lower()).strip("_") or "personaje"
    ident, n = base, 2
    while ident in ocupados:
        ident, n = f"{base}_{n}", n + 1
    return ident


# ---------- la imagen ----------


def _quitar_fondo(img):
    """Si no hay transparencia y las 4 esquinas son del mismo color, ese fondo se borra
    por contagio desde los bordes (los negros de adentro, como los ojos, se quedan)."""
    from PIL import ImageDraw

    if img.getchannel("A").getextrema()[0] < 255:
        return img  # ya trae transparencia
    w, h = img.size
    esquinas = [img.getpixel(p)[:3] for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
    ref = esquinas[0]
    if any(sum(abs(a - b) for a, b in zip(c, ref)) > TOLERANCIA for c in esquinas):
        return img  # el fondo no es liso: mejor no tocar nada
    img = img.copy()
    for punto in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if img.getpixel(punto)[3]:
            ImageDraw.floodfill(img, punto, (0, 0, 0, 0), thresh=TOLERANCIA)
    return img


def _partir(img):
    """Si es una tira de poses, la parte; si no, devuelve la imagen sola.

    Prueba con 2, 3… poses de igual ancho y se queda con la mayor cantidad cuyos cortes
    caen en columnas transparentes y deja poses de proporción razonable.
    """
    alfa = img.getchannel("A")
    w, h = img.size
    mejor = 1
    for n in range(2, MAX_POSES + 1):
        if w % n or not 0.35 <= (w / n) / h <= 2.5:
            continue
        ancho = w // n
        cortes_limpios = all(alfa.crop((k * ancho - 1, 0, k * ancho + 1, h)).getbbox() is None
                             for k in range(1, n))
        poses_llenas = all(alfa.crop((k * ancho, 0, (k + 1) * ancho, h)).getbbox()
                           for k in range(n))
        if cortes_limpios and poses_llenas:
            mejor = n
    ancho = w // mejor
    return [img.crop((k * ancho, 0, (k + 1) * ancho, h)) for k in range(mejor)]


def _poses(ruta):
    from PIL import Image, ImageSequence, UnidentifiedImageError

    try:
        with Image.open(ruta) as im:
            if getattr(im, "n_frames", 1) > 1:
                poses = [c.convert("RGBA") for _, c in zip(range(MAX_POSES), ImageSequence.Iterator(im))]
                return [_quitar_fondo(p) for p in poses]
            return _partir(_quitar_fondo(im.convert("RGBA")))
    except (OSError, UnidentifiedImageError) as exc:
        raise ErrorPersonaje("No pude leer esa imagen. Prueba con un PNG o un GIF.") from exc


def _caja_comun(poses):
    cajas = [p.getchannel("A").getbbox() for p in poses]
    if not any(cajas):
        raise ErrorPersonaje("La imagen está vacía (es toda transparente).")
    cajas = [c for c in cajas if c]
    return (min(c[0] for c in cajas), min(c[1] for c in cajas),
            max(c[2] for c in cajas), max(c[3] for c in cajas))


def importar(ruta, nombre, destino=PERSONAJES_PROPIOS, ocupados=()):
    """Crea la carpeta del personaje y devuelve ``(id, cantidad_de_poses)``."""
    from PIL import Image

    ruta = Path(ruta)
    if ruta.suffix.lower() not in EXTENSIONES:
        raise ErrorPersonaje("Usa una imagen PNG, GIF, WEBP o JPG.")
    poses = _poses(ruta)
    x0, y0, x1, y1 = _caja_comun(poses)
    poses = [p.crop((x0, y0, x1, y1)) for p in poses]
    w, h = poses[0].size
    if h > ALTO_MAX:  # se reduce: pixel art sin suavizar, lo demás suavizado
        escala = ALTO_MAX / h
        pocos_colores = poses[0].getcolors(256) is not None
        filtro = Image.Resampling.NEAREST if pocos_colores else Image.Resampling.LANCZOS
        w, h = max(1, round(w * escala)), ALTO_MAX
        poses = [p.resize((w, h), filtro) for p in poses]

    cw, ch = w + 2 * MARGEN, h + 2 * MARGEN
    hoja = Image.new("RGBA", (cw * len(poses), ch), (0, 0, 0, 0))
    for i, pose in enumerate(poses):
        hoja.paste(pose, (i * cw + MARGEN, MARGEN))

    ident = id_para(nombre, set(ocupados) | _existentes(destino))
    carpeta = destino / ident
    carpeta.mkdir(parents=True, exist_ok=True)
    try:
        hoja.save(carpeta / "spritesheet.png", optimize=True)
        # para el logo: la parte de arriba si es alto (la cabeza), o todo si es ancho
        alto_cabeza = round(ch * 0.6) if ch > cw * 1.15 else ch
        datos = {
            "nombre": nombre.strip(),
            "autor": f"Añadido desde {ruta.name}",
            "cuadro": [cw, ch],
            "cuadros": {e: (i if i < len(poses) else 0) for i, e in enumerate(ESTADOS)},
            "recorte": [0, 0, cw, ch],
            "cabeza": [0, 0, cw, alto_cabeza],
            "orden": 100,
        }
        (carpeta / "personaje.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
    except OSError as exc:
        shutil.rmtree(carpeta, ignore_errors=True)
        raise ErrorPersonaje(f"No pude guardarlo: {exc}") from exc
    return ident, len(poses)


def _existentes(destino):
    try:
        return {d.name for d in destino.iterdir()}
    except OSError:
        return set()


def quitar(ident, destino=PERSONAJES_PROPIOS):
    """Borra un personaje que añadiste (los que trae Pandex no se pueden quitar)."""
    carpeta = destino / ident
    if carpeta.parent != destino or not (carpeta / "personaje.json").exists():
        raise ErrorPersonaje("Ese personaje no es uno que hayas añadido.")
    shutil.rmtree(carpeta)
