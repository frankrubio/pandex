# 006 · Plan

## Enfoque

1. **Que la CI pruebe lo que el usuario realmente ejecuta** (PLA-01, PLA-02): matriz más
   amplia y un job `instaladores` que corre `instalar.sh`/`instalar.bat` sin preguntas, después
   `main.py --test`, y al final `desinstalar.*` (cuando exista) seguido de la prueba de
   residuos.
2. **Python viejo en Linux** (PLA-03): `instalar.sh` detecta la versión; si es menor que 3.12,
   ofrece `uv` con todo dentro de la carpeta del proyecto:
   ```bash
   export UV_CACHE_DIR="$PWD/.uv/cache" UV_PYTHON_INSTALL_DIR="$PWD/.uv/python"
   ./.uv/bin/uv venv --python 3.12 .venv
   ```
   `.uv/` va al `.gitignore` y se cuenta en el peso (002). Al terminar se borra `.uv/cache`.
3. **Mismo árbol en los dos sistemas** (PLA-04): una prueba que sincroniza con el Canvas falso
   y escribe la lista ordenada de rutas relativas (con `/`); se compara con un archivo
   esperado versionado. Corre en los dos sistemas de la matriz.
4. **Rutas raras** (PLA-05): carpeta temporal con nombre `OneDrive - Año Diseño` para todas
   las pruebas de punta a punta (`tests/apoyo.ConCarpetaTemporal` usa ese prefijo).
5. **Plantilla de issue** (PLA-08): reemplazar el desplegable por Windows 10 / Windows 11 /
   Linux y un campo de texto para la distribución.

## Principios

- P7 es el objetivo. P2/P3: el Python portátil vive en la carpeta de Pandex; nada global.
- P5: el Python portátil cuenta para el peso; si rompe el límite, se discute.

## Archivos que se tocan

| Archivo | Cambio |
|---|---|
| `.github/workflows/pruebas.yml` | matriz con `ubuntu-22.04`, `ubuntu-24.04`, `windows-latest` × 3.12/3.13/3.14 |
| `.github/workflows/instaladores.yml` | nuevo |
| `instalar.sh` | Python portátil con `uv` |
| `.gitignore` | `.uv/` |
| `tests/test_paridad.py`, `tests/datos/arbol_esperado.txt` | nuevos |
| `tests/apoyo.py` | prefijo con espacios, tildes y ñ |
| `.github/ISSUE_TEMPLATE/error.yml` | sistema operativo |
| `README.md`, `docs/linux.md` | sistemas soportados y no soportados |

## Riesgos

| Riesgo | Qué se hace |
|---|---|
| La matriz más grande hace lenta la CI | `fail-fast: false`, caché de pip **solo en la CI** (no en la PC del usuario), y el job `instaladores` solo en PRs que tocan instaladores o requirements. |
| `uv` cambia su forma de instalar | Versión fija de `uv` en `instalar.sh`. |
