# 003 · Sin residuos y desinstalación limpia

> Estado: aprobada  ·  Prefijo: `RES`  ·  Principios: P3, P2, P5

## Por qué

Pandex no debe desordenar la PC ni dejar archivos fuera de sus carpetas. Lo que crea con
permiso (accesos directos, despertador) tiene que poder quitarse, y lo que se acumula con el
uso tiene que tener límite. Hoy no hay desinstalador.

## Qué existe hoy (revisado el 19/10/2026 en el código)

Bien resuelto:

- Datos en una sola carpeta (`rutas.DATOS`); `PANDEX_DATOS` la redirige en las pruebas.
- `logs/pandex.log` rota al pasar 1 MB y guarda 3 copias (máximo ~4 MB).
- Temporales de descargas con más de 24 h se borran (`sincronizar._limpiar_temporales`).
- Accesos directos y despertador se pueden quitar desde Configuración.
- rclone usa su propio `rclone.conf` dentro de `DATOS`.

**Residuos encontrados:**

| # | Qué | Dónde queda | Origen |
|---|---|---|---|
| R1 | Caché de pip (cientos de MB tras instalar o actualizar) | `~/.cache/pip`, `%LOCALAPPDATA%\pip\Cache` | `instalar.sh`, `instalar.bat`, `extras.instalar`, `actualizar.instalar_dependencias` no usan `--no-cache-dir` |
| R2 | `geckodriver` que baja Selenium Manager | `~/.cache/selenium` | `canvas/firefox.py` no fija `SE_CACHE_PATH` |
| R3 | Chromium de Playwright (Windows sin Chrome) | `%LOCALAPPDATA%\ms-playwright` | `instalar.bat` no fija `PLAYWRIGHT_BROWSERS_PATH` |
| R4 | Respaldos de cada actualización, sin límite | `DATOS/respaldos/` | `actualizar._con_zip`, `limpiar_obsoletos` |
| R5 | Copias de configuración de Canvas, sin límite | `DATOS/config-canvas-anterior-*.json` | `canvas/asistente.py` |
| R6 | Paquetes que una versión nueva ya no usa siguen en `.venv` | `.venv` | `pip install` no desinstala lo que salió de `requirements.txt` |
| R7 | Sin desinstalador: quedan accesos, despertador, datos y perfil de snap | varios | — |
| R8 | Diarios de reordenamiento y registros de rclone: límite no verificado | `DATOS/reordenamientos/`, `DATOS/rclone-*.log` | por revisar |

## Requisitos

| Id | Requisito | Se comprueba con |
|---|---|---|
| RES-01 | Durante una sesión de pruebas completa, Pandex no crea ni modifica nada fuera de los lugares permitidos de `principios.md#p3`. | `tests/test_residuos.py::test_nada_fuera_de_lugares_permitidos` (HOME, `XDG_*`, `APPDATA` y `LOCALAPPDATA` apuntan a una carpeta temporal y se compara antes/después) |
| RES-02 | Ninguna llamada a `pip` deja caché (`--no-cache-dir` o `PIP_NO_CACHE_DIR=1`). | `test_pip_sin_cache` (lee los instaladores y busca cada `pip install` en el código) |
| RES-03 | Los drivers y navegadores que Pandex descarga quedan en `DATOS/navegadores/`. | `test_drivers_en_datos` |
| RES-04 | `DATOS/respaldos/` guarda como máximo los **2** últimos respaldos; los demás se borran solos. | `test_respaldos_con_limite` |
| RES-05 | `DATOS/config-canvas-anterior-*.json` guarda como máximo **3**. | `test_copias_de_config_con_limite` |
| RES-06 | Tras actualizar, `.venv` no tiene paquetes que ya no pide ningún `requirements*.txt` instalado. | `test_actualizar_quita_huerfanos` |
| RES-07 | Hay un desinstalador por sistema (`desinstalar.sh`, `desinstalar.bat`) y la opción **Configuración → Comportamiento → Desinstalar Pandex…**. | `test_desinstalar` + prueba manual |
| RES-08 | Desinstalar quita: accesos directos, arranque automático, despertador, carpeta de datos (incluye perfil del navegador, cookies e historial), perfil de snap, montajes de OneDrive de Pandex y `.venv`. **No** toca la carpeta de cursos ni tus archivos. | `test_desinstalar_quita_todo_lo_inventariado` |
| RES-09 | Antes de borrar, el desinstalador muestra la lista exacta de lo que va a quitar y pide confirmación. Ofrece conservar `config.json` (para reinstalar). | `test_desinstalar_pide_confirmacion` |
| RES-10 | Todo lo que Pandex crea fuera de la carpeta del proyecto y de `DATOS` queda anotado en `DATOS/inventario.json` (ruta, para qué, cuándo). El desinstalador usa ese inventario y, por si falta, las rutas conocidas. | `test_inventario_registra_accesos_y_despertador` |
| RES-11 | Todo lo que crece con el uso tiene límite documentado en `docs/arquitectura.md#dónde-vive-cada-dato`. | revisión + `test_residuos.py::test_limites_documentados` |

## Escenarios

**RES-01 · Una semana de uso**
- *Dado* un HOME vacío de pruebas
- *Cuando* se configura Canvas, se sincroniza, se convierte a Markdown, se crea el acceso
  directo y se actualiza
- *Entonces* los únicos cambios en HOME están en los lugares permitidos.

**RES-07 · Desinstalar**
- *Dado* Pandex instalado con acceso directo, arranque automático y despertador
- *Cuando* el usuario elige Desinstalar Pandex… y confirma
- *Entonces* no queda ninguno de esos, ni `DATOS`, ni `.venv`; la carpeta de cursos sigue
  igual; el mensaje final dice qué falta borrar a mano (la carpeta del proyecto, porque un
  programa no puede borrarse a sí mismo mientras corre) y cómo.

**Error · Algo no se pudo borrar**
- *Cuando* un archivo está en uso
- *Entonces* sigue con lo demás y al final lista lo que quedó, con su ruta.

## Fuera de alcance

- Desinstalar Python, Firefox, rclone, Tesseract o Ghostscript (los instalaste tú).
- Borrar archivos de la carpeta de cursos (son tuyos).
- Limpiar cachés de versiones anteriores a esta spec (se documenta cómo hacerlo a mano en
  `docs/ayuda.md`).

## Preguntas abiertas

| # | Pregunta | Por defecto | Decide |
|---|---|---|---|
| 1 | ¿El desinstalador también borra la carpeta del proyecto? En Windows no puede borrarse a sí mismo mientras corre. | No: dice cómo borrarla. En Linux, `desinstalar.sh` sí puede hacerlo si se pide con `--todo`. | Frank |
| 2 | ¿Cuántos respaldos guardar? | 2 (RES-04). | Frank |

## Historial

| Fecha | Cambio | Por qué |
|---|---|---|
| 2026-10-19 | Primera versión, con los residuos R1–R8 encontrados en el código. | Requisito de Frank: no dejar archivos fuera ni acumular. |
