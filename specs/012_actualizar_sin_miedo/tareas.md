# 012 · Tareas

## T012.1 · Confirmar, versiones publicadas con SHA-256 y volver atrás

- **Requisitos:** ACT-01 a ACT-06
- **Depende de:** —
- **Prueba primero:** `tests/test_actualizar.py`: `Confirmar`, `Publicadas`, `PuntoDeVuelta`,
  `VueltaAutomatica`; `tests/test_ui.py::test_actualizar_pide_confirmar_y_luego_reinicia`.
- **Cambio:** ver `plan.md`.
- **Terminado cuando:**
  - [x] pruebas en verde y antes fallaban;
  - [ ] la primera etiqueta publica la versión con su `.sha256` (CI);
  - [x] `docs/`, `README.md` y `CHANGELOG.md` al día.
