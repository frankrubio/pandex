# 002 · Plan

## Enfoque

1. **Medir siempre, en los dos sistemas.** `herramientas/medir_peso.py` suma el peso según la
   definición de la spec y lo imprime por componente (los 15 paquetes más pesados). Un job
   nuevo de la CI (`peso`) instala base y completo en `windows-latest` y `ubuntu-latest`, mide
   y falla si se pasa de 350/600 MB. Sin esto, cualquier dependencia nueva rompe el límite
   sin que nadie lo note.
2. **Bajar de 648 a < 600 MB**, con las opciones de menor riesgo primero. Cada una se mide; se
   aplican hasta tener al menos 30 MB de margen:

   | Opción | Ahorro esperado (Linux) | Riesgo |
   |---|---|---|
   | a. Instalar con `--no-cache-dir` y sin `pip` de sobra en `.venv` | ~0 en `.venv` (sí en caché: ver 003) | nulo |
   | b. Podar librerías de Qt no usadas tras instalar (lista en `herramientas/poda_qt.txt`) | 60–100 MB (por medir) | medio: si una librería sí se usaba, la interfaz no abre → prueba de humo |
   | c. Quitar el extra `xls` de MarkItDown (Excel viejo) si eso evita `pandas`/`xlrd` | hasta ~70 MB si pandas sale (por medir) | bajo: se pierde `.xls`, se mantiene `.xlsx` |
   | d. En Windows, Selenium + Edge/Chrome en vez de Playwright | ~75 MB y no descargar Chromium | medio: cambia el inicio de sesión en Windows; ya funciona en Linux |
   | e. Conversores directos en vez de MarkItDown (sin magika/onnxruntime) | ~70–140 MB | alto: reescribe la conversión |

3. **Extras declarados en un solo lugar.** `EXTRAS` gana `id`, `nombre`, `archivo`,
   `modulos`, `peso_mb` (lo escribe la CI) y `descripcion`. Los instaladores dejan de nombrar
   «Convertir a Markdown»: llaman a `python -m pandex.extras --preguntar` (o
   `--instalar markdown`, `--lista`), que recorre el catálogo. Así una función futura solo
   añade su entrada y su `requirements-<id>.txt`.
4. **Quitar un extra.** Al instalarlo se guarda en `DATOS/extras/<id>.json` la lista de
   paquetes que **ese** extra añadió (diferencia de `pip freeze` antes y después). Quitar =
   `pip uninstall -y` de esa lista, sin tocar los que ya estaban en la base. Si el archivo no
   existe (instalado por una versión vieja), se calcula con los metadatos de los paquetes
   instalados (`importlib.metadata`): los que solo requiere el extra.
5. **Navegador en Windows.** Orden: Chrome → Edge (`channel="msedge"`) → Chromium. Si hay que
   descargar Chromium: `PLAYWRIGHT_BROWSERS_PATH = DATOS/navegadores`.

## Principios

- P5: es el objetivo de esta spec.
- P3: `--no-cache-dir`; navegadores y metadatos de extras dentro de `DATOS`.
- P7: el job `peso` corre en los dos sistemas; la opción d unifica el código.
- P2: nada se instala fuera de `.venv`/`DATOS`.

## Archivos que se tocan

| Archivo | Cambio |
|---|---|
| `herramientas/medir_peso.py` | nuevo: mide según la definición; `--base`, `--json`, `--limite N` |
| `.github/workflows/peso.yml` | nuevo: instala y mide en Windows y Linux |
| `pandex/extras.py` | catálogo ampliado; CLI `--preguntar/--instalar/--quitar/--lista`; `quitar()` |
| `instalar.sh`, `instalar.bat` | llaman a `python -m pandex.extras`; `--no-cache-dir`; `PANDEX_EXTRAS` |
| `pandex/ui/configuracion.py` | botón **Quitar** junto a cada extra instalado |
| `pandex/canvas/sesion.py` | Edge antes que Chromium; `PLAYWRIGHT_BROWSERS_PATH` |
| `requirements-markdown.txt` | según lo que decidan las mediciones (opción c) |
| `herramientas/poda_qt.txt` + paso en instaladores | si se aprueba la opción b |
| `tests/test_extras.py` | nuevo |
| `README.md`, `docs/linux.md` | pesos medidos |

## Medición

```
python herramientas/medir_peso.py            # total y desglose
python herramientas/medir_peso.py --base     # falla si hay paquetes de extras
python herramientas/medir_peso.py --limite 600
```

| Antes (19/10/2026) | Linux | Windows |
|---|---|---|
| Base | 341 MB | sin medir |
| Completo | 648 MB | sin medir |

## Riesgos

| Riesgo | Qué se hace |
|---|---|
| La poda de Qt borra algo que sí se usa | Lista explícita (no comodines amplios) + `main.py --test` + `tests/test_ui.py` en la CI después de podar. |
| `pip uninstall` de un extra quita un paquete compartido con la base | Solo se quitan los paquetes de `DATOS/extras/<id>.json`, que no estaban antes de instalar el extra. |
| Los pesos cambian con cada versión de las dependencias | El job `peso` corre en cada PR que toque `requirements*.txt`. |
