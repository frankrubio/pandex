# Principios de Pandex

Son las reglas del proyecto. Ninguna spec, plan, tarea ni PR puede romperlas; si una idea
choca con una de ellas, se cambia la idea o se propone cambiar el principio en un issue
aparte, con Frank. Cada principio tiene una forma de comprobarlo.

**Objetivo de Pandex:** automatizar tareas típicas de estudiantes. Lo central es bajar el
material de Canvas y ordenarlo de forma inteligente; lo demás (Convertir a Markdown,
Comprimir carpeta, tareas futuras) son funciones de apoyo.

## P1. Privacidad: solo lo necesario, y nunca en GitHub

- Pandex guarda **solo** lo que necesita para funcionar: la dirección de tu Canvas, la
  carpeta destino, tus cursos y tus preferencias. Nada de nombre, correo, código de alumno,
  notas ni contraseñas.
- **Nunca ve tu contraseña.** El inicio de sesión ocurre en el navegador; Pandex solo usa la
  sesión que queda en su perfil propio.
- Los datos viven en tu PC: `config.json` y `logs/` (ignorados por git) y la carpeta de datos
  (`%LOCALAPPDATA%\Pandex` o `~/.local/share/Pandex`). **Nada de eso se sube a GitHub.**
- Sin telemetría, sin servidores propios, sin IA en la nube. Pandex solo habla con tu Canvas
  y, cuando buscas actualizaciones, con GitHub.
- El registro no guarda tokens, cookies ni contraseñas.

*Se comprueba con:* `tests/test_principios.py` y [004_privacidad_y_datos](004_privacidad_y_datos/spec.md).

## P2. No toca tu sistema

- No cambia configuraciones del sistema, no instala nada global y no pide `sudo` ni permisos
  de administrador. Todo lo de Python va en `.venv`, dentro de la carpeta de Pandex.
- Lo que el sistema necesita (Python, Firefox, rclone, Tesseract…) lo instalas tú; Pandex
  solo te dice el comando.
- Accesos directos, arranque automático y el «despertador» se crean **solo si los pides**, y
  se quitan desde Pandex o al desinstalar.
- Puede **leer** tu configuración (modo oscuro, carpeta de OneDrive, navegador instalado,
  idioma, escala de pantalla) para adaptarse. **Leer no es cambiar.**

## P3. Sin residuos

Pandex solo escribe en estos lugares. Fuera de esta lista, nada.

| Lugar | Windows | Linux | Cuándo |
|---|---|---|---|
| Carpeta del proyecto | `…\pandex\` (incluye `.venv`, `config.json`, `logs\`) | `~/pandex/` | siempre |
| Carpeta de datos | `%LOCALAPPDATA%\Pandex\` | `~/.local/share/Pandex/` | siempre |
| Carpeta de tus cursos | la que elegiste | la que elegiste | al sincronizar (solo crea) |
| Accesos directos | Escritorio, menú Inicio, carpeta *Inicio* | Escritorio, `~/.local/share/applications`, `~/.config/autostart` | si los pides |
| Despertador | tarea programada «Pandex» | `~/.config/systemd/user/pandex.{service,timer}` | si lo activas |
| Perfil de Firefox snap | — | `~/snap/firefox/common/pandex-perfil` | solo con el Firefox de snap (no puede leer carpetas ocultas) |
| OneDrive con rclone | — | `~/OneDrive*` (punto de montaje) | si lo conectas |

- La carpeta temporal del sistema solo se usa con `tempfile.TemporaryDirectory()` (se borra
  sola al terminar, también si hay un error). Nada de `mkdtemp` ni archivos sueltos ahí.
- **Cachés y descargas auxiliares** (pip, geckodriver, navegadores de Playwright) van dentro
  de la carpeta de datos o no se guardan.
- Lo que se acumula (registros, respaldos, temporales, diarios) tiene **límite** y se limpia
  solo.
- **Desinstalar** deja la PC como estaba antes de instalar, salvo la carpeta de tus cursos.

*Se comprueba con:* [003_sin_residuos_y_desinstalar](003_sin_residuos_y_desinstalar/spec.md).

## P4. Nada destructivo

- Sincronizar **solo crea** archivos: nunca borra, mueve, sobrescribe ni renombra lo tuyo.
- Mover (reordenar) solo con vista previa, confirmación y **deshacer**.
- Una tarea que borre o mueva cosas del usuario lo pregunta en `preparar(ctx)`.

## P5. Liviano

| Presupuesto | Límite | Cómo se mide |
|---|---|---|
| Instalación completa (con todas las funciones opcionales) | **≤ 600 MB** | `herramientas/medir_peso.py` (ver 002) |
| Instalación base (sin opcionales) | ≤ 350 MB | ídem |
| Memoria en reposo | ≤ 80 MB | `docs/arquitectura.md#rendimiento` |
| CPU en reposo | 0 % (sin temporizadores) | ídem |
| Arranque hasta ver la mascota | ≤ 1 s | `main.py --test` cronometrado |

- Lo opcional (hoy «Convertir a Markdown») se instala aparte y **solo si lo eliges**. Una
  tarea opcional que no está instalada no aparece en el menú.
- Lo pesado se importa dentro de la función que lo usa, nunca al arrancar.

## P6. Rápido

| Presupuesto | Límite |
|---|---|
| Sincronizar sin novedades (total, medido en el globo) | **≤ 6 s** |
| Sincronizar con descargas: tiempo propio de Pandex (todo menos la transferencia) | **≤ 10 s** |
| Respuesta de la interfaz a un clic | ≤ 100 ms (nada pesado en el hilo de la interfaz) |

Los números se miden, no se suponen: cada sincronización deja sus fases en el registro
(`fases: sesión 4.3s · módulos 3.7s · …`). Detalle en
[001_rendimiento_sincronizar](001_rendimiento_sincronizar/spec.md).

## P7. Igual en Windows y en Linux

- Misma función, mismos textos, mismo resultado en disco. Lo que depende del sistema va
  detrás de `rutas.WINDOWS` y tiene su prueba en los dos.
- Un instalador por sistema (`instalar.bat`, `instalar.sh`) y su desinstalador.
- La CI corre en Windows y Ubuntu, con las versiones de Python soportadas.
- Dependencias con versión fija (`==`) y marcadores de plataforma (`; sys_platform == …`):
  nunca se instala en un sistema lo que solo sirve en el otro.

## P8. Simple para quien lo usa

- Español de Perú neutro, frases cortas, sin jerga técnica. Toda hora en 12 horas
  (`pandex/horas.py`).
- Todo se configura desde la interfaz, con valores por defecto que ya funcionan. **Nunca** se
  le pide al usuario editar `config.json`.
- Cada mensaje de error dice **qué pasó y qué hacer**. El detalle técnico va a «Ver registro».
- Interfaz bonita, simple, concisa y funcional: ver
  [005_interfaz_y_configuracion](005_interfaz_y_configuracion/spec.md).

## P9. Simple para quien programa

- Núcleo genérico en `pandex/`; funciones en `tasks/` (delgadas) con su lógica en `pandex/`.
- Pruebas sin internet ni datos reales (`PANDEX_DATOS` temporal, Canvas falso).
- Convenciones en [docs/convenciones.md](../docs/convenciones.md). Cambios pequeños, uno por
  PR, con su prueba y su línea de `CHANGELOG.md`.
- Nada de refactorizar por gusto: se corrigen errores reales y se cumplen specs.

## P10. Licencias claras

- Código MIT. Toda imagen, sonido o dependencia nueva debe tener una licencia que permita
  redistribuirla en un repositorio público, y su crédito en `assets/CREDITS.md`.
- Ante la duda sobre un personaje de terceros (marca o franquicia), no se incluye en el
  repositorio: el usuario puede añadirlo en su PC con «Añadir personaje…».
