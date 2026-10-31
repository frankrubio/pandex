# 008 · Estilo de carpetas

> Estado: en curso  ·  Prefijo de requisitos: `EST`
> Principios que toca: P2 (archivos fuera de Pandex), P4 (nada destructivo), P7, P8

## Por qué

Pandex crea carpetas en la PC del estudiante (cursos, semanas, mitades, secciones). Hoy las
crea sin tildes ni ñ, pero **con espacios y signos** (`Diseno- Teoria`), y no distingue a quien
ya tiene su propio orden de quien empieza de cero. Eso deja nombres mezclados dentro de un curso
(`Sem 7` junto a `Sem_8`) o nombres que molestan a otras apps y a la sincronización de OneDrive.

## Qué existe hoy

- `pandex/canvas/nombres.py::nombre_de_carpeta` quita tildes y ñ; el interruptor
  `carpetas_sin_tildes` (docs/sincronizar-canvas.md).
- `pandex/canvas/destinos.py::resolver_subcarpeta` reutiliza una carpeta que ya existe (sin
  mirar tildes, espacios ni mayúsculas) y solo crea si no hay ninguna.
- `pandex/canvas/adoptar.py::detectar_convenciones` lee cómo nombras semanas, mitades y secciones.

## Requisitos

| Id | Requisito | Se comprueba con |
|---|---|---|
| EST-01 | Sin estilo propio, toda carpeta nueva se escribe con `_` en vez de espacios y sin tildes, ñ ni otros signos: `Diseño: Teoría` → `Diseno_Teoria`. Solo letras, números y `_`. | `tests/test_estilo_carpetas.py::GuionesBajos` |
| EST-02 | Con estilo propio (`estilo_carpetas: "propio"`), las carpetas nuevas de dentro del curso (semana, mitad, sección) se escriben tal como las tienes (`Sem 8`, `Teoría`, `Material de clase`); solo se cambian los signos que Windows no acepta. | `…::EstiloPropio` |
| EST-03 | La carpeta de cada curso nueva siempre va en `_` y sin tildes, con o sin estilo propio: es la ruta de la que cuelga todo. | `…::CarpetaDeCurso` |
| EST-04 | Una carpeta que ya existe se reutiliza aunque difiera en espacios, `_`, tildes o mayúsculas, y **nunca se renombra**. | `…::GuionesBajos::test_reutiliza_la_que_ya_tienes` |
| EST-05 | El asistente guarda `estilo_carpetas: "propio"` solo si leyó un estilo en las carpetas que ya tenías; si no, `"guiones_bajos"`. | `…::Asistente` |
| EST-06 | Quien ya tenía Canvas configurado antes de esta versión y no tiene `estilo_carpetas` sigue creando carpetas como las tiene configuradas (`propio`): no se mezclan estilos dentro de su curso. `carpetas_sin_tildes: false` también equivale a `propio`. | `…::Estilo::test_configuracion_anterior` |
| EST-07 | `herramientas/aplicar_config_canvas.py` mezcla un archivo con parámetros de Canvas en `config.json` sin tocar nada más, deja una copia de respaldo y no escribe si el archivo no es JSON válido. | `tests/test_estilo_carpetas.py::AplicarConfig` |

## Escenarios

**EST-01 · Sin estilo**
- *Dado* un usuario que apunta Pandex a una carpeta vacía
- *Cuando* se baja «Semana 3 / Material de clase» de «Física I (Lab.)»
- *Entonces* se crea `Fisica_I_Lab/Sem_3/Material_de_clase/`.

**EST-02 · Estilo propio**
- *Dado* `Programacion_I/Sem 7/Teoría/` ya existente y `estilo_carpetas: "propio"`
- *Cuando* llega la semana 8
- *Entonces* se crea `Programacion_I/Sem 8/Teoría/` (no `Sem_8`, no `Teoria`).

**EST-04 · Ya existe**
- *Dado* `Material de clase` y se pide `Material_de_clase` (o al revés)
- *Entonces* se usa la existente y no se crea otra.

**EST-07 · Archivo inválido**
- *Dado* un archivo que no es JSON
- *Entonces* no se toca `config.json` y se dice qué pasó.

## Fuera de alcance

- Renombrar carpetas que ya existen (P4).
- Cambiar el nombre de los **archivos** descargados: siguen como en Canvas (docs/sincronizar-canvas.md).
- Detectar el estilo por carpeta hermana; el estilo es uno por configuración.

## Preguntas abiertas

| # | Pregunta | Por defecto | Decide |
|---|---|---|---|
| 1 | ¿La carpeta de curso siempre en `_` aunque el usuario las tenga con espacios? | Sí (EST-03): es la ruta raíz y Frank ya lo usa así | Frank |

## Historial

| Fecha | Cambio | Por qué |
|---|---|---|
| 2026-10-31 | Primera versión. | Frank: lo predeterminado debe ser `_`, sin tildes ni signos, y Pandex debe acomodarse a su formato actual. |
