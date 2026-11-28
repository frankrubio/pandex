# 015 · Tareas

Reglas: una tarea = un PR pequeño. **La prueba va primero** y debe fallar por el motivo
correcto antes de tocar el código. Al terminar, marca la casilla y actualiza
[../tablero.md](../tablero.md).

## T015.1 · Descargas completas, opción de repetidos por semana, material adicional y Google Drive

- **Requisitos:** DES-01, DES-02, DES-03, DES-04, DES-05, DES-06
- **Depende de:** —
- **Prueba primero:** `tests/test_descargas_canvas.py` → pruebas de `DES-01` a `DES-06` (fallan antes del cambio).
- **Cambio:** `pandex/canvas/{drive,cliente,estructura,destinos,historial,sincronizar,sesion,asistente}.py`, `pandex/ui/configuracion.py`, `pandex/markdown/clasificador.py` y `pandex/red.py`.
- **Terminado cuando:**
  - [x] la prueba nueva pasa y antes fallaba;
  - [x] toda la suite pasa en Windows y en Linux (CI);
  - [x] `CHANGELOG.md` tiene su línea y se subió la versión en `pandex/__init__.py`;
  - [x] `docs/` actualizado.
