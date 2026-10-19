# 007 · Tareas

## T007.1 · Contrato y mapa verificados ✅

- **Requisitos:** EXT-01, EXT-02, EXT-03
- **Hecho:** `tests/test_principios.py` (clases `Tareas` y `Documentacion`) y la fila de
  `pandex/comprimir.py` en `docs/arquitectura.md`.

## T007.2 · Generador de tareas

- **Requisitos:** EXT-04
- **Depende de:** —
- **Prueba primero:** `tests/test_herramientas.py`
  - `test_nueva_tarea_crea_los_dos_archivos` (en una carpeta temporal);
  - `test_nueva_tarea_cumple_el_contrato` (la tarea generada pasa `Tareas::test_contrato`);
  - `test_nueva_tarea_no_pisa` (id existente → error y nada creado);
  - `test_id_invalido` (`Mi Tarea` → «Usa minúsculas y _, por ejemplo mi_tarea»).
- **Cambio:** `herramientas/nueva_tarea.py`; sección en `docs/crear-tareas.md`.
- **Terminado cuando:** pruebas en verde.

## T007.3 · Tareas documentadas

- **Requisitos:** EXT-05
- **Depende de:** —
- **Prueba primero:** `Documentacion::test_tareas_documentadas`: el `nombre` de cada tarea
  (salvo `ejemplo_saludo`) aparece en `README.md` o en algún `docs/*.md`.
- **Cambio:** «Comprimir carpeta» ya se añadió al README el 19/10/2026; falta solo la prueba.
- **Terminado cuando:** prueba en verde.

## T007.4 · Sin print y con estilo

- **Requisitos:** EXT-06, EXT-07
- **Depende de:** —
- **Prueba primero:** job `estilo` (`ruff check .`) y `test_sin_print`.
- **Cambio:** `pyproject.toml`; correcciones automáticas; `docs/convenciones.md` ya describe
  las reglas.
- **Terminado cuando:** el job pasa en la CI.

<!-- EXT-09 se cumple con T002.2 (extras en un solo lugar). -->

## T007.5 · Errores en los ganchos no tumban la app

- **Requisitos:** EXT-08
- **Depende de:** —
- **Prueba primero:** `tests/test_nucleo.py::test_error_en_preparar` y
  `test_error_en_configurar`.
- **Cambio:** solo si fallan (envolver los ganchos como ya se hace con `run`).
- **Terminado cuando:** pruebas en verde.
