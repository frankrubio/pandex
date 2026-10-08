"""Convierte una imagen suelta en un sprite listo para la mascota.

Le quita el fondo liso, lo recorta a la figura y lo guarda como PNG con
transparencia. Sirve para cualquier dibujo con fondo de un solo color.

    .venv\\Scripts\\python.exe herramientas/preparar_sprite.py entrada.webp assets/mi_panda/spritesheet.png

Opciones:
    --tolerancia N   qué tan distinto del fondo cuenta como fondo (por defecto 42)
    --margen N       píxeles transparentes que deja alrededor (por defecto 6)
    --escala N       divide el tamaño entre N (2 = mitad), por defecto 1

Importante: el fondo se borra por contagio desde los bordes, no por color. Así
los negros de adentro (orejas, contornos, ojos) NO se vuelven transparentes.
"""

import sys
from collections import deque
from pathlib import Path

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QApplication


def quitar_fondo(img, tolerancia=42):
    img = img.convertToFormat(QImage.Format.Format_ARGB32)
    ancho, alto = img.width(), img.height()

    esquinas = [(0, 0), (ancho - 1, 0), (0, alto - 1), (ancho - 1, alto - 1)]
    ref = [img.pixelColor(x, y) for x, y in esquinas]
    fondo = (
        sum(c.red() for c in ref) // 4,
        sum(c.green() for c in ref) // 4,
        sum(c.blue() for c in ref) // 4,
    )

    def es_fondo(x, y):
        c = img.pixelColor(x, y)
        return (
            abs(c.red() - fondo[0])
            + abs(c.green() - fondo[1])
            + abs(c.blue() - fondo[2])
        ) <= tolerancia

    visto = bytearray(ancho * alto)
    cola = deque()
    for x in range(ancho):
        for y in (0, alto - 1):
            if not visto[y * ancho + x] and es_fondo(x, y):
                visto[y * ancho + x] = 1
                cola.append((x, y))
    for y in range(alto):
        for x in (0, ancho - 1):
            if not visto[y * ancho + x] and es_fondo(x, y):
                visto[y * ancho + x] = 1
                cola.append((x, y))

    transparente = QColor(0, 0, 0, 0)
    while cola:
        x, y = cola.popleft()
        img.setPixelColor(x, y, transparente)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < ancho and 0 <= ny < alto:
                i = ny * ancho + nx
                if not visto[i] and es_fondo(nx, ny):
                    visto[i] = 1
                    cola.append((nx, ny))
    return img


def recortar(img, margen=6):
    ancho, alto = img.width(), img.height()
    izq, arr, der, aba = ancho, alto, -1, -1
    for y in range(alto):
        for x in range(ancho):
            if img.pixelColor(x, y).alpha() > 12:
                if x < izq: izq = x
                if x > der: der = x
                if y < arr: arr = y
                if y > aba: aba = y
    if der < izq:
        return img
    izq = max(0, izq - margen)
    arr = max(0, arr - margen)
    der = min(ancho - 1, der + margen)
    aba = min(alto - 1, aba + margen)
    return img.copy(QRect(izq, arr, der - izq + 1, aba - arr + 1))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = {a.split("=")[0]: a.split("=")[1] for a in sys.argv[1:] if "=" in a}
    if len(args) < 2:
        print(__doc__)
        return 1

    entrada, salida = Path(args[0]), Path(args[1])
    tolerancia = int(opts.get("--tolerancia", 42))
    margen = int(opts.get("--margen", 6))
    escala = int(opts.get("--escala", 1))

    _app = QApplication(sys.argv)  # QImage necesita una aplicación Qt viva
    img = QImage(str(entrada))
    if img.isNull():
        print(f"no pude leer {entrada}")
        return 1
    print(f"entrada : {img.width()}x{img.height()}")

    img = recortar(quitar_fondo(img, tolerancia), margen)
    if escala > 1:
        img = img.scaled(
            img.width() // escala, img.height() // escala,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    salida.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(salida))
    print(f"salida  : {img.width()}x{img.height()}  ->  {salida}")
    print("\nEn config.json pon frame_ancho y frame_alto con esas medidas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
