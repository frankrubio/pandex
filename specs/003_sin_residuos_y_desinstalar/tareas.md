# 003 · Tareas

## T003.1 · La prueba que vigila los residuos

- **Requisitos:** RES-01
- **Depende de:** —
- **Prueba primero:** `tests/test_residuos.py::Residuos::test_nada_fuera_de_lugares_permitidos`
  con los flujos: configurar Canvas (falso), sincronizar, crear acceso directo, activar y
  desactivar despertador (con `subprocess` simulado).
- **Cambio:** solo la prueba y su ayudante `foto(carpeta) -> dict`. Si hoy ya falla por un
  residuo real, se marca ese caso con `@unittest.expectedFailure` y una referencia a la tarea
  que lo arregla (p. ej. `# T003.3`).
- **Terminado cuando:** la prueba corre en Windows y Linux en la CI.

## T003.2 · pip sin caché, en un solo lugar

- **Requisitos:** RES-02
- **Depende de:** —
- **Prueba primero:** `tests/test_residuos.py::test_pip_sin_cache`: todo `pip install` en
  `instalar.sh`, `instalar.bat` y `pandex/**/*.py` va con `--no-cache-dir` o bajo
  `PIP_NO_CACHE_DIR=1`; y `pandex.paquetes.instalar` pasa la opción (se simula `subprocess.run`).
- **Cambio:** `pandex/paquetes.py`; `extras.py` y `actualizar.py` lo usan; instaladores exportan
  `PIP_NO_CACHE_DIR=1`.
- **Terminado cuando:** prueba en verde; `CHANGELOG.md`: «Instalar y actualizar ya no dejan
  copias de paquetes fuera de la carpeta de Pandex».

## T003.3 · Drivers y navegadores en la carpeta de datos

- **Requisitos:** RES-03
- **Depende de:** —
- **Prueba primero:** `test_drivers_en_datos`: al llamar a `firefox.abrir` (con `webdriver`
  simulado), `os.environ["SE_CACHE_PATH"]` es `DATOS/navegadores`; al abrir Playwright,
  `PLAYWRIGHT_BROWSERS_PATH` también.
- **Cambio:** `rutas.NAVEGADORES`; `firefox.py`, `sesion.py`, `instalar.bat`.
- **Terminado cuando:** prueba en verde; la «Ayuda» explica cómo borrar `~/.cache/selenium`
  de versiones anteriores.

## T003.4 · Límites para respaldos y copias

- **Requisitos:** RES-04, RES-05, RES-11
- **Depende de:** —
- **Prueba primero:** `test_respaldos_con_limite` (5 respaldos → quedan los 2 más nuevos),
  `test_copias_de_config_con_limite` (5 → 3), `test_limites_documentados` (cada carpeta de
  `DATOS` que crece aparece en la tabla de `docs/arquitectura.md` con su límite).
- **Cambio:** `rutas.limitar()`; llamarlo en `actualizar.py` y `canvas/asistente.py`; revisar
  R8 (`reordenamientos/`, `rclone-*.log`) y ponerles límite si no tienen.
- **Terminado cuando:** pruebas en verde.

## T003.5 · Quitar paquetes huérfanos al actualizar

- **Requisitos:** RES-06
- **Depende de:** T003.2
- **Prueba primero:** `test_actualizar_quita_huerfanos`: con `pip freeze` simulado que incluye
  un paquete que ningún requirements pide, se llama a `pip uninstall -y` con ese paquete y no
  con `pip`/`setuptools`/`wheel`.
- **Cambio:** `pandex/paquetes.huerfanos()`; `actualizar.instalar_dependencias` lo usa.
- **Terminado cuando:** prueba en verde.

## T003.6 · Inventario de lo creado fuera

- **Requisitos:** RES-10
- **Depende de:** —
- **Prueba primero:** `test_inventario_registra_accesos_y_despertador`: crear acceso directo,
  arranque automático y despertador (simulados) deja 3 entradas en `DATOS/inventario.json`;
  quitarlos las borra.
- **Cambio:** `pandex/inventario.py`; llamadas en `accesos.py`, `despertador.py`,
  `onedrive.py`, `firefox.py`.
- **Terminado cuando:** prueba en verde.

## T003.7 · Desinstalar Pandex

- **Requisitos:** RES-07, RES-08, RES-09
- **Depende de:** T003.6
- **Prueba primero:** `tests/test_residuos.py::Desinstalar`
  - `test_desinstalar_quita_todo_lo_inventariado` (HOME temporal con todo creado → tras
    desinstalar, la foto es igual a la de antes de instalar, salvo la carpeta del proyecto y
    la de cursos);
  - `test_desinstalar_no_toca_la_carpeta_de_cursos`;
  - `test_desinstalar_pide_confirmacion` (sin confirmar, no borra nada);
  - `test_desinstalar_puede_conservar_config`.
- **Cambio:** `pandex/desinstalar.py`, `desinstalar.sh`, `desinstalar.bat`, botón en
  Configuración, sección «Desinstalar» en README y `docs/linux.md`.
- **Terminado cuando:** pruebas en verde; prueba manual en Windows y Linux anotada en el PR.
