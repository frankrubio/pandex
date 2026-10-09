"""Pixel art al estilo de Rusty: se dibuja en una cuadrícula chica y se amplía ×4.

Rusty mide 48×52 píxeles «de dibujo»; ampliados ×4 dan sus cuadros de 192×208. Esta
librería reproduce sus reglas para que cualquier personaje nuevo se vea igual de bien:

- **Contorno** de 1 píxel casi negro alrededor de cada parte (``Lienzo.parte``). Una
  parte dibujada encima de otra deja su contorno sobre la de abajo, y así se separan
  (las patas sobre el cuerpo, la pantalla sobre la carcasa…).
- **Tres tonos por material** (``Material``): luz arriba y a la izquierda, sombra abajo
  y a la derecha, y el tono base en medio. Los tonos se derivan solos del color base
  con un leve corrimiento de matiz (luz más cálida, sombra más fría), como hace el
  pixel art cuidado.
- **Textura** opcional: unos pocos píxeles del tono vecino, siempre los mismos (no
  cambian entre cuadros), para que las superficies grandes no se vean planas.

Todo es determinista: el mismo script produce siempre la misma imagen.
"""

import colorsys
import random

from PIL import Image

ESCALA = 4
ANCHO, ALTO = 48, 52  # × ESCALA = 192 × 208, el cuadro de Rusty
CONTORNO = "#120E0C"  # el de Rusty: casi negro, cálido


def rgba(color, alfa=255):
    if isinstance(color, tuple):
        return color if len(color) == 4 else (*color, alfa)
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4)) + (alfa,)


def ajustar(color, luz=0.0, sat=0.0, matiz=0.0):
    """El mismo color con otra luminosidad, saturación y matiz (fracciones de 0 a 1)."""
    r, g, b, a = rgba(color)
    h, brillo, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    h = (h + matiz) % 1.0
    brillo = min(1.0, max(0.0, brillo + luz))
    s = min(1.0, max(0.0, s + sat))
    r, g, b = colorsys.hls_to_rgb(h, brillo, s)
    return (round(r * 255), round(g * 255), round(b * 255), a)


class Material:
    """Los tonos de una superficie: ``luz``, ``base``, ``sombra`` y ``hondo`` (la sombra
    más oscura, para pliegues y la parte de abajo)."""

    def __init__(self, base, luz=None, sombra=None, hondo=None, textura=0.0):
        self.base = rgba(base)
        self.luz = rgba(luz) if luz else ajustar(base, luz=0.10, matiz=-0.015)
        self.sombra = rgba(sombra) if sombra else ajustar(base, luz=-0.13, sat=0.05, matiz=0.02)
        self.hondo = rgba(hondo) if hondo else ajustar(base, luz=-0.24, sat=0.05, matiz=0.035)
        self.textura = textura


# ---------- máscaras: conjuntos de (x, y) ----------


def rect(x, y, w, h, r=0):
    """Rectángulo con esquinas recortadas en escalera (``r`` = radio en píxeles)."""
    puntos = set()
    for j in range(h):
        for i in range(w):
            dx = max(r - i, i - (w - 1 - r), 0)
            dy = max(r - j, j - (h - 1 - r), 0)
            if r and dx and dy and dx * dx + dy * dy > r * r + r * 0.6:
                continue
            puntos.add((x + i, y + j))
    return puntos


def elipse(cx, cy, rx, ry):
    """Elipse centrada en (cx, cy); acepta medios píxeles para formas pares."""
    puntos = set()
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            if ((x - cx) / (rx + 0.25)) ** 2 + ((y - cy) / (ry + 0.25)) ** 2 <= 1.0:
                puntos.add((x, y))
    return puntos


def linea(x0, y0, x1, y1):
    puntos = set()
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        puntos.add((x0, y0))
        if (x0, y0) == (x1, y1):
            return puntos
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def mover(mascara, dx=0, dy=0):
    return {(x + dx, y + dy) for x, y in mascara}


def espejo(mascara, eje=ANCHO):
    """Refleja en horizontal (eje = el ancho del lienzo: simetría izquierda-derecha)."""
    return {(eje - 1 - x, y) for x, y in mascara}


def anillo(mascara):
    """El borde de 1 píxel que rodea a la máscara (vecinos en cruz, como Rusty)."""
    borde = set()
    for x, y in mascara:
        for vx, vy in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (vx, vy) not in mascara:
                borde.add((vx, vy))
    return borde


# ---------- el lienzo ----------


class Lienzo:
    def __init__(self, contorno=CONTORNO, ancho=ANCHO, alto=ALTO, semilla=7):
        self.ancho, self.alto = ancho, alto
        self.contorno = rgba(contorno)
        self.px = {}
        self._semilla = semilla

    def _dentro(self, x, y):
        return 0 <= x < self.ancho and 0 <= y < self.alto

    def pintar(self, mascara, color):
        """Relleno plano, sin contorno ni sombreado (detalles, brillos, ojos)."""
        c = rgba(color)
        for x, y in mascara:
            if self._dentro(x, y):
                self.px[(x, y)] = c

    def punto(self, x, y, color):
        self.pintar({(x, y)}, color)

    def borrar(self, mascara):
        for p in mascara:
            self.px.pop(p, None)

    def parte(self, mascara, material, contorno=True, luz=True, sombra=2, color_contorno=None):
        """Una pieza del personaje: contorno, tres tonos y textura.

        ``sombra`` = cuántas filas de abajo van en tono sombra (Rusty usa 2).
        """
        if contorno:
            self.pintar(anillo(mascara), color_contorno or self.contorno)
        azar = random.Random(self._semilla)
        ruido = {p: azar.random() for p in sorted(mascara)}
        for x, y in mascara:
            abajo = sum(1 for k in range(1, sombra + 1) if (x, y + k) not in mascara)
            if (x, y + 1) not in mascara and sombra:
                tono = material.hondo
            elif abajo or (x + 1, y) not in mascara:
                tono = material.sombra
            elif luz and ((x, y - 1) not in mascara or (x - 1, y) not in mascara):
                tono = material.luz
            else:
                tono = material.base
                if material.textura and ruido[(x, y)] < material.textura:
                    tono = material.luz if ruido[(x, y)] < material.textura / 2 else material.sombra
            if self._dentro(x, y):
                self.px[(x, y)] = tono

    def imagen(self, escala=ESCALA):
        img = Image.new("RGBA", (self.ancho, self.alto), (0, 0, 0, 0))
        for (x, y), color in self.px.items():
            img.putpixel((x, y), color)
        if escala != 1:
            img = img.resize((self.ancho * escala, self.alto * escala), Image.Resampling.NEAREST)
        return img
