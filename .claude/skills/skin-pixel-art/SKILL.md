---
name: skin-pixel-art
description: Diseña un personaje (skin) nuevo para la mascota de Pandex en pixel art con el estilo y la calidad de Rusty, y lo deja instalado con su ícono. Úsala cuando pidan crear, añadir, redibujar o ajustar una skin, un personaje o una mascota, ya sea a partir de una imagen de referencia, de una descripción o de un sprite sheet.
---

# Skins de Pandex en el estilo de Rusty

Esta skill es para personajes que **se incluyen en Pandex** (`assets/personajes/`). Si Frank
solo quiere usar una imagen suya en su PC, sin dibujar nada, no hace falta: basta con
**Configuración → Apariencia → Añadir personaje…** (`pandex/personaje_nuevo.py`).

Rusty (`assets/personajes/rusty/`) es la referencia de calidad. Todo personaje nuevo
tiene que verse como de la misma familia que Rusty: mismo tamaño, mismo grosor de
contorno y el mismo cuidado en el sombreado.

## La regla de Frank

- **Por defecto, reinterpreta.** Una imagen de referencia (un dibujo, una captura,
  pixel art de otro estilo) se redibuja en el estilo de Rusty, no se copia. Conserva
  lo que hace reconocible al personaje (silueta, colores, rasgos) y adapta todo lo
  demás a las reglas de abajo.
- **Copia tal cual solo si Frank lo pide de forma explícita** ("tal cual", "igual
  que la imagen", "no lo cambies"), o si ya es un sprite sheet de 192×208 con estas
  mismas reglas. Si tienes el archivo, úsalo directo. Si solo ves la imagen en el
  chat, redibújalo pose por pose y avísale que, para tener los píxeles exactos,
  necesitas el PNG en el repositorio.
- Si no está claro cuál de los dos quiere, pregunta antes de dibujar.

## El estilo, medido en Rusty

| Regla | Valor |
|---|---|
| Cuadrícula | **48×52 píxeles de dibujo**, ampliados ×4 sin suavizar, dan cuadros de **192×208** |
| Ocupación | El personaje llena el cuadro con 1 o 2 píxeles de margen. Nada flota suelto. |
| Proporción | Chibi: la cabeza (o la parte con la cara) ocupa la mitad del alto o más. Patas cortas, pies visibles. |
| Contorno | 1 píxel, casi negro y teñido del color del personaje (Rusty: `#120E0C`; BMO: `#0F1A18`; Robot: `#1C2436`). Nunca negro puro ni gris. |
| Separación | Cada pieza encima de otra lleva su contorno (patas sobre el cuerpo, pantalla sobre la carcasa). |
| Sombreado | 3 o 4 tonos por material: luz (arriba e izquierda), base, sombra (abajo y derecha) y hondo (la última fila). La luz va más cálida y la sombra más fría (corrimiento de matiz), nunca solo más clara o más oscura. |
| Textura | Superficies grandes con 2 a 5 % de píxeles del tono vecino (pelo, plástico gastado). Superficies lisas (pantallas, metal pulido) sin textura. |
| Cara | Pequeña y tierna. Ojos de 2×3 o 3×3 con un píxel de brillo blanco arriba a la izquierda, boca de 2 a 6 píxeles. El rubor es opcional. |
| Paleta | Pocos colores por material y saturados sin chillar. El conjunto se tiene que leer sobre fondo claro **y** oscuro. |
| Estados | `idle` (de frente, contento), `trabajando` (concentrado: ojos entrecerrados o mirando a un lado), `feliz` (ojos cerrados `^ ^`, sonrisa grande) y `error` (preocupado: cejas inclinadas, boca ondulada; puede ser igual a `idle`, como en Rusty). |
| Coherencia | Entre poses no se mueve el cuerpo de lugar: solo cambian la cara, los brazos o 1 píxel de altura. La mascota es estática (un cuadro por estado), así que cada pose tiene que funcionar sola. |

## Cómo se hace

Todo el dibujo es código: es reproducible y se corrige por coordenadas.

1. **Mira la referencia y planifica en la cuadrícula de 48×52**: dónde va el cuerpo, la
   cara, los brazos y las patas. Define los materiales con colores sacados de la
   referencia.
2. **Escribe `herramientas/skins/<id>.py`** copiando la forma de `bmo.py` (un personaje
   reinterpretado) o de `robot.py` (copia fiel de un sprite sheet). El módulo define
   `ID`, `NOMBRE`, `AUTOR`, `ORDEN`, `POSES`, `ESTADOS`, `CABEZA` (lo que se ve en el
   logo, en la cuadrícula), `FONDO_LOGO`, `CONTORNO` y `dibujar(lienzo, pose)`.
   La librería está en `herramientas/skins/pixelart.py`:
   - Máscaras: `rect(x, y, w, h, r)`, `elipse(cx, cy, rx, ry)`, `linea`, `mover`, `espejo` (simetría).
   - `lienzo.parte(mascara, Material(...))`: contorno, sombreado y textura de una pieza.
   - `lienzo.pintar(mascara, color)` y `lienzo.punto(x, y, color)`: detalles planos (ojos, brillos).
   - Dibuja **de atrás hacia adelante**: patas y brazos, cuerpo, cabeza, cara.
3. **Construye y revisa**, sin la venv de Windows también sirve cualquier Python con
   PyQt6 y Pillow:
   ```
   python herramientas/skins/construir.py <id> --vista /tmp/vista.png
   ```
   Abre la vista y revisa las poses sobre fondo claro y oscuro, y la pose ampliada.
   Corrige y repite hasta que pase la lista de abajo. Esto escribe
   `assets/personajes/<id>/` (`spritesheet.png`, `personaje.json` y `icono.ico`).
4. **Revisa el logo**: el ícono a 256, 48 y 16 px tiene que reconocerse. Si la cara
   queda cortada o muy chica, ajusta `CABEZA`. Si se pierde contra el fondo, ajusta
   `FONDO_LOGO`.
5. **Integra**: el personaje aparece solo en Configuración (Personaje y Logo). Agrega su
   id a la lista de `test_cada_personaje_un_cuadro_fijo_por_estado`
   (`tests/test_ui.py`), su crédito en `assets/CREDITS.md` y una línea en `CHANGELOG.md`.
   Corre las pruebas:
   `QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -t .`
6. **Muestra el resultado** a Frank (la vista y los íconos) antes de dar el trabajo por cerrado.

## Lista de control antes de entregar

- [ ] Al lado de Rusty parece de la misma familia: mismo tamaño en pantalla, mismo contorno, mismo nivel de detalle.
- [ ] Contorno continuo de 1 píxel, sin huecos ni esquinas dobles.
- [ ] Cada material tiene luz, base y sombra visibles; no hay superficies planas grandes.
- [ ] Se lee bien sobre fondo claro y oscuro.
- [ ] Las 4 caras (`idle`, `trabajando`, `feliz`, `error`) se distinguen a 120 px.
- [ ] El ícono se reconoce a 16 px.
- [ ] Las pruebas pasan.
- [ ] Si es un personaje con derechos de autor (series, juegos), quedó anotado en `assets/CREDITS.md` como fan art no oficial, fuera de la licencia MIT.
