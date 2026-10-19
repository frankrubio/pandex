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
| Fecha de la última búsqueda de actualizaciones | `config.json` (`ultima_busqueda`) | buscar una vez al día como máximo |
| Qué archivo de Canvas está en qué ruta de tu PC | `historial_canvas.json` (carpeta de datos) | no volver a bajar lo que ya tienes |
| Sesión del navegador (cookies) | `browser-profile/` o `browser-profile-firefox/` (carpeta de datos) | entrar a Canvas sin escribir la contraseña |
| Cuentas de OneDrive (el nombre que les pusiste) y su acceso | `onedrive.json`, `rclone.conf` (carpeta de datos) | montar tu OneDrive en Linux |
| Cuándo corrió cada tarea | `ultimas_ejecuciones.json` (carpeta de datos) | ponerse al día si la PC estuvo apagada |
| Movimientos de un reordenamiento | `reordenamientos/` (carpeta de datos) | poder deshacerlo |
| Personajes que añadiste | `personajes/` (carpeta de datos) | mostrarlos |
| Respaldos de actualizaciones | `respaldos/` (carpeta de datos) | volver atrás si algo sale mal |
| Registro de eventos | `logs/pandex.log` (carpeta de Pandex, máx. ~4 MB) | entender qué pasó |

**Carpeta de datos:** `%LOCALAPPDATA%\Pandex` en Windows, `~/.local/share/Pandex` en Linux.

El registro incluye nombres de cursos y de archivos, y rutas de tu PC. Por eso:

- **Antes de pegarlo en un issue, revísalo** y borra lo que no quieras compartir.
- Nunca incluye contraseñas, cookies ni tokens.

## Con quién habla

| Destino | Cuándo | Qué envía |
|---|---|---|
| Tu Canvas (la dirección que escribiste) | al configurar y sincronizar | pedidos de lectura de la API con tu sesión, y descargas |
| GitHub (`raw.githubusercontent.com`, `codeload.github.com`; `github.com` con `git pull`) | al buscar actualizaciones (una vez al día como máximo; se puede apagar) | nada tuyo: solo lee la versión y las novedades, y descarga el código |
| PyPI (`pypi.org`, `files.pythonhosted.org`) | al instalar o actualizar Pandex o una función opcional | nada tuyo: descarga paquetes |

Programas que Pandex abre y que hablan por su cuenta:

| Programa | Con quién | Cuándo |
|---|---|---|
| Tu navegador (Chrome en Windows, o el Chromium de Playwright si no tienes Chrome; Firefox en Linux) con el perfil de Pandex | Canvas y el inicio de sesión de tu universidad | al iniciar sesión |
| Selenium Manager (Linux) | GitHub, para bajar `geckodriver` (~3 MB) | la primera vez que inicias sesión |
| rclone (Linux) | Microsoft | si conectas OneDrive |

## Borrar tus datos

- **Solo la sesión de Canvas:** borra las carpetas `browser-profile*` de la carpeta de datos
  (con el Firefox de snap, la sesión está en `~/snap/firefox/common/pandex-perfil`).
- **Todo lo de Pandex:** cierra Pandex y borra la carpeta de datos y `config.json`. Tus cursos
  descargados no se tocan.
- Cuando exista el desinstalador ([specs/003](../specs/003_sin_residuos_y_desinstalar/spec.md)),
  hará esto por ti.
