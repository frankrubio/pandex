# Convenciones

Cómo se escribe y se organiza Pandex, para que cualquiera (persona o agente) pueda leerlo,
corregirlo, depurarlo y ampliarlo sin adivinar. Están sacadas del código que ya existe: si
algo aquí contradice al código, se corrige uno de los dos en un PR, no se ignora.

## Idioma

- **Todo en español de Perú neutro:** textos de la interfaz, documentos, comentarios,
  docstrings, nombres de módulos, funciones, variables y pruebas (`sincronizar`, `destinos`,
  `test_un_archivo_a_medias_nunca_llega_a_tu_carpeta`).
- Se quedan en inglés: palabras del lenguaje y de las librerías (`run`, `Task`, `ctx`,
  `schedule`, `self`), y términos sin traducción común (*plug-in*, *SSO*, *cron*).
- Frases cortas y directas. Sin jerga técnica en lo que ve el usuario.
- Toda hora visible en 12 horas (`pandex/horas.py`): *7:05 p. m.*

## Nombres de archivos y carpetas

- Sin tildes, sin `ñ`, sin espacios (`test_principios.py` lo verifica en lo versionado).
- Código Python: `minusculas_con_guion_bajo.py`. Documentos de `docs/`: `minusculas-con-guion.md`
  (como los que ya existen). Specs: `NNN_nombre_con_guion_bajo/`.
- Las carpetas que Pandex crea para el usuario siguen `carpetas_sin_tildes` (por defecto, sin
  tildes ni `ñ`).

## Organización

```
pandex/            núcleo genérico (no sabe de Canvas ni de Markdown)
├── canvas/        lógica de Sincronizar Canvas
├── markdown/      lógica de Convertir a Markdown
└── ui/            ventanas, tema y mascota (lo único que dibuja)
tasks/             plug-ins delgados: conectan una función de pandex/ con el menú
tests/             pruebas sin internet
herramientas/      scripts para quien programa (no llegan al usuario)
specs/             qué se va a cambiar y por qué
docs/              cómo funciona hoy
```

- **Una responsabilidad por módulo.** El mapa está en `docs/arquitectura.md`; todo módulo
  nuevo se añade ahí (la CI lo exige).
- **La lógica no depende de Qt** si no dibuja: así se prueba sin ventanas. Lo de Qt vive en
  `pandex/ui/` o en los asistentes.
- **Lo que depende del sistema** va detrás de `rutas.WINDOWS` y en funciones pequeñas.
- **Rutas siempre con `pathlib.Path`** y desde `pandex/rutas.py` (`RAIZ`, `DATOS`…). Nunca
  rutas escritas a mano ni `os.getcwd()`.

## Estilo de código

- PEP 8, líneas de hasta 120 caracteres, comillas dobles.
- Importaciones: biblioteca estándar, librerías, Pandex (relativas dentro del paquete).
- **Lo pesado se importa dentro de la función que lo usa** (Playwright, Selenium, requests,
  MarkItDown, Pillow, APScheduler), con un comentario de por qué. El arranque no los carga.
- Constantes en `MAYUSCULAS`; clases en `MayusculaInicial`; lo privado con `_`.
- Docstring en cada módulo (qué hace y, si no es obvio, por qué así) y en cada función
  pública. Dentro de un docstring, el código va entre dobles acentos graves, como en el
  resto del proyecto.
- Comentarios para el **por qué**, no para el qué.
- Sin `print` fuera de los puntos de entrada de línea de comandos: se usa el registro.
- Sin dependencias nuevas sin spec (afectan el peso, P5). Si se añade una: versión fija `==`,
  marcador de plataforma si aplica, y su peso medido en el PR.

## Registro y errores

- `log = get_logger("pandex.<modulo>")` al inicio del módulo; en una tarea, `ctx.log(...)`.
- Niveles: `info` para decisiones («ya lo tenías (mismo nombre)…»), `warning` para algo que
  el usuario debería saber, `error` con el *traceback* para fallas.
- Nunca se registran contraseñas, cookies, tokens ni cuerpos de respuestas con datos
  personales (P1).
- Errores que ve el usuario: una excepción propia del módulo (`CanvasError`, `ErrorExtra`,
  `ErrorActualizacion`…) cuyo mensaje se muestra **tal cual**: qué pasó y qué hacer. El detalle
  técnico va al registro.
- Una tarea nunca tumba la app: el ejecutor atrapa la excepción, la registra y avisa.

## Hilos e interfaz

- Una tarea a la vez. `run(ctx)` corre en otro hilo y **no abre ventanas**; lo que pregunte va
  en `preparar(ctx)`.
- Nada que tarde más de ~100 ms en el hilo de la interfaz.
- En reposo: sin temporizadores ni repintados (0 % de CPU).
- Colores, letras y radios solo en `pandex/ui/tema.py`.

## Configuración y datos

- Toda opción nueva tiene valor por defecto en `pandex/config.py → DEFAULTS` (o en la tarea)
  y un control en Configuración, o se marca como interna.
- Si cambia el formato de `config.json`, se sube `VERSION_CONFIG` y se escribe la migración en
  `config.migrar()` con su prueba.
- Lo que Pandex genera va en `DATOS`, nunca en el proyecto (salvo `config.json` y `logs/`).

## Git, ramas y versiones

- **Nunca** se empuja directo a `main`. Rama propia y PR.
- Nombres de rama: `tipo/descripcion-corta`, con `tipo` = `spec`, `tarea`, `arreglo`, `docs`
  (`tarea/T003.2-pip-sin-cache`).
- Mensajes de commit en español e imperativo, con la tarea o requisito si aplica:
  `Instalar sin caché de pip (T003.2, RES-02)`.
- Un PR = una tarea. Si crece, se parte.
- Versiones `MAYOR.MENOR.PARCHE` en `pandex/__init__.py`:
  - PARCHE: arreglos sin cambios visibles de función;
  - MENOR: algo nuevo que el usuario nota;
  - MAYOR: cambia algo que obliga al usuario a hacer algo (p. ej. reconfigurar).
- `CHANGELOG.md`: una línea por cambio que el usuario nota, en lenguaje simple. Pandex muestra
  esa sección al actualizar.
