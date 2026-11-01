# 009 · Plan

## Enfoque

`pandex/canvas/reconectar.py` (sin Qt): `adaptar(params, nueva)` devuelve `(params_nuevos, informe)`
sin escribir nada. La ventana lo muestra, pide confirmación y recién entonces guarda.
No hace falta iniciar sesión en Canvas: los cursos se emparejan por el nombre de carpeta
que ya tiene cada regla (y su `nombre_canvas`/`alias`).

## Archivos que se tocan

| Archivo | Cambio |
|---|---|
| `pandex/canvas/reconectar.py` | nuevo |
| `pandex/ui/configuracion.py` | botón en la tarjeta de Canvas |
| `pandex/canvas/sincronizar.py` | el aviso de carpeta no encontrada menciona el botón |
| `tests/test_reconectar.py`, `tests/test_ui.py` | pruebas |
| `docs/sincronizar-canvas.md`, `CHANGELOG.md`, `pandex/__init__.py` | 2.5.2 |

## Riesgos

| Riesgo | Qué se hace |
|---|---|
| Emparejar mal un curso | Se muestra el resumen antes de guardar y queda copia de la configuración anterior. |
