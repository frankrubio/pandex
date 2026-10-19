# 007 · Agregar tareas y modificar Pandex fácilmente

> Estado: aprobada  ·  Prefijo: `EXT`  ·  Principios: P9, P5, P8

## Por qué

Pandex crece con funciones de apoyo para estudiantes. Agregar una tarea nueva, o cambiar
una existente, tiene que ser fácil para una persona o un agente, sin romper lo que ya
funciona y siguiendo las convenciones del proyecto.

## Qué existe hoy

- Contrato de plug-ins: un archivo en `tasks/` con una clase `Task` (`pandex/tareas.py`,
  `docs/crear-tareas.md`). Aparece en el menú con **Recargar tareas**.
- Un archivo roto se salta con un aviso: no tumba la app.
- `requiere = "markdown"` oculta la tarea si su función opcional no está instalada.
- Las tareas son delgadas (23–50 líneas); la lógica vive en `pandex/`.
- Ejemplo comentado: `tasks/ejemplo_saludo.py`.

**Huecos encontrados:** no hay generador de tareas; el contrato solo se valida al cargar (no
en la CI); `pandex/comprimir.py` no figuraba en el mapa de `docs/arquitectura.md`; «Comprimir
carpeta» no aparece en «Cómo se usa» del README.

## Requisitos

| Id | Requisito | Se comprueba con |
|---|---|---|
| EXT-01 | Toda tarea de `tasks/` cumple el contrato: `id` en minúsculas ASCII con `_`, igual al nombre del archivo, único; `nombre`; `run` invocable; `requiere` (si existe) está en `EXTRAS`. | `tests/test_principios.py::Tareas::test_contrato` ✅ |
| EXT-02 | Las tareas son delgadas: ≤ 120 líneas cada archivo de `tasks/`. Lo que pase de ahí va a un módulo de `pandex/` con sus pruebas. | `Tareas::test_tareas_delgadas` ✅ |
| EXT-03 | Todo módulo de `pandex/` (primer nivel) aparece en el mapa de `docs/arquitectura.md`. | `Documentacion::test_mapa_de_modulos_completo` ✅ |
| EXT-04 | `python herramientas/nueva_tarea.py <id> "<Nombre>"` crea `tasks/<id>.py` (desde una plantilla con comentarios), `tests/test_tarea_<id>.py` (con una prueba que falla hasta implementarla) y una línea pendiente en `CHANGELOG.md`. No pisa archivos existentes. | `tests/test_herramientas.py::test_nueva_tarea` |
| EXT-05 | Toda tarea del menú tiene una línea en «Cómo se usa» del README o una página en `docs/`. | `Documentacion::test_tareas_documentadas` |
| EXT-06 | El código de `pandex/` y `tasks/` no usa `print` (usa el registro), salvo los puntos de entrada de línea de comandos (`if __name__ == "__main__"`). | `test_sin_print` |
| EXT-07 | Las convenciones de código y de proyecto están escritas en `docs/convenciones.md` y la CI las verifica con `ruff` (estilo e importaciones). | job `estilo` |
| EXT-08 | Una tarea que lanza una excepción en `run`, `preparar` o `configurar` deja a Pandex funcionando, con el error en el registro y un globo con «⚠». | prueba existente en `tests/test_nucleo.py` + `test_error_en_preparar` |
| EXT-09 | Una función opcional nueva se agrega declarándola en `EXTRAS` y en su `requirements-<id>.txt`; la tarea solo pone `requiere = "<id>"` (ver 002, PES-05). | 002 |

✅ = la prueba ya existe y pasa.

## Escenarios

**EXT-04 · Una tarea nueva en un minuto**
- *Dado* un clon limpio
- *Cuando* se ejecuta `python herramientas/nueva_tarea.py renombrar_pdfs "Renombrar PDFs"`
- *Entonces* existen `tasks/renombrar_pdfs.py` y `tests/test_tarea_renombrar_pdfs.py`; la suite
  tiene **una** prueba fallando que dice qué falta; al pulsar «Recargar tareas», aparece
  «Renombrar PDFs» en el menú.

**Error · id repetido**
- *Cuando* se pide `nueva_tarea.py sync_canvas "Otra"`
- *Entonces* responde «Ya existe una tarea con id sync_canvas» y no crea nada.

## Fuera de alcance

- Un «mercado» de tareas o instalarlas desde internet.
- Tareas en otros lenguajes.

## Preguntas abiertas

| # | Pregunta | Por defecto | Decide |
|---|---|---|---|
| 1 | Las tareas propias del usuario viven en `tasks/` (dentro del repositorio clonado). ¿Se mueven a `DATOS/tareas/` para que nunca se suban por error y sobrevivan a cualquier forma de actualizar? | Sí, en una versión futura; `tasks/` queda para las del proyecto. | Frank |

## Historial

| Fecha | Cambio | Por qué |
|---|---|---|
| 2026-10-19 | Primera versión; se añade `comprimir.py` al mapa de arquitectura. | Requisito de Frank: agregar tareas y modificar Pandex tiene que ser fácil. |
