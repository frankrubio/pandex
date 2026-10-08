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
| `pandex/accesos.py` | Accesos directos de Windows (Escritorio y arranque). |
| `pandex/ui/` | `mascota.py` (la ventana, estática), `rusty.py` (el panda rojo en pixel art), `dibujo.py` (panda robot vectorial y el logo), `sprites.py`, `globo.py`, `tema.py` (colores, tipografía y la hoja de estilos claro/oscuro), `iconos.py` y los diálogos de configuración, informe, registro y actualización. |
| `pandex/actualizar.py` | «Buscar actualizaciones…»: compara la versión con GitHub y actualiza con `git pull` o con el ZIP, con respaldo. |
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
    "personaje": "rusty",          // "rusty", "vectorial" (panda robot) o "pixel" (sprite sheet)
    "tamano": 120,                 // alto en píxeles
    "opacidad": 1.0,
    "spritesheet": { ... },        // solo con "personaje": "pixel"; ver «Cambiar el personaje»
    "globo_activo": true,
    "globo_segundos": 5,
    "posicion": [1291, 695],       // se guarda sola al arrastrarla
    "siempre_encima": true,
    "frases_click": ["¿Qué tal?", "..."]
  },
  "arrancar_con_windows": false,
  "version_config": 3,             // para poner al día un config.json viejo al actualizar
  "tareas": {
    "<id de la tarea>": {
      "activa": true,
      "schedule": "0 19 * * *",    // cron opcional; null = solo manual
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

## Rendimiento

La mascota es **estática**: cada estado (reposo, feliz, trabajando, error) se pinta una
sola vez y queda en caché (`rusty.imagen`, `dibujo.imagen`). No hay temporizadores de
animación; la ventana solo se repinta cuando cambia el estado. El único temporizador es
un disparo único que la devuelve al reposo tras una reacción. Las transiciones (globo,
apertura de ventanas) duran menos de 0,3 s y solo corren en ese momento. Los avances de
una tarea refrescan el globo como mucho 4 veces por segundo.
