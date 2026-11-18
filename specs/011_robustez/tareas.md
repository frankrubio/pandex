# 011 · Tareas

## T011.1 · Red de seguridad: errores inesperados y configuración dañada

- **Requisitos:** ROB-01, ROB-02, ROB-03, ROB-04, ROB-07
- **Depende de:** —
- **Prueba primero:** `tests/test_robustez.py` (`ErroresInesperados`, `ConfiguracionDanada`,
  `ArranqueFallido`) y `tests/test_nucleo.py::Ganchos`.
- **Cambio:** `pandex/errores.py`, `pandex/config.py`, `main.py`, `pandex/app.py`.
- **Terminado cuando:**
  - [x] las pruebas nuevas pasan y antes fallaban;
  - [ ] toda la suite pasa en Windows y en Linux (CI);
  - [x] `CHANGELOG.md` y `docs/` al día.

## T011.2 · Cancelar una tarea y salir limpio

- **Requisitos:** ROB-05, ROB-06
- **Depende de:** T011.1
- **Prueba primero:** `tests/test_robustez.py::Cancelar`.
- **Cambio:** `pandex/tareas.py`, `pandex/ejecutor.py`, `pandex/app.py` y los bucles de
  `pandex/canvas/` y `pandex/markdown/`.
- **Terminado cuando:**
  - [x] las pruebas nuevas pasan y antes fallaban;
  - [x] probado con un proceso real en Linux: una tarea que coopera cierra limpio; una que no
        responde ya no cuelga a Pandex ni hace que Qt aborte;
  - [ ] toda la suite pasa en Windows y en Linux (CI);
  - [x] `CHANGELOG.md` y `docs/` al día.
