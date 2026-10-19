# NNN · Tareas

Reglas: una tarea = un PR pequeño. **La prueba va primero** y debe fallar por el motivo
correcto antes de tocar el código. Al terminar, marca la casilla y actualiza
[../tablero.md](../tablero.md).

## TNNN.1 · Título en imperativo

- **Requisitos:** XXX-01
- **Depende de:** —
- **Prueba primero:** `tests/test_….py` → `test_…` (qué afirma, en una línea)
- **Cambio:** qué archivo y qué se hace, sin más.
- **Terminado cuando:**
  - [ ] la prueba nueva pasa y antes fallaba;
  - [ ] toda la suite pasa en Windows y en Linux (CI);
  - [ ] `CHANGELOG.md` tiene su línea si el usuario lo nota;
  - [ ] `docs/` actualizado si cambió el comportamiento.
