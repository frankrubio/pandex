# 008 · Plan

## Enfoque

Un solo parámetro, `estilo_carpetas`, con dos valores: `guiones_bajos` (lo predeterminado) y
`propio`. Lo lee `Sincronizacion` al empezar (`nombres.estilo_de(params)`) y lo guarda el
asistente. La carpeta de curso no depende del estilo (EST-03).

Se descartó mirar las carpetas hermanas de cada carpeta nueva: es adivinar, y un estilo
declarado se puede probar y explicar.

## Principios

- **P4:** nada se renombra; solo cambia el nombre de lo que se crea.
- **P8:** no hay que editar `config.json`: el asistente decide el estilo. La herramienta
  `aplicar_config_canvas.py` existe para quien ya tiene su configuración escrita.
- **P1:** la configuración personal de cada usuario no entra al repositorio.

## Archivos que se tocan

| Archivo | Cambio |
|---|---|
| `pandex/canvas/nombres.py` | `en_guiones_bajos`, `nombre_de_carpeta(nombre, estilo)`, `nombre_de_curso`, `estilo_de` |
| `pandex/canvas/destinos.py` | `resolver_subcarpeta(..., estilo)` |
| `pandex/canvas/sincronizar.py` | fija el estilo; carpeta de curso con `nombre_de_curso` |
| `pandex/canvas/adoptar.py` | `Convenciones.detectada` |
| `pandex/canvas/asistente.py` | guarda `estilo_carpetas`; sugiere carpetas de curso en `_` |
| `herramientas/aplicar_config_canvas.py` | nuevo: mezcla parámetros en `config.json` |
| `tests/test_estilo_carpetas.py` | pruebas de EST-01 a EST-07; se ajustan las que fijaban el estilo anterior |
| `docs/sincronizar-canvas.md`, `docs/convenciones.md`, `CHANGELOG.md` | el parámetro nuevo |

No se toca el nombre de los archivos descargados ni `historial.py`.

## Riesgos

| Riesgo | Qué se hace |
|---|---|
| Quien ya usaba Pandex vería `Sem_8` junto a `Sem 7` | EST-06: sin `estilo_carpetas` y con cursos configurados se usa `propio`. |
| Un usuario con carpetas de curso con espacios | Se respetan las que existen; solo las nuevas van en `_` (pregunta abierta 1). |
