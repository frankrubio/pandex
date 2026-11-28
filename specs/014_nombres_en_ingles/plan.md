# 014 · Plan

## Enfoque

Extender las reglas de texto, emparejamiento, detección de convenciones, reutilización de
carpetas y clasificación de Markdown que ya existen en Pandex para que acepten variantes en
inglés (`semester`, `week`, `wk`, `course`, `theory`, `lecture`, `laboratory`, `assignments`,
`readings`, `syllabus`…) manteniendo intacto el comportamiento actual en español.

No se agregan dependencias ni configuración nueva: Pandex detecta el estilo desde las carpetas
existentes del usuario o desde los propios nombres de módulos y cursos en Canvas.

## Principios

- **P4 (nada destructivo):** solo se reutilizan carpetas existentes y se calcula el destino;
  nunca se renombra ni borra nada.
- **P5 (liviano):** cero dependencias nuevas y expresiones regulares simples.
- **P7 (Windows y Linux):** solo lógica de rutas y nombres con `pathlib.Path`.
- **P8 (simple):** cero opciones manuales en `config.json`; funciona solo en el asistente,
  reconexión, sincronización y conversión a Markdown.

## Archivos que se tocan

| Archivo | Cambio |
|---|---|
| `pandex/canvas/nombres.py` | Ampliar `RE_SEMANA` (`Week_03`, `Week-3`, `Wk 3`, sin confundir `Semester`/`Sem 2026`) y `RE_LAB` (`Laboratory`, `Labs`). |
| `pandex/canvas/estructura.py` | Ampliar `_MITAD` y `tipo` con `Theory`/`Lecture`/`Lec`/`Laboratory`/`Labs`. |
| `pandex/canvas/destinos.py` | Ampliar `alias_semana` (`Week 03`, `Wk`, `W`, `S`) y `_EQUIVALENTES` (mitades, secciones y módulos comunes español ↔ inglés). |
| `pandex/canvas/adoptar.py` | Ampliar `_VACIAS`, `PREFIJOS_SEMANA`, `TEORIA`, `LAB`, `_misma_seccion`, banderas de detección en `Convenciones` y `convenciones_de_canvas`. |
| `pandex/canvas/asistente.py` | Usar `convenciones_de_canvas` como base para cursos nuevos y completar lo no detectado al adoptar. |
| `pandex/canvas/reconectar.py` | Actualizar `subcarpeta_fija`, `alias_subcarpeta` y `secciones` cuando se detectan en la carpeta reconectada. |
| `pandex/markdown/clasificador.py` | Añadir patrones y carpetas equivalentes en inglés para «Material de estudio». |
| `tests/test_nombres_ingles.py` | Pruebas de `ING-01` a `ING-06`. |
| `docs/sincronizar-canvas.md` | Documentar el soporte de nombres y convenciones en inglés. |
| `CHANGELOG.md`, `pandex/__init__.py` | Registrar el cambio y subir versión a `2.7.1`. |

No se toca la interfaz en español ni el esquema de `config.json`.

## Medición

Toda la suite de pruebas (`QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -t . -v`)
y comprobación de arranque (`QT_QPA_PLATFORM=offscreen .venv/bin/python main.py --test`).

## Riesgos

| Riesgo | Qué se hace |
|---|---|
| Falsos positivos al emparejar cursos que comparten `Course` o `Semester` | Incluir esos términos en `_VACIAS` y probar explícitamente que dos cursos distintos no se emparejan. |
| Confundir `Semester 1` o `Sem 2026` con una semana | Delimitar `RE_SEMANA` con `(?<![a-z])` y `(?!\d)` y probar explícitamente. |
| Cambiar el comportamiento de carpetas en español | Mantener `Sem {n}`, `Teoría` y `Lab` por defecto cuando Canvas está en español y correr las 442 pruebas existentes. |
