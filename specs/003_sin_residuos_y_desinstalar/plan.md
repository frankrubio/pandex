# 003 · Plan

## Enfoque

1. **Una prueba que vigile todo** (RES-01): `tests/test_residuos.py` redirige `HOME`,
   `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME`, `APPDATA`, `LOCALAPPDATA` y
   `PANDEX_DATOS` a una carpeta temporal, toma una «foto» (rutas + tamaño + fecha), ejecuta los
   flujos con Canvas falso y compara. Cualquier archivo nuevo fuera de los lugares permitidos
   hace fallar la prueba con su ruta. Es la red de seguridad de todo lo demás.
2. **Cerrar los residuos uno por uno** (R1–R6), cada uno con su prueba.
   - R1: `PIP_NO_CACHE_DIR=1` en los instaladores y `--no-cache-dir` en `extras.py` y
     `actualizar.py` (una función común `pandex.paquetes.instalar(...)` para no repetirlo).
   - R2: `os.environ["SE_CACHE_PATH"] = str(DATOS / "navegadores")` antes de crear el
     servicio de Selenium.
   - R3: `PLAYWRIGHT_BROWSERS_PATH = DATOS/navegadores` (comparte con 002, T002.5).
   - R4/R5: función común `limitar(carpeta, patron, cuantos)` en `pandex/rutas.py`.
   - R6: tras `pip install`, comparar `pip freeze` con lo que piden los `requirements*.txt`
     instalados (con sus dependencias) y desinstalar el resto. Con lista blanca: `pip`,
     `setuptools`, `wheel`.
3. **Inventario** (RES-10): `pandex/inventario.py` con `anotar(ruta, motivo)`, `quitar(ruta)`
   y `todo()`. Lo llaman `accesos.py`, `despertador.py`, `onedrive.py` y `firefox.py` (perfil
   de snap). Es un JSON pequeño en `DATOS`.
4. **Desinstalar** (RES-07/08/09): `pandex/desinstalar.py` (lógica, sin Qt) +
   `desinstalar.sh` / `desinstalar.bat` (llaman a `python -m pandex.desinstalar`) + botón en
   Configuración. Orden: detener despertador → quitar arranque → quitar accesos → desmontar
   OneDrive de Pandex → borrar `DATOS` → borrar `.venv` → mensaje final.

## Principios

- P3 y P2: objetivo de esta spec.
- P4: el desinstalador nunca toca la carpeta de cursos; pide confirmación con la lista.
- P1: borrar `DATOS` borra perfil del navegador, cookies e historial.

## Archivos que se tocan

| Archivo | Cambio |
|---|---|
| `tests/test_residuos.py` | nuevo (foto antes/después) |
| `pandex/paquetes.py` | nuevo: `instalar()`, `desinstalar()`, `huerfanos()` sin caché |
| `pandex/extras.py`, `pandex/actualizar.py` | usan `pandex/paquetes.py` |
| `pandex/canvas/firefox.py`, `pandex/canvas/sesion.py` | `SE_CACHE_PATH`, `PLAYWRIGHT_BROWSERS_PATH` |
| `pandex/rutas.py` | `NAVEGADORES = DATOS / "navegadores"`, `limitar()` |
| `pandex/inventario.py` | nuevo |
| `pandex/desinstalar.py`, `desinstalar.sh`, `desinstalar.bat` | nuevos |
| `pandex/accesos.py`, `pandex/despertador.py`, `pandex/onedrive.py` | anotan en el inventario |
| `pandex/ui/configuracion.py` | botón «Desinstalar Pandex…» |
| `docs/arquitectura.md`, `docs/ayuda.md`, `README.md` | límites, cómo desinstalar |

## Medición

En Linux: `du -sh ~/.cache/pip ~/.cache/selenium` antes y después de `./instalar.sh` en un
usuario nuevo. En Windows: `%LOCALAPPDATA%\pip\Cache` y `%LOCALAPPDATA%\ms-playwright`. Las
dos deben quedar sin cambios.

## Riesgos

| Riesgo | Qué se hace |
|---|---|
| La prueba de foto es lenta o inestable (Qt escribe cachés propias) | Si Qt escribe en `~/.cache/<app>`, se fija `QT_*`/`XDG_CACHE_HOME` hacia `DATOS` o se añade a la lista permitida con justificación en P3. |
| Borrar `DATOS` mientras el navegador tiene el perfil abierto | El desinstalador cierra Pandex y espera; si falla, reintenta y lo lista al final. |
| Quitar huérfanos borra algo que el usuario instaló a mano en `.venv` | `.venv` es de Pandex (P2); se documenta. Lista blanca para `pip`, `setuptools`, `wheel`. |
