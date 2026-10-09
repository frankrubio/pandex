"""Los personajes de Pandex: Rusty y los demás, cada uno en su carpeta.

Los que trae Pandex viven en ``assets/personajes/<id>/``; los que añades tú (desde
Configuración, ver ``pandex/personaje_nuevo.py``), en ``%LOCALAPPDATA%\\Pandex\\personajes``,
para que sobrevivan a las actualizaciones. Cada carpeta tiene:

- ``spritesheet.png``: los cuadros en fila, todos del mismo tamaño.
- ``personaje.json``: su nombre, qué cuadro usa cada estado, el recorte común (para
  que la figura no salte al cambiar de estado) y la cabeza (para el logo).
- ``icono.ico``: el ícono de la app con su cara (``herramientas/crear_icono.py``).

Para agregar uno basta con crear su carpeta: aparece solo en Configuración. Los
dibujos nuevos que se incluyen en Pandex se hacen con ``herramientas/skins/`` (ver la
skill ``skin-pixel-art``).

La mascota es **estática**: cada estado es un cuadro fijo que se escala una sola vez
por tamaño y queda en caché. En reposo no se usa CPU.
"""

import json
from functools import lru_cache

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QImage, QPixmap

from ..log import get_logger
from ..rutas import ASSETS_DIR, PERSONAJES_PROPIOS

log = get_logger("pandex.personajes")

CARPETA = ASSETS_DIR / "personajes"
POR_DEFECTO = "rusty"
ESTADOS = ("idle", "feliz", "trabajando", "error")
FONDO_LOGO = ("#4A7FBA", "#244A75")


class Personaje:
    def __init__(self, ident, datos, carpeta, propio=False):
        self.id = ident
        self.propio = propio  # lo añadiste tú: se puede quitar
        self.nombre = str(datos.get("nombre") or ident)
        self.autor = str(datos.get("autor") or "")
        self.orden = int(datos.get("orden", 50))
        self.hoja_ruta = carpeta / "spritesheet.png"
        self.icono = carpeta / "icono.ico"
        self.cuadro = tuple(int(v) for v in datos.get("cuadro", (192, 208)))
        cuadros = datos.get("cuadros") or {}
        self.cuadros = {e: int(cuadros.get(e, cuadros.get("idle", 0))) for e in ESTADOS}
        # opcional: {estado: {"cuadros": [i, …], "ms": 150}} para moverse mientras trabaja o reacciona
        self.animaciones = {}
        for estado, anim in (datos.get("animaciones") or {}).items():
            try:
                indices = [int(i) for i in anim["cuadros"]]
                if estado in ESTADOS and len(indices) > 1:
                    self.animaciones[estado] = (indices, max(60, int(anim.get("ms", 150))))
            except (KeyError, TypeError, ValueError):
                continue
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
    """``{id: Personaje}`` de los que tienen su sprite sheet, en orden.

    Si un personaje tuyo se llama igual que uno de Pandex, manda el de Pandex.
    """
    encontrados = {}
    for raiz, propio in ((CARPETA, False), (PERSONAJES_PROPIOS, True)):
        for json_ in sorted(raiz.glob("*/personaje.json")):
            carpeta = json_.parent
            if carpeta.name in encontrados or not (carpeta / "spritesheet.png").exists():
                continue
            try:
                datos = json.loads(json_.read_text(encoding="utf-8"))
                encontrados[carpeta.name] = Personaje(carpeta.name, datos, carpeta, propio)
            except (OSError, ValueError, TypeError) as exc:
                log.warning("personaje %s ignorado: %s", carpeta.name, exc)
    orden = sorted(encontrados.values(), key=lambda p: (p.orden, p.nombre.lower()))
    return {p.id: p for p in orden}


def recargar():
    """Después de añadir o quitar uno: vuelve a leer las carpetas y vacía las cachés."""
    for funcion in (catalogo, _hoja, _imagen, _animados, cabeza):
        funcion.cache_clear()


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


@lru_cache(maxsize=2)  # la hoja entera solo hace falta mientras se recortan sus cuadros
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


def ritmo(ident, estado):
    """Milisegundos por cuadro si ese estado tiene animación; si no, None."""
    p = elegir(ident)
    anim = p.animaciones.get(estado) if p else None
    return anim[1] if anim else None


@lru_cache(maxsize=6)
def _animados(ident, estado, alto, dpr):
    p = elegir(ident)
    ancho, alto_ = tamano(ident, alto)
    salida = []
    for indice in p.animaciones[estado][0]:
        pix = QPixmap.fromImage(_escalar(_cuadro(p, indice, p.recorte), round(ancho * dpr), round(alto_ * dpr)))
        pix.setDevicePixelRatio(dpr)
        salida.append(pix)
    return tuple(salida)


def cuadros(ident, estado, alto, dpr=1.0):
    """Los cuadros de la animación de ese estado (ya escalados, en caché), o ``()``."""
    if ritmo(ident, estado) is None:
        return ()
    return _animados(ident, estado, int(alto), round(float(dpr), 2))


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
