"""BMO, la consola de Hora de Aventura, en el estilo de Rusty.

Fan art no oficial: el personaje es de Cartoon Network (ver assets/CREDITS.md).
"""

from pixelart import Material, elipse, espejo, linea, rect

ID = "bmo"
NOMBRE = "BMO"
AUTOR = "Fan art de BMO (Hora de Aventura, © Cartoon Network), dibujado para Pandex"
ORDEN = 20
POSES = ["idle", "trabajando", "feliz", "error"]
ESTADOS = {"idle": "idle", "trabajando": "trabajando", "feliz": "feliz", "error": "error"}
CABEZA = (7, 2, 34, 24)          # la pantalla y el borde de la carcasa: lo que va en el logo
FONDO_LOGO = ("#3E4A63", "#1F2638")
CONTORNO = "#0F1A18"             # casi negro, con un toque del verde de BMO

CARCASA = Material("#6FC1AB", luz="#9ADBC7", sombra="#4E9E8C", hondo="#3A7C70", textura=0.03)
PANTALLA = Material("#C6EFD6", luz="#E2FAEA", sombra="#A3D9BD", hondo="#8DC8AB")
PIERNA = Material("#5FB29D", luz="#86CDB8", sombra="#438C7C", hondo="#356F63")
AMARILLO = Material("#F5C23A", luz="#FFE27A", sombra="#CF9420", hondo="#A9741A")
CIAN = Material("#3DBEE0", luz="#86E0F5", sombra="#2393B5", hondo="#1B7390")
VERDE = Material("#4BC95B", luz="#8BE88F", sombra="#2F9C40", hondo="#247A33")
ROJO = Material("#E2483C", luz="#FF8072", sombra="#B22F28", hondo="#8C221E")
GRIS = Material("#56656A", luz="#7B8B8F", sombra="#3E4B4F", hondo="#30393C")

OSCURO = "#0F1A18"
BLANCO = "#FFFFFF"
BOCA = "#2C6450"
LENGUA = "#F08C8C"
RUBOR = "#F2A39A"
BRILLO = "#F4FFF8"


def _brazos(lienzo, pose):
    if pose == "feliz":  # brazos arriba
        izq = rect(4, 11, 4, 11, r=2)
    elif pose == "error":  # pegados al cuerpo
        izq = rect(5, 25, 4, 9, r=2)
    else:
        izq = rect(4, 23, 4, 10, r=2)
    lienzo.parte(izq, CARCASA)
    lienzo.parte(espejo(izq), CARCASA)


def _piernas(lienzo):
    for x in (15, 30):
        lienzo.parte(rect(x, 42, 3, 5), PIERNA, sombra=0)
    pie = rect(13, 46, 6, 3, r=1)
    lienzo.parte(pie, PIERNA, sombra=1)
    lienzo.parte(mover_x(pie, 16), PIERNA, sombra=1)


def mover_x(mascara, dx):
    return {(x + dx, y) for x, y in mascara}


def _botones(lienzo):
    # ranura y parlante
    lienzo.pintar(linea(13, 26, 21, 26), OSCURO)
    for x in (31, 33, 35):
        lienzo.punto(x, 26, CARCASA.hondo)
    # cruceta amarilla
    cruz = rect(12, 31, 9, 3) | rect(15, 28, 3, 9)
    lienzo.parte(cruz, AMARILLO, sombra=1)
    # triángulo cian
    tri = {(25, 28), (24, 29), (25, 29), (26, 29), (23, 30), (24, 30), (25, 30), (26, 30), (27, 30)}
    lienzo.parte(tri, CIAN, sombra=1)
    # botón verde chico y botón rojo grande
    lienzo.parte(rect(34, 28, 2, 2), VERDE, sombra=1)
    lienzo.parte(elipse(31, 35, 2.5, 2.5), ROJO, sombra=1)
    lienzo.punto(30, 34, ROJO.luz)
    # botón gris alargado
    lienzo.parte(rect(22, 36, 4, 2), GRIS, sombra=1)


def _cara(lienzo, pose):
    ojos = {"izq": 16, "der": 29}
    if pose == "feliz":
        for x in ojos.values():  # ojos cerrados de felicidad: ^ ^
            lienzo.pintar({(x, 15), (x + 1, 14), (x + 2, 15)}, OSCURO)
        boca = [(20, 27, OSCURO, None), (20, 27, None, BLANCO), (21, 26, None, BOCA),
                (22, 25, None, LENGUA), (23, 24, OSCURO, None)]
        for fila, (a, b, borde, relleno) in enumerate(boca, start=18):
            if relleno:
                lienzo.punto(a, fila, OSCURO)
                lienzo.punto(b, fila, OSCURO)
                lienzo.pintar(linea(a + 1, fila, b - 1, fila), relleno)
            else:
                lienzo.pintar(linea(a, fila, b, fila), borde)
        for x in (14, 15, 32, 33):
            lienzo.punto(x, 17, RUBOR)
        return

    alto = 2 if pose == "trabajando" else 3
    y0 = 14 if pose == "trabajando" else 13
    for x in ojos.values():
        lienzo.pintar(rect(x, y0, 3, alto), OSCURO)
        lienzo.punto(x, y0, BLANCO)

    if pose == "trabajando":
        lienzo.pintar(linea(22, 19, 25, 19), OSCURO)
        # barra de carga en la pantalla
        lienzo.pintar(linea(15, 22, 32, 22), PANTALLA.hondo)
        lienzo.pintar(linea(15, 22, 25, 22), BOCA)
        return
    if pose == "error":
        lienzo.pintar({(15, 12), (16, 12), (17, 11)}, OSCURO)            # cejas preocupadas
        lienzo.pintar({(30, 11), (31, 12), (32, 12)}, OSCURO)
        lienzo.pintar({(21, 20), (22, 19), (23, 20), (24, 19), (25, 20), (26, 19)}, OSCURO)
        lienzo.pintar({(34, 10), (33, 11), (34, 11), (34, 12)}, "#8FD8F0")  # gota de sudor
        lienzo.punto(34, 12, "#5DB8DA")
        return
    # idle: sonrisa abierta
    lienzo.pintar(linea(21, 18, 26, 18), OSCURO)
    lienzo.punto(21, 19, OSCURO)
    lienzo.punto(26, 19, OSCURO)
    lienzo.pintar(linea(22, 19, 25, 19), BLANCO)
    lienzo.punto(22, 20, OSCURO)
    lienzo.punto(25, 20, OSCURO)
    lienzo.pintar(linea(23, 20, 24, 20), BOCA)
    lienzo.pintar(linea(23, 21, 24, 21), OSCURO)
    for x in (14, 15, 32, 33):
        lienzo.punto(x, 17, RUBOR)


def dibujar(lienzo, pose):
    _piernas(lienzo)
    _brazos(lienzo, pose)
    lienzo.parte(rect(8, 3, 32, 40, r=3), CARCASA)
    lienzo.parte(rect(12, 7, 24, 17, r=2), PANTALLA, sombra=1)
    lienzo.pintar({(14, 9), (15, 9), (14, 10)}, BRILLO)  # reflejo de la pantalla
    _botones(lienzo)
    _cara(lienzo, pose)
