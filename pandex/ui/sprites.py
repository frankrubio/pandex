"""Corta un sprite sheet en frames y devuelve el que toca según el estado.

Formato del sheet: una grilla regular de frames (p. ej. frames de 192x208).
Cada estado de la mascota apunta a una lista de [fila, columna] en config.json,
así puedes recomponer las animaciones sin tocar código.
"""

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QImage, QPixmap

from ..log import get_logger
from ..rutas import RAIZ

log = get_logger("pandex.sprites")

MUESTREO = 4  # paso en píxeles al calcular el recorte; suficiente y rápido


class Sprites:
    def __init__(self, cfg):
        self.ok = False
        self._cache = {}

        archivo = (cfg or {}).get("archivo")
        if not archivo:
            return

        ruta = RAIZ / archivo
        if not ruta.exists():
            log.warning("no encuentro el spritesheet %s", ruta)
            return

        self.hoja = QImage(str(ruta))
        if self.hoja.isNull():
            log.error("no pude leer el spritesheet %s", ruta)
            return

        self.fw = int(cfg.get("frame_ancho", 192))
        self.fh = int(cfg.get("frame_alto", 208))
        self.cols = self.hoja.width() // self.fw
        self.filas = self.hoja.height() // self.fh
        self.animaciones = cfg.get("animaciones", {})
        # nearest conserva el pixel art cuando la reducción es leve; con
        # dibujos grandes (>2x de reducción) el suavizado se ve mejor
        self.suavizado = bool(cfg.get("suavizado", False))
        if not self.animaciones or not self.cols or not self.filas:
            log.warning("spritesheet sin animaciones utilizables")
            return

        self.recorte = self._calcular_recorte(cfg.get("recortar_margen", True))
        self.ok = True
        log.info(
            "spritesheet %s: %dx%d frames, recorte %dx%d",
            ruta.name, self.cols, self.filas,
            self.recorte.width(), self.recorte.height(),
        )

    # ---------- geometría ----------

    def _frames_usados(self):
        vistos = []
        for anim in self.animaciones.values():
            for fila, col in anim.get("frames", []):
                if 0 <= fila < self.filas and 0 <= col < self.cols:
                    vistos.append((fila, col))
        return vistos or [(0, 0)]

    def _calcular_recorte(self, recortar):
        """Caja que abarca a la mascota en TODOS los frames que se usan.

        Es una caja común, no una por frame, para que el personaje no salte
        entre poses. Sin esto la ventana queda llena de margen transparente.
        """
        completo = QRect(0, 0, self.fw, self.fh)
        if not recortar:
            return completo

        izq, arr = self.fw, self.fh
        der = aba = 0
        for fila, col in self._frames_usados():
            ox, oy = col * self.fw, fila * self.fh
            for y in range(0, self.fh, MUESTREO):
                for x in range(0, self.fw, MUESTREO):
                    if self.hoja.pixelColor(ox + x, oy + y).alpha() > 16:
                        izq, der = min(izq, x), max(der, x)
                        arr, aba = min(arr, y), max(aba, y)

        if der <= izq or aba <= arr:
            return completo

        margen = MUESTREO * 2
        izq = max(0, izq - margen)
        arr = max(0, arr - margen)
        der = min(self.fw, der + margen)
        aba = min(self.fh, aba + margen)
        return QRect(izq, arr, der - izq, aba - arr)

    def tamano_ventana(self, alto):
        """La ventana sigue la proporción del recorte, sin espacio muerto."""
        ancho = round(alto * self.recorte.width() / self.recorte.height())
        return max(24, ancho), max(24, int(alto))

    # ---------- frames ----------

    def _pixmap(self, fila, col, ancho, alto):
        clave = (fila, col, ancho, alto)
        if clave in self._cache:
            return self._cache[clave]

        recorte = QRect(
            col * self.fw + self.recorte.x(),
            fila * self.fh + self.recorte.y(),
            self.recorte.width(),
            self.recorte.height(),
        )
        modo = (
            Qt.TransformationMode.SmoothTransformation
            if self.suavizado
            else Qt.TransformationMode.FastTransformation
        )
        pix = QPixmap.fromImage(self.hoja.copy(recorte)).scaled(
            ancho, alto, Qt.AspectRatioMode.KeepAspectRatio, modo
        )
        self._cache[clave] = pix
        return pix

    def _anim(self, estado):
        return self.animaciones.get(estado) or self.animaciones.get("idle")

    def frame(self, estado, t, ancho, alto):
        anim = self._anim(estado)
        frames = anim.get("frames") if anim else None
        if not frames:
            return None
        fps = float(anim.get("fps", 2) or 2)
        fila, col = frames[int(t * fps) % len(frames)]
        return self._pixmap(fila, col, ancho, alto)

    def tiene(self, estado):
        return estado in self.animaciones

    def cuadros(self, estado):
        """Cuántas poses distintas tiene ese estado (1 = imagen fija)."""
        anim = self._anim(estado)
        return len({tuple(f) for f in (anim or {}).get("frames", [])}) or 1

    def icono(self, lado):
        anim = self._anim("idle")
        fila, col = (anim.get("frames") or [[0, 0]])[0]
        return self._pixmap(fila, col, lado, lado)
