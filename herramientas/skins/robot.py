"""Robot: un robot blanco con visor oscuro y detalles cian.

Copia fiel, pose por pose, del sprite sheet que compartió Frank (6 cuadros de 192×208,
el mismo formato que Rusty). Como ya venía en ese estilo, no se reinterpretó.
"""

from pixelart import Material, elipse, espejo, mover, rect

ID = "robot"
NOMBRE = "Robot"
AUTOR = "Sprite sheet compartido por Frank, redibujado para Pandex"
ORDEN = 30
POSES = ["idle", "trabajando", "salto", "feliz", "mirada", "saludo"]
ESTADOS = {"idle": "idle", "trabajando": "trabajando", "feliz": "feliz", "error": "idle"}
CABEZA = (5, 0, 38, 27)          # antena, cabeza y orejas
FONDO_LOGO = ("#3B4660", "#1C2233")
CONTORNO = "#1C2436"             # azul marino muy oscuro, no negro

BLANCO = Material("#F2F4F8", luz="#FFFFFF", sombra="#D5DBE5", hondo="#BCC4D2")
CIAN = Material("#35C6C4", luz="#7FE4E0", sombra="#22A0A3", hondo="#1A8086")
VISOR = Material("#1D2333", luz="#262E42", sombra="#181D2B", hondo="#141824")
PIERNA = Material("#2E354A", luz="#465068", sombra="#232939", hondo="#1C2130")

OJO = "#3FD6D2"
SOMBRA_SUELO = (20, 24, 36, 60)


def _cabeza(lienzo, pose, dy):
    # antena
    lienzo.parte(elipse(23.5, 2.5 + dy, 1.5, 1.5), CIAN, sombra=1)
    lienzo.pintar(rect(23, 5 + dy, 2, 2), CONTORNO)
    # orejas (detrás de la cabeza)
    oreja = rect(6, 13 + dy, 4, 8, r=1)
    lienzo.parte(oreja, CIAN, sombra=1)
    lienzo.parte(espejo(oreja), CIAN, sombra=1)
    # cabeza y visor
    lienzo.parte(rect(10, 7 + dy, 28, 19, r=4), BLANCO, sombra=3)
    lienzo.parte(rect(13, 10 + dy, 22, 12, r=3), VISOR, sombra=0)

    mira = 1 if pose == "trabajando" else -1 if pose == "mirada" else 0
    if pose == "feliz":  # ojos cerrados
        for x in (18, 28):
            lienzo.pintar(rect(x - 1, 14 + dy, 4, 1), OJO)
    else:
        for x in (18, 28):
            lienzo.pintar(rect(x + mira, 12 + dy, 2, 4), OJO)
            lienzo.pintar(rect(x + mira, 12 + dy, 2, 1), CIAN.luz)
    # sonrisa
    lienzo.pintar({(22, 17 + dy), (25, 17 + dy), (23, 18 + dy), (24, 18 + dy)}, OJO)


def _cuerpo(lienzo, pose):
    brazo = rect(10, 30, 3, 9, r=1)
    mano = rect(10, 39, 3, 2)
    lienzo.parte(brazo, BLANCO, sombra=1)
    lienzo.parte(mano, CIAN, sombra=1)
    if pose == "saludo":  # el brazo derecho se abre
        brazo_der = {(35 + (y - 30) // 4 + i, y) for y in range(30, 39) for i in range(3)}
        lienzo.parte(brazo_der, BLANCO, sombra=1)
        lienzo.parte(mover(rect(37, 39, 3, 2), 1, 0), CIAN, sombra=1)
    else:
        lienzo.parte(espejo(brazo), BLANCO, sombra=1)
        lienzo.parte(espejo(mano), CIAN, sombra=1)
    for x in (17, 26):
        lienzo.parte(rect(x, 45, 5, 3, r=1), PIERNA, sombra=1)
    lienzo.parte(rect(15, 28, 18, 16, r=3), BLANCO, sombra=3)
    lienzo.parte(elipse(23.5, 35.5, 3.5, 3.5), CIAN, sombra=1)
    lienzo.parte(elipse(23.5, 35.5, 1.5, 1.5), VISOR, sombra=0, contorno=False)


def dibujar(lienzo, pose):
    lienzo.pintar(elipse(23.5, 50, 10, 1), SOMBRA_SUELO)
    _cuerpo(lienzo, pose)
    dy = {"trabajando": 1, "salto": -1}.get(pose, 0)
    _cabeza(lienzo, pose, dy)
