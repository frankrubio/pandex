# Sincronizar Canvas

Baja el material de tus cursos de Canvas y lo ordena en carpetas que copian la organización
del curso. El código vive en `pandex/canvas/`; `tasks/sync_canvas.py` solo lo conecta.

| Módulo | Qué hace |
|---|---|
| `nombres.py` | Normalizar texto, nombres válidos en Windows, leer el nº de semana, reconocer «Laboratorio». |
| `cliente.py` | La API REST de Canvas con las cookies de tu sesión. Paginación y reintentos. |
| `sesion.py` | Iniciar sesión con un navegador real (Playwright) y cerrarlo enseguida. |
| `historial.py` | Qué archivo de Canvas ya está en tu disco y dónde. |
| `estructura.py` | Leer cursos y módulos: semanas, secciones, parejas teoría/lab. |
| `destinos.py` | A qué carpeta va cada archivo y si ya lo tienes (índice de duplicados). |
| `sincronizar.py` | La tarea completa, por fases. |
| `adoptar.py` | Usar una carpeta que ya tenías: emparejar, leer tu estilo, reordenar, deshacer. |
| `asistente.py` | La ventana de configuración inicial. |

## Cómo lee Canvas

Un curso de Canvas tiene **módulos** (`Semana 3`, `Sílabo y anexo`…). Cada módulo es una
lista de ítems: archivos, enlaces, tareas y **subencabezados** (`Material de clase`,
`Actividades`…) que agrupan a los ítems que vienen después. Pandex solo baja los ítems de
tipo **archivo** de los módulos **publicados**.

La semana sale del **nombre del módulo** (`Semana 7`, `Sem 7`, `Week 07`). Los módulos sin
número de semana van a una carpeta con su nombre.

Muchas universidades separan **teoría y laboratorio en dos cursos** de Canvas
(`Programación I - Teoría 1` y `Programación I - Laboratorio 14`). El asistente los reconoce
porque sus nombres solo difieren en esa parte, y les da una sola carpeta con `Teoría` y `Lab`
dentro de cada semana. Un curso cuyo nombre trae las dos cosas (`Teo. 1 - Lab. 11`) es uno solo.

## Las fases de una sincronización

| Fase | Qué pasa | Tiempo típico |
|---|---|---|
| sesión | El navegador abre sin ventana con tu sesión guardada, confirma con la API que estás dentro y se cierra. Si la sesión venció, abre una ventana para que entres. | ~4 s |
| módulos | Lee los módulos de todos tus cursos **a la vez**. | ~2 s |
| consultas | Pide nombre real y tamaño **solo de lo que el historial no conoce**. | 0 s si no hay nada nuevo |
| revisar disco | Para cada archivo nuevo: ¿ya lo tienes? ¿a qué carpeta va? | < 1 s |
| descargas | Baja en paralelo a una carpeta temporal y mueve de a uno. | lo que pese |

Una sincronización sin novedades tarda unos 6 segundos. Cada fase queda cronometrada en
**Ver registro** (`fases: sesión 4.2s · módulos 1.8s · …`).

## Reglas que nunca se rompen

1. **Solo crea archivos.** Sincronizar nunca borra, mueve, sobrescribe ni renombra nada tuyo.
2. Si el archivo ya está en el destino (o apareció mientras bajaba), no lo pisa.
3. **Un archivo a medias nunca llega a tu carpeta:** se baja aparte y se comprueba que tenga
   exactamente los bytes que Canvas dice; si no, se descarta y se reintenta la próxima vez.
4. El archivo se llama **como en el módulo de Canvas**, con la **extensión del archivo real**
   (hay títulos con puntos en medio que, si no, quedarían sin extensión). Solo se cambian los
   caracteres que Windows no acepta (`< > : " / \ | ? *`).
5. Las carpetas de `nunca_escribir` son intocables.

## ¿Ya lo tienes? (duplicados)

Antes de bajar algo, Pandex revisa **la carpeta entera del curso** (todas las semanas y
subcarpetas), no solo el destino, porque es común tener el mismo archivo en otra semana, en
otra sección o renombrado a mano. Lo salta si:

- **coincide el nombre completo**, ignorando tildes, espacios, signos y mayúsculas; o
- **coincide el tamaño exacto en bytes**, aunque lo hayas renombrado.

Para no saltar de más:

- El nombre se compara **con extensión**: la misma clase en `.pptx` y en `.pdf` son dos
  archivos que quieres.
- El tamaño solo cuenta **desde 4 KB**: los accesos `.url` pesan todos casi lo mismo.
- Los `.md` que genera Convertir a Markdown no cuentan por tamaño.
- **Entre teoría y laboratorio, el nombre solo no basta**: cada docente sube su propio
  `semana 9.pptx` y son materiales distintos. Entre las dos mitades, un archivo solo se salta
  si además pesa exactamente lo mismo (el docente de lab volvió a subir el de teoría).

Cada decisión queda en el registro con su motivo y la ruta del archivo que ya tenías:
`ya lo tenías (mismo nombre) · Programación · Clase 3.pdf → …\Sem 3\Teoría\Clase 3.pdf`.

## El historial

`%LOCALAPPDATA%\Pandex\historial_canvas.json` recuerda, por cada archivo de Canvas (su id),
dónde quedó en tu disco. Si sigue ahí, la próxima vez ni se consulta: por eso una
sincronización sin novedades no le pregunta nada a Canvas archivo por archivo. Si lo moviste
o lo borraste, se revisa desde cero con las reglas de arriba (y si lo borraste, vuelve a bajar).

También recuerda:

- los cursos donde Canvas negó el listado de archivos (a muchos alumnos les responde 403):
  se reintenta cada 30 días, no en cada corrida;
- los archivos que elegiste **no bajar** en la descarga inicial.

Borrar el historial es seguro: la siguiente sincronización tarda un poco más y lo rehace.

## Usar una carpeta que ya tenías

En el asistente, la opción «En una carpeta donde ya tengo mis cursos» hace tres cosas, y
muestra cada una antes de tocar nada:

1. **Empareja** tus carpetas con los cursos de Canvas comparando palabras, siglas y el código
   del curso (`Introduccion_a_la_CD_e_IA` ↔ «Introducción a Ciencia de Datos e Inteligencia
   Artificial»). Puedes corregir cada pareja.
2. **Aprende tu estilo:** cómo nombras las semanas (`Sem 3`, `Semana 03`, `S3`…), las mitades
   (`Teoría`/`Lab`/`Laboratorio`) y las secciones. Lo nuevo seguirá ese estilo; la estructura
   (semana → mitad → sección) la manda Canvas.
3. **Reordena** (opcional) los archivos de Canvas que estén fuera de lugar:
   - se reconoce un archivo de Canvas por **nombre y tamaño exacto**; lo que no coincide (tus
     trabajos, tus apuntes) **no se toca**;
   - nunca se borra ni se reemplaza nada: si el destino está ocupado o tienes dos copias, el
     archivo se queda donde está y se lista como «se queda como está»;
   - si un archivo está publicado en teoría y en lab, y ya está en cualquiera de los dos
     lugares, se queda;
   - su `.md` de Convertir a Markdown lo acompaña;
   - cada movimiento se anota en `%LOCALAPPDATA%\Pandex\reordenamientos\` y **Configurar
     Canvas… → Deshacer el último reordenamiento** devuelve todo a su lugar.

## El aviso al terminar

- **Globo**, siempre: `✓ Todo al día · 9 cursos, 194 archivos · 6 s` o
  `✓ 3 nuevo(s): Cálculo 2, Física 1 · 9 s`. Si algo falló, la mascota tiembla y lo dice:
  `⚠ 2 nuevo(s)… · 1 no se pudo bajar`.
- **Ventana de resumen**, solo si hubo novedades o problemas: los archivos nuevos por curso
  con su carpeta (`Sem 7 · Teoría · Material de clase`), lo que falló y por qué, y un botón
  para abrir la carpeta.

## Configuración

El asistente escribe todo esto en `config.json → tareas → sync_canvas`. Se puede editar a mano
(con Pandex cerrado: guarda su posición al arrastrarla).

| Clave | Por defecto | Qué es |
|---|---|---|
| `canvas_url` | — | La dirección de tu Canvas. |
| `destino` | — | La carpeta donde están las carpetas de tus cursos. |
| `cursos` | — | Lista de cursos (ver abajo). |
| `formato_semana` | `"Sem {n}"` | Nombre de las carpetas de semana. `"Semana {n:02d}"` da `Semana 03`. Siempre se reconocen además `Sem N` y `Semana N`. |
| `secciones` | `{}` | Subencabezado de Canvas → carpeta. La etiqueta vale como prefijo (`"material de clase"` cubre «Material de clases») y gana la más larga. |
| `schedule` | `null` | Horario cron (p. ej. `"0 19 * * *"`). |
| `dedupe_por_tamano` | `true` | Saltar archivos con el mismo tamaño aunque cambie el nombre. |
| `headless` | `true` | Probar primero sin ventana con la sesión guardada. |
| `usar_chrome_instalado` | `true` | Usar tu Google Chrome; si no está, el Chromium de Playwright. |
| `espera_login_segundos` | `300` | Cuánto esperar a que inicies sesión en la ventana. |
| `calendario` | — | Opcional: `[{"semana": 1, "inicio": "2026-08-10", "fin": "2026-08-16"}, …]`. Solo lo necesitan los cursos en modo `"lista"`. Si existe y hoy no cae en ninguna semana, no se sincroniza. |

Cada curso de `cursos`:

| Clave | Qué es |
|---|---|
| `canvas_id` | El id del curso en Canvas (lo escribe el asistente). |
| `codigo` + `tipo` | Alternativa para escribir a mano: un código que aparece en el nombre del curso (`"CS6002"`) y `"teoria"` o `"laboratorio"` para distinguir las dos mitades. |
| `carpeta` | Nombre de la carpeta del curso dentro de `destino`. |
| `alias` | Nombre corto para los avisos (`"Programación (lab)"`). |
| `crear_secciones` | `true`: copia cada subencabezado de Canvas como carpeta (lo que hace el asistente). `false`: solo las secciones del mapa `secciones`; las demás se saltan, y dentro de una mitad se usa la carpeta de sección solo si ya existe. |
| `otros_modulos` | `true`: baja también los módulos sin número de semana, a una carpeta con su nombre. |
| `subcarpeta_fija` | La mitad del curso dentro de cada semana: `"Teoría"` o `"Lab"`. |
| `alias_subcarpeta` | Otros nombres válidos para esa mitad (`["Laboratorio"]`): si ya existe una, se usa esa. |
| `modo` | `"semanas"` (normal) o `"lista"`: un curso con un solo módulo plano que se reparte por la semana del `calendario`. Con `subcarpeta_raiz` (carpeta base) y `seccion_unica` (solo los archivos bajo ese subencabezado). |
| `nunca_escribir` | Carpetas donde Pandex jamás escribe (p. ej. `["Trabajos de laboratorio"]`). |

Ejemplo escrito a mano:

```jsonc
"cursos": [
  {"codigo": "CS6002", "tipo": "teoria", "carpeta": "Programacion_I",
   "subcarpeta_fija": "Teoría", "alias": "Programación"},
  {"codigo": "CS6002", "tipo": "laboratorio", "carpeta": "Programacion_I",
   "subcarpeta_fija": "Lab", "alias_subcarpeta": ["Laboratorio"], "alias": "Programación (lab)"}
]
```

## Límites conocidos

- Pandex ve lo mismo que tú como alumno: **lo que el docente no publicó, no existe** para él.
- Solo lee **archivos dentro de módulos**. Un adjunto puesto solo en una tarea, un anuncio o
  una página no se baja.
- Cada ciclo nuevo trae cursos nuevos en Canvas: vuelve a correr **Configurar Canvas…**.

## Hechos de Canvas que explican el diseño

- A muchos alumnos `/courses/{id}/files` les responde **403**: el nombre real y el tamaño se
  piden archivo por archivo (en paralelo, y solo para lo que el historial no conoce).
- La cookie de sesión no sobrevive a cerrar el navegador; el inicio de sesión institucional
  (SSO) la renueva solo en unos segundos. Por eso se pregunta a `/api/v1/users/self` hasta que
  responda, en vez de mirar la URL una sola vez.
- Las listas largas vienen paginadas (`Link: rel="next"`) y, si se pregunta muy rápido,
  Canvas responde 429: se espera y se reintenta.
