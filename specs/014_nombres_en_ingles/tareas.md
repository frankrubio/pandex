# 014 · Tareas

Reglas: una tarea = un PR pequeño. **La prueba va primero** y debe fallar por el motivo
correcto antes de tocar el código. Al terminar, marca la casilla y actualiza
[../tablero.md](../tablero.md).

## T014.1 · Adaptar Pandex a nombres en inglés (semanas, cursos, mitades, secciones y clasificador)

- **Requisitos:** ING-01, ING-02, ING-03, ING-04, ING-05, ING-06
- **Depende de:** —
- **Prueba primero:** `tests/test_nombres_ingles.py` → pruebas de `ING-01` a `ING-06` (fallan antes del cambio).
- **Cambio:** `pandex/canvas/{nombres,estructura,destinos,adoptar,asistente,reconectar}.py` y `pandex/markdown/clasificador.py`.
- **Terminado cuando:**
  - [x] la prueba nueva pasa y antes fallaba;
  - [x] toda la suite pasa en Windows y en Linux (CI);
  - [x] `CHANGELOG.md` tiene su línea y se subió la versión en `pandex/__init__.py`;
  - [x] `docs/sincronizar-canvas.md` actualizado.
