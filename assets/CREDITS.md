# Créditos de los recursos gráficos

Cada personaje vive en `personajes/<id>/`: `spritesheet.png`, `personaje.json` e `icono.ico`.

## Rusty, el panda rojo (personaje por defecto): `personajes/rusty/`

**Rusty** es obra de **LuoSKraD** y fue publicado en Codex Pets:
<https://codex-pets.net/share/rusty> · autor: <https://codex-pets.net/users/luoskrad>.
«A tiny red panda coding companion with a ringed tail».

El sprite sheet son los 6 cuadros de su GIF original, puestos en fila sin modificar
(`herramientas/gif_a_sprite.py`). Pandex usa un cuadro fijo por estado. Rusty es además la
referencia de estilo para los demás personajes (skill `.claude/skills/skin-pixel-art`).

## BMO: `personajes/bmo/`

Fan art **no oficial** de BMO, de *Hora de Aventura* (© Cartoon Network). Lo dibujó Claude
para Pandex en el estilo de Rusty (`herramientas/skins/bmo.py`). El personaje no es nuestro:
este dibujo **no está cubierto por la licencia MIT** del proyecto y solo está para uso
personal, sin fines comerciales.

## Robot: `personajes/robot/`

Redibujado pose por pose a partir de un sprite sheet que compartió el autor del proyecto
(`herramientas/skins/robot.py`).

## Panda robot (clásico): `personajes/panda_clasico/`

El personaje de Pandex 1.x, aportado por el autor del proyecto (imagen generada por IA).
Se procesó con `herramientas/preparar_sprite.py`: se quitó el fondo liso, se recortó y se
redujo a la mitad (346×355 px, un solo cuadro).

## Íconos: `personajes/<id>/icono.ico`, `pandex.ico`, `pandex_256.png`, `logo.png`

La cara de cada personaje sobre un squircle de color, dibujada en `pandex/ui/logo.py` y
exportada con `herramientas/crear_icono.py`. `pandex.ico`, `pandex_256.png` y `logo.png` son
los de Rusty, el logo por defecto.

## ¿Quieres otro personaje?

Mira «Personajes» en `docs/arquitectura.md`. Si usas mascotas de terceros (por ejemplo, de
Codex Pets u [OpenPets](https://openpets.dev)), revisa su licencia antes de redistribuirlas y
agrega aquí su atribución.
