# Créditos de los recursos gráficos

## Rusty, el panda rojo (personaje por defecto): `rusty/spritesheet.png`

**Rusty** es obra de **LuoSKraD** y fue publicado en Codex Pets:
<https://codex-pets.net/share/rusty> · autor: <https://codex-pets.net/users/luoskrad>.
«A tiny red panda coding companion with a ringed tail».

El sprite sheet son los 6 cuadros de su GIF original, puestos en fila sin modificar
(`herramientas/gif_a_sprite.py`). Pandex usa un cuadro fijo por estado.

## Ícono de la app: `pandex.ico`, `pandex_256.png`, `logo.png`

La cara de Rusty (recortada del sprite de LuoSKraD) sobre un squircle azul. Se dibujan en `pandex/ui/dibujo.py → logo()` y se
exportan con `herramientas/crear_icono.py`.

## Panda robot

- **Vectorial** (`personaje: "vectorial"`): dibujado con QPainter en `pandex/ui/dibujo.py`.
- **Pixel art** (`personaje: "pixel"`, `panda_robot/spritesheet.png`): aportado por el autor
  del proyecto (imagen generada por IA). Se procesó con `herramientas/preparar_sprite.py`:
  se quitó el fondo liso, se recortó y se redujo a la mitad (346×355 px, un solo cuadro).

## ¿Quieres otro personaje?

Cualquier imagen o sprite sheet sirve; mira «Cambiar el personaje» en el README. Si usas
mascotas de terceros (por ejemplo, de Codex Pets u [OpenPets](https://openpets.dev)), revisa
su licencia antes de redistribuirlas y agrega aquí su atribución.
