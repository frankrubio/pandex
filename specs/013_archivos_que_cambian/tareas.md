# 013 · Tareas

## T013.1 · Bajar la versión corregida sin tocar la anterior

- **Requisitos:** CAM-01 a CAM-06
- **Depende de:** —
- **Prueba primero:** `tests/test_canvas_sincronizar.py::ArchivosQueCambian`.
- **Cambio:** `pandex/canvas/historial.py`, `pandex/canvas/sincronizar.py`,
  `docs/sincronizar-canvas.md`.
- **Terminado cuando:** pruebas en verde y antes fallaban; docs y CHANGELOG al día.
