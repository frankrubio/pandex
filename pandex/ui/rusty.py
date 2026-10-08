"""Rusty, el panda rojo de Pandex, en pixel art.

Se arma en una cuadrícula pequeña (44×42 «píxeles») con figuras simples y un
contorno automático, y se amplía con un factor entero sin suavizar: cada píxel
queda nítido. Cada estado se arma una sola vez y queda en caché; la mascota no
anima nada, así que en reposo no usa CPU.
"""

from functools import lru_cache

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QImage, QPixmap

ANCHO, ALTO = 44, 42

PALETA = {
    "K": "#2A1308",  # contorno
    "O": "#D9561F",  # naranja
    "o": "#B9441A",  # naranja en sombra
    "L": "#EE7A34",  # naranja con luz
    "W": "#FCEBD0",  # crema
    "w": "#E8CCA0",  # crema en sombra
    "E": "#5B2A15",  # interior de la oreja
    "B": "#5A2414",  # patas y brazos
    "b": "#3D160B",  # patas en sombra
    "e": "#16100E",  # ojos, nariz, boca
    "s": "#FFFFFF",  # brillo de los ojos
    "T": "#F6AE45",  # anillos claros de la cola
    "t": "#C9521D",  # anillos oscuros de la cola
    "R": "#E35151",  # error
    "F": "#F08A8A",  # rubor
}

ESTADOS = ("idle", "feliz", "trabajando", "error")


class _Lienzo:
    def __init__(self):
        self.p = [[None] * ANCHO for _ in range(ALTO)]

    def punto(self, x, y, c):
        if 0 <= x < ANCHO and 0 <= y < ALTO:
            self.p[y][x] = c

    def elipse(self, cx, cy, rx, ry, c, sombra=None, desde=None):
        """``sombra``: color para la parte de abajo (desde la fila ``desde``)."""
        for y in range(ALTO):
            for x in range(ANCHO):
                if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1.0:
                    self.punto(x, y, sombra if sombra and desde is not None and y >= desde else c)

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.punto(x, y, c)

    def triangulo(self, a, b, c, color):
        def lado(p, q, r):
            return (p[0] - r[0]) * (q[1] - r[1]) - (q[0] - r[0]) * (p[1] - r[1])

        for y in range(ALTO):
            for x in range(ANCHO):
                pt = (x + 0.5, y + 0.5)
                d1, d2, d3 = lado(pt, a, b), lado(pt, b, c), lado(pt, c, a)
                if not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0)):
                    self.punto(x, y, color)

    def puntos(self, lista, c):
        for x, y in lista:
            self.punto(x, y, c)

    def contorno(self, color="K"):
        llenos = {(x, y) for y in range(ALTO) for x in range(ANCHO) if self.p[y][x]}
        for x, y in list(llenos):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                v = (x + dx, y + dy)
                if v not in llenos and 0 <= v[0] < ANCHO and 0 <= v[1] < ALTO:
                    self.p[v[1]][v[0]] = color


def _cola(l):
    """Cola anillada que sube por la derecha, detrás del cuerpo."""
    camino = [(31, 34), (33, 33), (35, 31.5), (37, 29.5), (38.5, 27), (39.5, 24.5), (40, 22), (40, 19.5)]
    for i, (x, y) in enumerate(camino):
        anillo = "T" if (i // 2) % 2 == 0 else "t"
        r = 3.4 if i < len(camino) - 1 else 3.0
        l.elipse(x, y, r, r, anillo)
    l.elipse(40, 18.6, 2.4, 2.0, "t")  # la punta, oscura


def _cuerpo(l, estado):
    # patas
    l.rect(14, 34, 19, 39, "B")
    l.rect(23, 34, 28, 39, "B")
    l.rect(14, 38, 19, 39, "b")
    l.rect(23, 38, 28, 39, "b")
    l.puntos([(15, 39), (17, 39), (24, 39), (26, 39)], "o")
    # tronco
    l.elipse(21.5, 30, 9.5, 8, "O", sombra="o", desde=33)
    l.elipse(21.5, 28, 5.5, 4, "L")
    # brazos (feliz: saluda con el derecho)
    l.elipse(16.5, 32, 3.6, 3.8, "B")
    l.elipse(26.5, 32, 3.6, 3.8, "B")
    l.puntos([(15, 30), (25, 30)], "E")  # brillo en las patitas


def _cabeza(l):
    # orejas: crema por fuera, café por dentro
    l.triangulo((7, 12), (10, 1), (19, 7), "W")
    l.triangulo((36, 12), (33, 1), (24, 7), "W")
    l.triangulo((10, 10), (11.2, 4), (16, 7.5), "E")
    l.triangulo((33, 10), (31.8, 4), (27, 7.5), "E")
    # cráneo
    l.elipse(21.5, 16.5, 14, 11.5, "O", sombra="o", desde=24)
    l.elipse(21.5, 12, 8, 4, "L")
    # máscara crema: cejas, mejillas y hocico
    l.elipse(16, 11.6, 2.2, 1.3, "W")
    l.elipse(27, 11.6, 2.2, 1.3, "W")
    l.elipse(11.5, 21, 5.2, 4.2, "W")
    l.elipse(31.5, 21, 5.2, 4.2, "W")
    l.elipse(21.5, 22.4, 6.6, 4.8, "W", sombra="w", desde=25)
    # mechones a los lados de la cara
    l.puntos([(7, 18), (6, 19), (7, 20), (36, 18), (37, 19), (36, 20)], "O")


def _cara(l, estado):
    ojos = (15, 26)  # esquina izquierda de cada ojo (4×4)
    if estado == "feliz":                       # ^ ^
        for x in ojos:
            l.puntos([(x, 17), (x + 1, 16), (x + 2, 16), (x + 3, 17)], "e")
    elif estado == "error":                     # × ×
        for x in ojos:
            l.puntos([(x, 15), (x + 3, 15), (x + 1, 16), (x + 2, 16),
                      (x + 1, 17), (x + 2, 17), (x, 18), (x + 3, 18)], "e")
    elif estado == "trabajando":                # concentrado: párpados a media altura
        for x in ojos:
            l.rect(x, 16, x + 3, 18, "e")
            l.punto(x + 2, 16, "s")
            l.rect(x, 15, x + 3, 15, "o")
    else:                                       # ojos grandes con brillo
        for x in ojos:
            l.rect(x, 15, x + 3, 18, "e")
            l.punto(x + 2, 15, "s")
            l.punto(x + 2, 16, "s")
    # nariz
    l.rect(20, 20, 22, 20, "e")
    l.punto(21, 21, "e")
    # boca
    if estado == "feliz":
        l.rect(19, 23, 23, 23, "e")
        l.rect(20, 24, 22, 24, "e")
        l.punto(21, 24, "R")
    elif estado == "error":
        l.puntos([(19, 24), (20, 23), (21, 23), (22, 23), (23, 24)], "e")
    elif estado == "trabajando":
        l.rect(20, 23, 22, 23, "e")
    else:
        l.puntos([(19, 22), (20, 23), (21, 23), (22, 23), (23, 22)], "e")
    if estado != "error":                      # rubor
        l.puntos([(10, 21), (11, 21), (32, 21), (33, 21)], "F")


@lru_cache(maxsize=8)
def cuadricula(estado="idle"):
    """La figura como lista de filas de letras de ``PALETA`` (``None`` = transparente)."""
    l = _Lienzo()
    _cola(l)
    _cuerpo(l, estado)
    _cabeza(l)
    _cara(l, estado)
    l.contorno()
    return tuple(tuple(fila) for fila in l.p)


@lru_cache(maxsize=8)
def _base(estado):
    img = QImage(ANCHO, ALTO, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    colores = {k: QColor(v).rgba() for k, v in PALETA.items()}
    for y, fila in enumerate(cuadricula(estado)):
        for x, c in enumerate(fila):
            if c:
                img.setPixel(x, y, colores[c])
    return img


def factor(alto):
    """Ampliación entera más cercana al alto pedido: cada píxel, del mismo tamaño."""
    return max(1, round(alto / ALTO))


def tamano(alto):
    f = factor(alto)
    return ANCHO * f, ALTO * f


@lru_cache(maxsize=16)
def _imagen(estado, alto, dpr):
    # factor entero en píxeles físicos: con pantallas al 125 % o 150 % puede quedar
    # un poco más chico que la ventana, pero nunca borroso
    f = max(1, int(alto * dpr / ALTO + 1e-6))
    pix = QPixmap.fromImage(_base(estado).scaled(ANCHO * f, ALTO * f, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                 Qt.TransformationMode.FastTransformation))
    pix.setDevicePixelRatio(dpr)
    return pix


def imagen(estado, alto, dpr=1.0):
    """Rusty listo para pintar (``QPixmap`` con la escala de la pantalla), en caché.

    Ocupa como mucho ``alto`` píxeles lógicos; quien lo pinta lo centra.
    """
    if estado not in ESTADOS:
        estado = "idle"
    return _imagen(estado, int(alto), round(float(dpr), 2))


@lru_cache(maxsize=1)
def cabeza():
    """Solo la cabeza, recortada (para el logo), como ``QImage`` en la cuadrícula original."""
    l = _Lienzo()
    _cabeza(l)
    _cara(l, "idle")
    l.contorno()
    llenos = [(x, y) for y in range(ALTO) for x in range(ANCHO) if l.p[y][x]]
    x0, x1 = min(x for x, _ in llenos), max(x for x, _ in llenos)
    y0, y1 = min(y for _, y in llenos), max(y for _, y in llenos)
    img = QImage(x1 - x0 + 1, y1 - y0 + 1, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    for x, y in llenos:
        img.setPixel(x - x0, y - y0, QColor(PALETA[l.p[y][x]]).rgba())
    return img
