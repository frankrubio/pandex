"""Añadir un personaje propio a partir de una imagen (Configuración → Apariencia).

Formatos: PNG, GIF, WEBP o JPG. Pandex entiende tres casos:

- **Una imagen sola**: el mismo dibujo para todos los estados.
- **Una tira horizontal de poses del mismo tamaño** (como Rusty): la 1.ª es la normal,
  la 2.ª «trabajando», la 3.ª «feliz» y la 4.ª «error». Si faltan, se usa la normal;
  si sobran, se ignoran.
- **Un GIF animado**: cada cuadro es una pose, en ese mismo orden (la mascota no se
  anima: usa una pose fija por estado).
- **Una mascota de Codex Pets** (codex-pets.net): su ``spritesheet.webp`` o el ``.zip``
  descargado (con ``pet.json``). Es una cuadrícula de 8 columnas con cuadros de 192×208,
  una fila por animación; Pandex toma una pose de la fila que corresponde a cada estado
  y el nombre del ``pet.json``.

Si la imagen no tiene transparencia y el fondo es de un solo color (blanco, por
ejemplo), se quita solo. El resultado queda en ``%LOCALAPPDATA%\\Pandex\\personajes``,
así sobrevive a las actualizaciones. Pillow se carga solo aquí.
"""

import io
import json
import re
import shutil
import unicodedata
import zipfile
from pathlib import Path

from .rutas import PERSONAJES_PROPIOS

EXTENSIONES = (".png", ".gif", ".webp", ".jpg", ".jpeg", ".zip")
ESTADOS = ("idle", "trabajando", "feliz", "error")
MAX_POSES = 12
ALTO_MAX = 416       # más alto no se nota en pantalla y solo ocupa memoria
MARGEN = 2
TOLERANCIA = 40      # qué tan parecido al color de las esquinas cuenta como fondo
MAX_ZIP = 40 * 1024 * 1024  # un ZIP de mascota pesa pocos KB; más que esto no es una mascota

# Codex Pets: atlas de 8 columnas, cuadros de 192×208 y una fila por animación
# (0 idle, 1-2 correr, 3 saludar, 4 saltar, 5 falló, 6 esperar, 7 correr, 8 revisar…).
# Para cada estado de Pandex: (fila, columna) de la pose que mejor lo cuenta.
CODEX_COLUMNAS = 8
CODEX_PROPORCION = 208 / 192
CODEX_POSES = {"idle": (0, 0), "trabajando": (8, 0), "feliz": (3, 1), "error": (5, 2)}


class ErrorPersonaje(Exception):
    """Algo que el usuario tiene que saber, con un mensaje para mostrarle."""


def nombre_desde_archivo(ruta):
    """El nombre que se le sugiere al usuario.

    El ``displayName`` del ``pet.json`` de Codex Pets si lo hay (dentro del ZIP o al lado
    de la imagen); si no, el del archivo: ``mi_gato-feliz.png`` → ``Mi gato feliz``.
    """
    ruta = Path(ruta)
    manifiesto = _manifiesto(ruta)
    if manifiesto.get("displayName"):
        return str(manifiesto["displayName"]).strip()[:40]
    base = ruta.parent.name if ruta.stem.lower() in ("spritesheet", "sprite", "pet") else ruta.stem
    texto = re.sub(r"[_\-]+", " ", base).strip()
    return texto[:1].upper() + texto[1:] if texto else "Mi personaje"


def _manifiesto(ruta):
    """El ``pet.json`` de Codex Pets, del ZIP o de la carpeta de la imagen (o ``{}``)."""
    try:
        if ruta.suffix.lower() == ".zip":
            with zipfile.ZipFile(ruta) as z:
                nombre = next((n for n in z.namelist() if Path(n).name.lower() == "pet.json"), None)
                return json.loads(z.read(nombre)) if nombre else {}
        vecino = ruta.parent / "pet.json"
        return json.loads(vecino.read_text(encoding="utf-8")) if vecino.exists() else {}
    except (OSError, ValueError, zipfile.BadZipFile, KeyError):
        return {}


def _abrir(ruta):
    """La imagen a leer: el archivo, o el sprite sheet de adentro si es un ZIP."""
    if ruta.suffix.lower() != ".zip":
        return ruta
    try:
        with zipfile.ZipFile(ruta) as z:
            nombres = [n for n in z.namelist() if not n.endswith("/")]
            pedido = str(_manifiesto(ruta).get("spritesheetPath") or "")
            candidatos = [n for n in nombres if pedido and n.endswith(pedido)] or [
                n for n in nombres if Path(n).suffix.lower() in EXTENSIONES[:-1]]
            if not candidatos:
                raise ErrorPersonaje("Ese ZIP no trae ninguna imagen de mascota.")
            info = z.getinfo(candidatos[0])
            if info.file_size > MAX_ZIP:
                raise ErrorPersonaje("La imagen de ese ZIP es demasiado grande para una mascota.")
            return io.BytesIO(z.read(info))
    except zipfile.BadZipFile as exc:
        raise ErrorPersonaje("Ese ZIP está dañado o no es un ZIP.") from exc


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


def _rejilla_codex(img):
    """``(ancho, alto)`` de cada cuadro si la imagen es un atlas de Codex Pets; si no, None.

    Se reconoce por la forma: 8 columnas de cuadros 192×208 (o la misma proporción, por si
    la imagen se reescaló) y 9 filas o más.
    """
    w, h = img.size
    ancho = w / CODEX_COLUMNAS
    if ancho < 64 or img.getchannel("A").getextrema()[0] > 0:
        return None  # muy chica para ser un atlas, o sin fondo transparente (Codex siempre lo tiene)
    alto = ancho * CODEX_PROPORCION
    filas = round(h / alto)
    if filas < 9 or abs(h - filas * alto) > max(2, h * 0.01):
        return None
    return ancho, h / filas


def _poses_codex(img, ancho, alto):
    def celda(fila, columna):
        caja = (round(columna * ancho), round(fila * alto), round((columna + 1) * ancho), round((fila + 1) * alto))
        return img.crop(caja)

    poses = []
    for estado in ESTADOS:
        fila, columna = CODEX_POSES[estado]
        pose = celda(fila, columna)
        if pose.getchannel("A").getbbox() is None:  # fila más corta: su primer cuadro
            pose = celda(fila, 0)
        if pose.getchannel("A").getbbox() is None:  # fila vacía: la normal
            pose = celda(0, 0)
        poses.append(pose)
    return poses


def _poses(ruta):
    from PIL import Image, ImageSequence, UnidentifiedImageError

    try:
        with Image.open(_abrir(ruta)) as im:
            if getattr(im, "n_frames", 1) > 1:
                poses = [c.convert("RGBA") for _, c in zip(range(MAX_POSES), ImageSequence.Iterator(im))]
                return [_quitar_fondo(p) for p in poses]
            img = im.convert("RGBA")
            rejilla = _rejilla_codex(img)
            if rejilla:
                return _poses_codex(img, *rejilla)
            return _partir(_quitar_fondo(img))
    except (OSError, UnidentifiedImageError) as exc:
        raise ErrorPersonaje("No pude leer esa imagen. Prueba con un PNG, un GIF o el ZIP de "
                             "Codex Pets.") from exc


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
        raise ErrorPersonaje("Usa una imagen PNG, GIF, WEBP o JPG, o el ZIP de Codex Pets.")
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
