# Crear tus propias tareas

Una función nueva para Pandex es **un archivo `.py` en `tasks/`** con una clase `Task`.
Pandex lo encuentra al arrancar (o con **Recargar tareas** en el menú), lo agrega al menú y,
si tiene horario, lo programa. No hay que tocar nada más.

## La tarea mínima

```python
# tasks/hola.py
class Task:
    id = "hola"                         # único; también es su clave en config.json
    nombre = "Decir hola"               # lo que se ve en el menú
    descripcion = "Saluda y se va"      # tooltip y ventana de Configuración
    schedule = None                     # None = solo manual; "0 8 * * 1-5" = 8:00 de lunes a viernes
    icono = "hola"                      # opcional: sincronizar, documento, hola, canvas, lista… (pandex/ui/iconos.py)

    def run(self, ctx):
        ctx.decir("¡Hola!")
        return {"ok": True, "resumen": "Saludé."}
```

`run` corre en un hilo aparte, así que puede tardar lo que necesite sin congelar la mascota.

## Qué te da `ctx`

| | |
|---|---|
| `ctx.log(msg, nivel="info")` | Escribe en `logs/pandex.log` (`"warning"`, `"error"`…). |
| `ctx.decir(texto)` | Muestra el globo de diálogo. |
| `ctx.progreso(n, total)` | El globo dice «Voy n/total…». |
| `ctx.params` | Tu sección de `config.json` (`tareas → <id>`). Léela para tus opciones. |
| `ctx.guardar()` | Guarda en `config.json` lo que cambiaste en `ctx.params`. |
| `ctx.config` | Todo `config.json`, por si lo necesitas. |
| `ctx.entrada` | Lo que devolvió `preparar(ctx)` o `configurar(ctx)`; si no, `None`. |

## Qué devuelve `run(ctx)`

Un diccionario. Solo `ok` y `resumen` importan de verdad:

```python
return {
    "ok": True,                              # False → la mascota tiembla y antepone ⚠
    "resumen": "3 archivos listos · 2 s",    # una línea para el globo
    "detalle": ["línea para el log", "..."], # opcional
    "informe": "Texto largo\ncon detalles",  # opcional: abre una ventana de resumen
    "carpeta": r"C:\ruta",                   # opcional: botón «Abrir carpeta» en esa ventana
}
```

Si `run` lanza una excepción, Pandex la registra con su traceback y avisa: nunca se cae.

## Preguntar algo antes: `preparar(ctx)`

`run` no puede abrir ventanas. Si tu tarea necesita que el usuario elija algo, hazlo en
`preparar`, que corre antes y en el hilo de la interfaz. Lo que devuelva llega a `run` como
`ctx.entrada`; si devuelve `None`, la ejecución se cancela.

```python
from PyQt6.QtWidgets import QFileDialog


class Task:
    id = "contar_archivos"
    nombre = "Contar archivos de una carpeta"

    def preparar(self, ctx):
        carpeta = QFileDialog.getExistingDirectory(None, "¿Qué carpeta cuento?",
                                                   ctx.params.get("ultima", ""))
        if not carpeta:
            return None                       # canceló
        ctx.params["ultima"] = carpeta
        ctx.guardar()
        return {"carpeta": carpeta}

    def run(self, ctx):
        from pathlib import Path

        n = sum(1 for p in Path(ctx.entrada["carpeta"]).rglob("*") if p.is_file())
        return {"ok": True, "resumen": f"Hay {n} archivos.", "carpeta": ctx.entrada["carpeta"]}
```

`preparar` también se llama en las ejecuciones programadas: si allí no hace falta preguntar
nada, devuelve `{}`.

## Configuración inicial: `necesita_configurar` y `configurar`

Para tareas que necesitan un asistente la primera vez (como Sincronizar Canvas):

```python
class Task:
    id = "mi_servicio"
    nombre = "Mi servicio"
    configurar_texto = "Configurar mi servicio…"   # entrada en el menú

    def necesita_configurar(self, params):
        return not params.get("carpeta")            # True → se abre al arrancar (una vez)

    def configurar(self, ctx):
        # abre tu diálogo, guarda en ctx.params, llama ctx.guardar()
        # devuelve una "entrada" para ejecutar run enseguida, o None
        ...

    def run(self, ctx):
        ...
```

## Programarla

Con `schedule` en la clase o, mejor, desde **Configuración → Horario (cron)**, que se guarda
en `config.json` y manda sobre el código. Formato cron de 5 campos: `minuto hora día mes día_semana`.

| Cron | Cuándo |
|---|---|
| `0 19 * * *` | todos los días a las 19:00 |
| `0 8 * * 1-5` | de lunes a viernes a las 8:00 |
| `*/30 * * * *` | cada 30 minutos |

## Reglas de la casa

- **Nada destructivo sin preguntar.** Si tu tarea borra o mueve cosas del usuario, que lo
  confirme en `preparar` y deje cómo deshacerlo.
- **Nada de ventanas en `run`.** Usa `ctx.decir`, `ctx.progreso` y el `informe` final.
- **Opciones en `ctx.params`**, no escritas en el código: así cada usuario las ajusta.
- **Importa lo pesado dentro de las funciones** (como hace `convertir_md`): el arranque de
  Pandex sigue siendo rápido.
- Si tu tarea crece, mueve la lógica a un módulo de `pandex/` y deja el archivo de `tasks/`
  delgado. Así se puede probar en `tests/`.
- Para desactivar una tarea sin borrarla, renómbrala con `_` al principio (`_mi_tarea.py`)
  o desmárcala en Configuración.
