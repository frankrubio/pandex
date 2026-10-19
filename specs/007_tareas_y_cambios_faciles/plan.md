# 007 · Plan

## Enfoque

1. **El contrato, verificado en la CI** (EXT-01 a EXT-03): ya está en
   `tests/test_principios.py`. Cualquier tarea nueva que no lo cumpla rompe la CI con un
   mensaje que dice qué falta.
2. **Generador** (EXT-04): `herramientas/nueva_tarea.py`, solo con la biblioteca estándar.
   Plantillas dentro del mismo script (sin archivos extra). La prueba generada usa
   `tests/apoyo.CtxFalso` y falla con `self.fail("Implementa run(): …")`.
3. **Estilo automático** (EXT-06, EXT-07): `ruff` con una configuración mínima en
   `pyproject.toml` (solo `[tool.ruff]`, sin convertir Pandex en paquete instalable):
   reglas `E`, `F`, `I`, `T20` (prints), `B`; largo de línea 120 (hoy solo 4 líneas lo pasan).
   `ruff` corre en la CI, no se instala en la PC del usuario.
4. **Documentación** (EXT-05): README → «Cómo se usa» con «Comprimir carpeta».

## Principios

- P9 es el objetivo. P5: el generador y `ruff` no llegan a la instalación del usuario.

## Archivos que se tocan

| Archivo | Cambio |
|---|---|
| `herramientas/nueva_tarea.py` | nuevo |
| `tests/test_herramientas.py` | nuevo |
| `pyproject.toml` | nuevo, solo `[tool.ruff]` |
| `.github/workflows/pruebas.yml` | job `estilo` |
| `pandex/accesos.py` | el `print` del final queda dentro de `if __name__ == "__main__"` (ya lo está: verificar) |
| `README.md` | «Comprimir carpeta» en «Cómo se usa» |
| `docs/crear-tareas.md` | sección «Con el generador» |

## Riesgos

| Riesgo | Qué se hace |
|---|---|
| `ruff` marca cientos de líneas existentes | Primer PR: solo configurar y corregir automáticamente (`ruff check --fix`, `ruff format` **no**). Lo que no se corrija solo, se ignora por archivo con fecha límite. Nada de refactorizar a mano por estilo (P9). |
