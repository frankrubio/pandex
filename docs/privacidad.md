# Privacidad

Qué guarda Pandex, dónde, para qué y con quién habla. Si algo de aquí no coincide con lo
que hace Pandex, es un error: repórtalo (ver [SECURITY.md](../SECURITY.md)).

## En corto

- **Todo pasa en tu PC.** Sin servidores propios, sin telemetría, sin IA en la nube.
- **Pandex nunca ve tu contraseña.** Inicias sesión en el navegador; Pandex usa la sesión que
  queda guardada en su propio perfil (no el tuyo).
- **Nada tuyo llega a GitHub.** Tu configuración, tu registro y tu sesión están fuera de lo
  que se sube (y las pruebas de `tests/test_principios.py` lo vigilan).
- **Guarda solo lo necesario.** No guarda tu nombre, correo, código de alumno ni notas.

## Qué guarda y dónde

| Dato | Archivo | Para qué |
|---|---|---|
| Dirección de tu Canvas, carpeta destino, cursos y secciones | `config.json` (carpeta de Pandex) | saber qué bajar y dónde ponerlo |
| Preferencias de la mascota y horarios | `config.json` | apariencia y tareas programadas |
| Copia de tu configuración (`config-ultima-buena.json`) y, si alguna vez se dañó, hasta 3 copias del archivo dañado (`config-danado-*.json`) | carpeta de datos | abrir Pandex aunque `config.json` se dañe |
| Fecha de la última búsqueda de actualizaciones | `config.json` (`ultima_busqueda`) | buscar una vez al día como máximo |
| Qué archivo de Canvas está en qué ruta de tu PC | `historial_canvas.json` (carpeta de datos) | no volver a bajar lo que ya tienes |
| Sesión guardada (`sesion_canvas.json`: solo las cookies de tu Canvas, permisos solo para tu usuario) | carpeta de datos | no abrir el navegador cada vez; se borra sola si Canvas la rechaza y al desinstalar |
| Sesión del navegador (cookies) | `browser-profile/` o `browser-profile-firefox/` (carpeta de datos) | entrar a Canvas sin escribir la contraseña |
| Cuentas de OneDrive (el nombre que les pusiste) y su acceso | `onedrive.json`, `rclone.conf` (carpeta de datos) | montar tu OneDrive en Linux |
| Cuándo corrió cada tarea | `ultimas_ejecuciones.json` (carpeta de datos) | ponerse al día si la PC estuvo apagada |
| Movimientos de un reordenamiento | `reordenamientos/` (carpeta de datos) | poder deshacerlo |
| Personajes que añadiste | `personajes/` (carpeta de datos) | mostrarlos |
| Plugins personales y su estado local | `plugins_personales/` (carpeta de datos) | mantener tus extensiones al actualizar |
| Caché de plugins publicados | `plugins_publicados/` (carpeta de datos) | instalar sin modificar el repositorio |
| Respaldos de actualizaciones | `respaldos/` (carpeta de datos) | volver atrás si algo sale mal |
| Punto de vuelta de la última actualización (versiones y archivos, nada tuyo) | `actualizacion.json` (carpeta de datos) | «Volver a la versión anterior» |
| Registro de eventos | `logs/pandex.log` (carpeta de Pandex, máx. ~4 MB) | entender qué pasó |

**Carpeta de datos:** `%LOCALAPPDATA%\Pandex` en Windows, `~/.local/share/Pandex` en Linux.
En Linux, la carpeta de datos y los perfiles del navegador son solo para tu usuario (`0700`), y
`sesion_canvas.json` y `rclone.conf` también (`0600`). En Windows, `%LOCALAPPDATA%` ya es solo tuyo.

### Las claves de `config.json`

| Clave | Qué guarda |
|---|---|
| `version_config` | la versión del formato, para ponerlo al día al actualizar |
| `mascota` | nombre, personaje, logo, tamaño, globo, posición y frases de la mascota |
| `arrancar_con_windows` | si Pandex abre al iniciar sesión en tu PC |
| `buscar_actualizaciones` | si revisa una vez al día si hay versión nueva |
| `modo_programador` | si el menú muestra «Saludar» y «Recargar tareas» |
| `tareas` | lo propio de cada tarea: si está activa, su horario y sus opciones (Canvas: la dirección, la carpeta, los cursos; ver [sincronizar-canvas.md](sincronizar-canvas.md)) |
| `modo`, `ultima_busqueda` | se crean al usarse: «siempre» o «a la hora», y la fecha de la última búsqueda de actualizaciones |

El registro incluye nombres de cursos y de archivos, y rutas de tu PC. Por eso:

- **Antes de pegarlo en un issue, revísalo** y borra lo que no quieras compartir.
- Nunca incluye contraseñas, cookies ni tokens: un filtro los cambia por `[oculto]` antes de
  escribir, aunque vengan dentro de un error (spec 004, PRI-03).

## Con quién habla

| Destino | Cuándo | Qué envía |
|---|---|---|
| Tu Canvas (la dirección que escribiste) | al configurar y sincronizar | pedidos de lectura de la API con tu sesión, y descargas (Canvas las redirige a su almacenamiento de archivos; esa redirección la decide Canvas) |
| GitHub (`api.github.com`, `github.com`, `raw.githubusercontent.com`, `codeload.github.com`) | al buscar actualizaciones (una vez al día como máximo; se puede apagar) | nada tuyo: lee la última versión publicada y sus novedades, y descarga su ZIP y su SHA-256 (GitHub los sirve desde `release-assets.githubusercontent.com`) |
| PyPI (`pypi.org`, `files.pythonhosted.org`) | al instalar o actualizar Pandex o una función opcional | nada tuyo: descarga paquetes |
| GitHub (`github.com`, que sirve el archivo desde `release-assets.githubusercontent.com`) | solo al instalar, si no tienes Python 3.12 o más nuevo y aceptas bajar uno | nada tuyo: descarga Python (python-build-standalone) y lo comprueba con la huella fija de `herramientas/python_portatil.txt` |

Programas que Pandex abre y que hablan por su cuenta:

Pandex rechaza cualquier pedido propio a otro host (`pandex/red.py`, spec 004, PRI-04).

| Programa | Con quién | Cuándo |
|---|---|---|
| Tu navegador (Firefox, Chrome o Edge: el que elijas) con el perfil de Pandex | Canvas y el inicio de sesión de tu universidad | al iniciar sesión |
| Selenium Manager (Linux) | GitHub, para bajar `geckodriver` (~3 MB) | la primera vez que inicias sesión |
| rclone (Linux) | Microsoft | si conectas OneDrive |

Ninguna biblioteca que Pandex carga manda telemetría. MarkItDown («Convertir a Markdown») pide
Magika y `onnxruntime`, que intenta conectarse a `mobile.events.data.microsoft.com`. Pandex no los
instala ni los carga: decide el tipo de archivo por la extensión (spec 004, PRI-10; spec 002, PES-10).

## Borrar tus datos

- **Solo la sesión de Canvas:** Configuración → Tareas → Sincronizar Canvas → **Olvidar mi
  sesión**. Borra los perfiles del navegador de Pandex (también el de Firefox snap) y
  `sesion_canvas.json`; no toca tus cursos, tu historial ni `config.json`. La próxima vez inicias
  sesión otra vez.
- **Todo lo de Pandex:** cierra Pandex y borra la carpeta de datos y `config.json`. Tus cursos
  descargados no se tocan.
  **Desinstalar Pandex…** (Configuración → Comportamiento) hace esto por ti
  ([specs/003](../specs/003_sin_residuos_y_desinstalar/spec.md)).
