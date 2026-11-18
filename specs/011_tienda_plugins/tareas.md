# 011 · Tareas

## T011.1 · Pruebas y manifiestos

- **Requisitos:** PLG-01 a PLG-04
- **Depende de:** —
- **Prueba primero:** `tests/test_plugins.py`
- **Cambio:** módulo `pandex/plugins.py` y rutas `DATOS/plugins_*`.
- **Terminado cuando:**
  - [ ] las pruebas pasan;
  - [ ] el catálogo rechaza manifiestos inválidos;
  - [ ] no hay ejecución durante validación.

## T011.2 · Conservación personal

- **Requisitos:** PLG-05 a PLG-07
- **Depende de:** T011.1
- **Prueba primero:** `tests/test_residuos.py::DesinstalarConPluginsPersonales`
- **Cambio:** desinstalador, rutas y inventario.
- **Terminado cuando:**
  - [ ] desinstalar conserva personales por defecto;
  - [ ] el borrado exige opción o confirmación;
  - [ ] actualización no los toca.

## T011.3 · Tienda de escritorio

- **Requisitos:** PLG-08 a PLG-13
- **Depende de:** T011.1
- **Prueba primero:** pruebas de UI en `tests/test_ui.py`
- **Cambio:** página en Configuración y catálogo local.
- **Terminado cuando:**
  - [ ] búsqueda, detalles y permisos;
  - [ ] instalar/actualizar/desactivar/eliminar;
  - [ ] teclado y tema claro/oscuro.

## T011.4 · Manual y revisión

- **Requisitos:** PLG-08 y PLG-14
- **Depende de:** T011.3
- **Prueba primero:** revisión del checklist.
- **Cambio:** `docs/crear-plugins.md`, `docs/privacidad.md`, línea de changelog.
- **Terminado cuando:**
  - [ ] usuario puede crear y enviar;
  - [ ] Frank tiene lista eficiente de revisión;
  - [ ] aprobación sigue una sola persona.
