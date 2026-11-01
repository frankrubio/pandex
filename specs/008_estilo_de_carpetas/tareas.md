# 008 · Tareas

## T008.1 · Estilo de carpetas (`_` por defecto, o el tuyo)

- **Requisitos:** EST-01 a EST-06
- **Depende de:** —
- **Prueba primero:** `tests/test_estilo_carpetas.py` (`GuionesBajos`, `EstiloPropio`,
  `CarpetaDeCurso`, `Estilo`, `Asistente`).
- **Cambio:** ver plan.
- **Terminado cuando:**
  - [x] las pruebas nuevas pasan y antes fallaban;
  - [ ] toda la suite pasa en Windows y Linux (CI);
  - [x] `CHANGELOG.md` y `docs/` al día.

## T008.2 · Aplicar una configuración de Canvas ya escrita

- **Requisitos:** EST-07
- **Depende de:** —
- **Prueba primero:** `tests/test_estilo_carpetas.py::AplicarConfig`
- **Cambio:** `herramientas/aplicar_config_canvas.py`.
- **Terminado cuando:**
  - [x] la prueba nueva pasa y antes fallaba;
  - [x] `docs/sincronizar-canvas.md` explica cómo usarla.
