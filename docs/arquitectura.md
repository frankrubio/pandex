# Arquitectura

Pandex es una aplicación PyQt6 pequeña con un núcleo genérico (la mascota y un motor de
tareas) y funciones enchufables (*plug-ins*) en `tasks/`. El núcleo no sabe nada de Canvas
ni de Markdown: solo descubre tareas, las ejecuta sin congelar la interfaz y muestra lo que
devuelven.

## Mapa del código

| Módulo | Responsabilidad |
|---|---|
| `main.py` | Punto de entrada: instancia única, traducción de Qt al español, ícono. |
| `pandex/app.py` | `PandexApp`: une mascota, menú, bandeja, ejecutor y reloj; abre el asistente la primera vez. |
| `pandex/tareas.py` | El contrato de los plug-ins: `descubrir()` y `TaskContext` (el `ctx`). |
| `pandex/ejecutor.py` | `Ejecutor`: corre una tarea a la vez en un `QThread`. |
| `pandex/programador.py` | `Programador`: dispara tareas con horario cron (APScheduler). |
| `pandex/config.py` | `Config`: `config.json` con valores por defecto y guardado atómico. |
| `pandex/rutas.py` | Dónde vive cada cosa (proyecto y `%LOCALAPPDATA%\Pandex`). |
| `pandex/log.py` | `logs/pandex.log`, rotativo. |
| `pandex/accesos.py` | Accesos directos de Windows (Escritorio y arranque) y su ícono. |
| `pandex/horas.py` | Horas y fechas para el usuario, en formato de 12 horas (*7:05 p. m.*). |
| `pandex/personaje_nuevo.py` | «Añadir personaje…»: convierte una imagen o un GIF en un personaje (Pillow, solo al usarlo). |
| `pandex/ui/` | `mascota.py` (la ventana, estática), `personajes.py` (el catálogo de `assets/personajes/`), `logo.py` (el logo y los íconos), `globo.py`, `tema.py` (colores, tipografía y la hoja de estilos claro/oscuro), `iconos.py` y los diálogos de configuración, informe, registro y actualización. |
| `pandex/markdown/proceso.py` | Corre la conversión a Markdown en un proceso hijo (la memoria del conversor se libera al terminar). |
| `pandex/actualizar.py` | «Buscar actualizaciones…»: compara la versión con GitHub y actualiza con `git pull` o con el ZIP, con respaldo. Al arrancar aparta los archivos que dejaron versiones anteriores (`OBSOLETOS`), porque el ZIP solo agrega y reemplaza. |
| `pandex/canvas/` | Sincronizar Canvas → [sincronizar-canvas.md](sincronizar-canvas.md) |
| `pandex/markdown/` | Convertir a Markdown → [convertir-markdown.md](convertir-markdown.md) |
| `tasks/*.py` | Los plug-ins. Delgados: conectan una función de `pandex/` con el menú. |

## El flujo de una tarea

```
 clic derecho → menú ──┐
 reloj (cron) ─────────┼─► Ejecutor.ejecutar(tarea)
 asistente terminado ──┘         │
                                 ├─ ¿la tarea tiene preparar(ctx)?  (hilo de la interfaz)
                                 │      sí → puede abrir diálogos; devuelve la "entrada"
                                 │           o None para cancelar
                                 ▼
                        QThread: tarea.run(ctx)        ← aquí no se abren ventanas
                                 │  ctx.decir(...)  → globo
                                 │  ctx.progreso(n, total) → "Voy 3/10…"
                                 ▼
                        resultado = {"ok", "resumen", "detalle", "informe", "carpeta"}
                                 │
                                 ├─ globo con el resumen (⚠ si ok es False)
                                 ├─ detalle → logs/pandex.log
                                 └─ informe → ventana de resumen con «Abrir carpeta»
```

Reglas del modelo de hilos:

- **Una tarea a la vez.** Si pides otra mientras corre una, Pandex lo dice y no la lanza.
- **`run` corre en otro hilo:** no puede crear ventanas. Lo que necesite preguntar va en
  `preparar(ctx)`, que corre antes, en el hilo de la interfaz.
- El reloj (APScheduler) corre en su propio hilo; su disparo se reenvía a la interfaz con una
  señal Qt encolada antes de llamar al ejecutor.
- Un error en `run` no tumba la app: se registra con su traceback y la mascota avisa.

## Primera ejecución

`PandexApp.iniciar()` muestra la mascota y, 1,5 s después, revisa cada tarea que define
`necesita_configurar(params)`. Si alguna devuelve `True` (y nunca se le mostró su asistente),
se abre su `configurar(ctx)`. Se marca `asistente_visto` en su configuración para no
insistir en cada arranque; el asistente sigue disponible en el menú.

Para Canvas, "configurado" significa tener `destino` y al menos un curso en `cursos`
(`pandex.canvas.sincronizar.esta_configurado`).

## Dónde vive cada dato

| Qué | Dónde | ¿Va a GitHub? |
|---|---|---|
| Código, recursos, documentación | carpeta del proyecto | sí |
| Tus preferencias y cursos | `config.json` (carpeta del proyecto) | **no** (`.gitignore`) |
| Registro de eventos | `logs/pandex.log` | **no** |
| Sesión del navegador (cookies de Canvas) | `%LOCALAPPDATA%\Pandex\browser-profile` | no (fuera del proyecto) |
| Historial de Canvas (qué archivo está dónde) | `%LOCALAPPDATA%\Pandex\historial_canvas.json` | no |
| Diarios de reordenamiento (para deshacer) | `%LOCALAPPDATA%\Pandex\reordenamientos\` | no |
| Descargas y conversiones a medio hacer | `%LOCALAPPDATA%\Pandex\descargas`, `md_tmp` | no |

La variable de entorno `PANDEX_DATOS` reemplaza `%LOCALAPPDATA%\Pandex` (las pruebas la usan
para no tocar nunca los datos reales).

## `config.json`

Se crea solo la primera vez. Las claves que no escribas toman su valor por defecto
(`pandex/config.py → DEFAULTS`).

```jsonc
{
  "mascota": {
    "nombre": "Pandex",
    "personaje": "rusty",          // uno de assets/personajes/ o uno que añadiste
    "logo": "personaje",           // ícono de la app: el del personaje o el id de otro
    "tamano": 120,                 // alto en píxeles
    "opacidad": 1.0,
    "globo_activo": true,
    "globo_segundos": 5,
    "posicion": [1291, 695],       // se guarda sola al arrastrarla
    "siempre_encima": true,
    "frases_click": ["¿Qué tal?", "..."]
  },
  "arrancar_con_windows": false,
  "version_config": 4,             // para poner al día un config.json viejo al actualizar
  "tareas": {
    "<id de la tarea>": {
      "activa": true,
      "schedule": "0 19 * * *",    // cron (Configuración → Tareas lo arma por ti); null = solo manual
      ...                          // lo propio de cada tarea
    }
  }
}
```

Las claves de cada tarea están documentadas en su página:
[Sincronizar Canvas](sincronizar-canvas.md#configuración) ·
[Convertir a Markdown](convertir-markdown.md#configuración).

## Pruebas

```bash
.venv\Scripts\python.exe -m unittest discover -s tests -t .
```

`tests/__init__.py` apunta la carpeta de datos a un temporal y Qt a una pantalla invisible
antes de importar nada. `tests/apoyo.py` trae un **Canvas falso** (cursos, módulos y
archivos fijos; cuenta llamadas y puede fallar a propósito) y un `ctx` falso. Hay pruebas de
punta a punta de la sincronización, del reordenamiento con deshacer y del asistente completo
manejado por código. Ninguna usa internet.

## Decisiones de diseño

- **La API de Canvas, no raspar HTML.** Más rápido y estable. El navegador (Playwright) solo
  se usa para iniciar sesión: así funciona con cualquier SSO institucional sin que Pandex
  toque contraseñas ni tokens.
- **Sin IA.** El conversor decide el tipo por la extensión (sin el modelo Magika de
  MarkItDown) y el clasificador de material de estudio son reglas que se pueden leer.
- **Nada destructivo por defecto.** Sincronizar solo crea archivos. Reordenar mueve, pero
  solo lo que confirmas en una vista previa, nunca pisa nada y anota cada movimiento para
  deshacerlo.
- **Plug-ins delgados.** La lógica vive en `pandex/` (probada y reutilizable); `tasks/`
  solo la conecta. Para una función propia y pequeña basta un archivo en `tasks/`.

## Personajes

Cada personaje es una carpeta de `assets/personajes/<id>/` y aparece solo en **Configuración →
Apariencia** (`ui/personajes.py` la lee):

| Archivo | Qué es |
|---|---|
| `spritesheet.png` | Los cuadros en fila, todos del mismo tamaño (los nuevos, 192×208). |
| `personaje.json` | `nombre`, `cuadros` (qué cuadro usa cada estado), `recorte` (la caja común, para que la figura no salte), `cabeza` (lo que va en el logo), `fondo_logo` y `orden`. |
| `icono.ico` | El ícono de la app con su cara (`herramientas/crear_icono.py <id>`). |

Hoy trae `rusty`, `bmo`, `robot` y `panda_clasico`. **El logo** (`mascota.logo`) sigue al
personaje o queda fijo en otro; al cambiarlo, Pandex cambia el ícono de las ventanas, de la
bandeja y de los accesos directos que existan (`accesos.cambiar_icono`).

**Un personaje nuevo para incluir en Pandex** se dibuja en código con `herramientas/skins/` (librería `pixelart.py`,
un archivo por personaje y `construir.py`, que genera la carpeta completa). La skill
`.claude/skills/skin-pixel-art` tiene las reglas del estilo de Rusty y el paso a paso.

**Un personaje tuyo**, sin tocar código: **Configuración → Apariencia → Añadir personaje…**
(`pandex/personaje_nuevo.py`). Acepta PNG, GIF, WEBP o JPG:

| Si la imagen es… | Pandex… |
|---|---|
| Una sola figura | Usa la misma imagen para todos los estados. |
| Varias poses del mismo tamaño, en fila (como Rusty) | Las separa solo, por las columnas transparentes entre poses. Orden: normal, trabajando, feliz, error; si faltan, usa la normal. |
| Un GIF animado | Toma cada cuadro como una pose, en ese orden. |
| Una mascota de Codex Pets (el `.zip`, su `pet.json` o su `spritesheet.webp`) | Reconoce el atlas de 8 columnas × 192×208 y toma: normal = fila 0 (*idle*), trabajando = fila 8 (*review*), feliz = fila 3 (*waving*), error = fila 5 (*failed*). El nombre sale de `displayName`. |

Si no tiene transparencia y el fondo es de un solo color, lo quita. El nombre que escribes es
el que aparece en el selector, con «(tuyo)». Se guarda en `%LOCALAPPDATA%\Pandex\personajes\<id>\`
(con su `personaje.json` e `icono.ico`), así que sobrevive a las actualizaciones; **Quitar** lo
borra de ahí. Un `config.json` antiguo con `"personaje": "pixel"` pasa a Rusty y conserva su
bloque `spritesheet`, para que puedas añadir esa imagen con el botón.

## Rendimiento

Medido con `QT_QPA_PLATFORM=offscreen` (Linux; en Windows las cifras absolutas cambian, las
proporciones no):

| | Antes | Ahora |
|---|---|---|
| Arranque | 400 ms | 200 ms |
| Memoria en reposo | 80 MB | 72 MB |
| Hilos | 2 (interfaz + APScheduler) | 1 (APScheduler solo si hay horarios) |
| CPU, repintados y temporizadores en reposo | 0 % · 0 · 0 | 0 % · 0 · 0 |
| Memoria que queda tras convertir a Markdown | +131 MB, hasta cerrar Pandex | +0,6 MB |

Qué se carga y cuándo:

- **Al arrancar:** Qt, la mascota, el menú y las tareas (solo su parte liviana).
- **`playwright`** (`canvas/sesion.py → _cargar`): al iniciar sesión en Canvas.
- **`requests`** (`canvas/cliente.py`, `actualizar.py`): al sincronizar o buscar actualizaciones.
- **APScheduler** (`programador.py`): solo si alguna tarea tiene horario.
- **MarkItDown** (`markdown/proceso.py`): en un proceso hijo que se cierra al terminar; Python
  no puede descargar módulos, así que es la única forma de recuperar esa memoria. Con
  `tareas.convertir_md.proceso_aparte: false` se convierte dentro de Pandex.
- **`asyncio`**: solo para el OCR de Windows.

La mascota es **estática**: cada estado (reposo, feliz, trabajando, error) se pinta una
sola vez y queda en caché (`personajes.imagen`). No hay temporizadores de
animación; la ventana solo se repinta cuando cambia el estado. El único temporizador es
un disparo único que la devuelve al reposo tras una reacción. Las transiciones (globo,
apertura de ventanas) duran menos de 0,3 s y solo corren en ese momento. Los avances de
una tarea refrescan el globo como mucho 4 veces por segundo.
