"""Los personajes de Pandex: Rusty y los demás, cada uno en su carpeta.

Cada personaje vive en ``assets/personajes/<id>/``:

- ``spritesheet.png``: los cuadros en fila, todos del mismo tamaño.
- ``personaje.json``: su nombre, qué cuadro usa cada estado, el recorte común (para
  que la figura no salte al cambiar de estado) y la cabeza (para el logo).
- ``icono.ico``: el ícono de la app con su cara (``herramientas/crear_icono.py``).

Para agregar uno basta con crear su carpeta: aparece solo en Configuración. Los
dibujos nuevos se hacen con ``herramientas/skins/`` (ver la skill ``skin-pixel-art``).

La mascota es **estática**: cada estado es un cuadro fijo que se escala una sola vez
por tamaño y queda en caché. En reposo no se usa CPU.
"""

import json
from functools import lru_cache

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QImage, QPixmap

from ..log import get_logger
from ..rutas import ASSETS_DIR

log = get_logger("pandex.personajes")

CARPETA = ASSETS_DIR / "personajes"
POR_DEFECTO = "rusty"
ESTADOS = ("idle", "feliz", "trabajando", "error")
FONDO_LOGO = ("#4A7FBA", "#244A75")


class Personaje:
    def __init__(self, ident, datos, carpeta):
        self.id = ident
        self.nombre = str(datos.get("nombre") or ident)
        self.autor = str(datos.get("autor") or "")
        self.orden = int(datos.get("orden", 50))
        self.hoja_ruta = carpeta / "spritesheet.png"
        self.icono = carpeta / "icono.ico"
        self.cuadro = tuple(int(v) for v in datos.get("cuadro", (192, 208)))
        cuadros = datos.get("cuadros") or {}
        self.cuadros = {e: int(cuadros.get(e, cuadros.get("idle", 0))) for e in ESTADOS}
        self.recorte = QRect(*_caja(datos.get("recorte"), self.cuadro))
        self.cabeza_caja = QRect(*_caja(datos.get("cabeza"), self.cuadro))
        fondo = datos.get("fondo_logo") or FONDO_LOGO
        self.fondo_logo = (str(fondo[0]), str(fondo[-1]))

    def __repr__(self):
        return f"<Personaje {self.id}>"


def _caja(valor, cuadro):
    try:
        x, y, w, h = (int(v) for v in valor)
        return x, y, w, h
    except (TypeError, ValueError):
        return 0, 0, cuadro[0], cuadro[1]


@lru_cache(maxsize=1)
def catalogo():
    """``{id: Personaje}`` de los que tienen su sprite sheet, en orden."""
    encontrados = []
    for json_ in sorted(CARPETA.glob("*/personaje.json")):
        carpeta = json_.parent
        if not (carpeta / "spritesheet.png").exists():
            continue
        try:
            datos = json.loads(json_.read_text(encoding="utf-8"))
            encontrados.append(Personaje(carpeta.name, datos, carpeta))
        except (OSError, ValueError, TypeError) as exc:
            log.warning("personaje %s ignorado: %s", carpeta.name, exc)
    encontrados.sort(key=lambda p: (p.orden, p.nombre.lower()))
    return {p.id: p for p in encontrados}


def lista():
    """``[(id, nombre)]`` para un combo."""
    return [(p.id, p.nombre) for p in catalogo().values()]


def existe(ident):
    return ident in catalogo()


def elegir(ident):
    """El personaje pedido o, si no está, Rusty (o el primero que haya)."""
    todos = catalogo()
    if ident in todos:
        return todos[ident]
    return todos.get(POR_DEFECTO) or next(iter(todos.values()), None)


@lru_cache(maxsize=8)
def _hoja(ident):
    p = catalogo().get(ident)
    if p is None:
        return None
    hoja = QImage(str(p.hoja_ruta))
    if hoja.isNull():
        log.error("no pude leer %s", p.hoja_ruta)
        return None
    return hoja.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)


def _cuadro(p, indice, caja):
    hoja = _hoja(p.id)
    if hoja is None:
        return QImage()
    return hoja.copy(caja.translated(indice * p.cuadro[0], 0))


def tamano(ident, alto):
    """Tamaño de la ventana para ese alto, con la proporción del personaje."""
    p = elegir(ident)
    if p is None:
        return max(24, int(alto)), max(24, int(alto))
    r = p.recorte
    return max(24, round(alto * r.width() / r.height())), max(24, int(alto))


def _escalar(img, ancho, alto):
    # al ampliar 2× o más, sin suavizar (píxeles nítidos); al reducir, suavizado
    # para no perder detalle del dibujo
    modo = (Qt.TransformationMode.FastTransformation if alto >= img.height() * 2
            else Qt.TransformationMode.SmoothTransformation)
    return img.scaled(ancho, alto, Qt.AspectRatioMode.KeepAspectRatio, modo)


@lru_cache(maxsize=24)
def _imagen(ident, estado, alto, dpr):
    p = elegir(ident)
    ancho, alto_ = tamano(ident, alto)
    if p is None:
        pix = QPixmap(round(ancho * dpr), round(alto_ * dpr))
        pix.fill(Qt.GlobalColor.transparent)
    else:
        cuadro = _cuadro(p, p.cuadros[estado], p.recorte)
        pix = QPixmap.fromImage(_escalar(cuadro, round(ancho * dpr), round(alto_ * dpr)))
    pix.setDevicePixelRatio(dpr)
    return pix


def imagen(ident, estado, alto, dpr=1.0):
    """El personaje listo para pintar (``QPixmap`` con la escala de la pantalla), en caché.

    Ocupa como mucho ``alto`` píxeles lógicos; quien lo pinta lo centra.
    """
    if estado not in ESTADOS:
        estado = "idle"
    return _imagen(ident, estado, int(alto), round(float(dpr), 2))


@lru_cache(maxsize=8)
def cabeza(ident):
    """Solo la cabeza (para el logo), como ``QImage`` en su tamaño original."""
    p = elegir(ident)
    return QImage() if p is None else _cuadro(p, 0, p.cabeza_caja)


def ruta_icono(ident):
    """El ``.ico`` del personaje, o ``None`` si todavía no se generó."""
    p = elegir(ident)
    return p.icono if p is not None and p.icono.exists() else None
