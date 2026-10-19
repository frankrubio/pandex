# 004 · Privacidad y datos mínimos

> Estado: aprobada  ·  Prefijo: `PRI`  ·  Principios: P1, P3

## Por qué

Pandex es un repositorio **público**: cualquiera puede leer el código, copiarlo y mandar
cambios. Los datos de quien lo usa (su Canvas, sus cursos, su sesión) nunca deben llegar a
GitHub, ni por un `git add .` descuidado, ni por un issue con el registro pegado, ni por un
PR de un tercero que «solo agrega un log».

## Qué existe hoy

- `config.json`, `logs/` y notas personales están en `.gitignore`.
- La sesión, el historial y los temporales viven fuera del proyecto, en `DATOS`.
- La plantilla de issue pide revisar el registro antes de pegarlo.
- Pandex no ve contraseñas: inicias sesión en el navegador.
- `GET /api/v1/users/self` se usa solo para saber si la sesión es válida (código 200).

## Qué datos guarda Pandex (el inventario completo)

| Dato | Dónde | Para qué | ¿Personal? |
|---|---|---|---|
| Dirección de Canvas | `config.json` | saber a qué Canvas hablar | bajo |
| Carpeta destino y carpetas de cursos | `config.json` | dónde guardar | medio (rutas de tu PC) |
| Ids y nombres de cursos, secciones | `config.json` | ordenar | medio |
| Preferencias de la mascota | `config.json` | apariencia | no |
| Qué archivo de Canvas está en qué ruta | `DATOS/historial_canvas.json` | no volver a bajar | medio |
| Sesión del navegador (cookies) | `DATOS/browser-profile*` | entrar sin contraseña | **alto** |
| Cuentas de OneDrive (nombre que les diste) y su configuración de rclone | `DATOS/onedrive.json`, `DATOS/rclone.conf` | montar OneDrive | **alto** (tokens de rclone) |
| Registro de eventos | `logs/pandex.log` | depurar | medio (nombres de archivos y cursos) |

Lo que Pandex **no** guarda ni pide: tu nombre, correo, código de alumno, notas, contraseñas,
mensajes de Canvas.

## Requisitos

| Id | Requisito | Se comprueba con |
|---|---|---|
| PRI-01 | `.gitignore` excluye `config.json`, `logs/` y cualquier archivo de datos personales. | `tests/test_principios.py::Privacidad::test_gitignore_cubre_datos_personales` ✅ |
| PRI-02 | Ningún archivo versionado es un archivo de datos personales (`config.json`, `*.log`, historial, perfiles, cookies, `rclone.conf`, inventario, sesión). | `test_repositorio_sin_archivos_personales` ✅ |
| PRI-03 | El registro nunca contiene valores de cookies, tokens, cabeceras `Authorization` ni el cuerpo de `/users/self`. | `tests/test_privacidad.py::test_registro_sin_secretos` |
| PRI-04 | Pandex solo se conecta a: el host de `canvas_url`; GitHub (`raw.githubusercontent.com`, `codeload.github.com`, y `github.com` mediante `git pull`) al buscar actualizaciones; PyPI solo al instalar funciones opcionales. Los programas externos que Pandex abre (el navegador para el SSO, rclone para Microsoft, Selenium Manager para bajar `geckodriver`) se listan en `docs/privacidad.md`. Cualquier host nuevo requiere cambiar esta spec. | `test_solo_hosts_permitidos` (se simula `requests` y se registran los hosts) |
| PRI-05 | **Ver registro → Copiar para un issue** copia el registro con tu carpeta personal reemplazada por `~`, tu usuario del sistema por `usuario` y la dirección de Canvas por `canvas`. | `test_registro_anonimizado` |
| PRI-06 | En Linux, los archivos sensibles de `DATOS` (sesión, `rclone.conf`, `sesion_canvas.json`) tienen permisos `0600` y sus carpetas `0700`. | `test_permisos_de_archivos_sensibles` |
| PRI-07 | Configuración → Canvas → **Olvidar mi sesión** borra el perfil del navegador y cualquier atajo de sesión, sin tocar cursos ni historial. | `test_olvidar_sesion` |
| PRI-08 | `docs/privacidad.md` lista cada dato guardado; toda clave nueva de `config.json` aparece ahí. | `test_claves_de_config_documentadas` |
| PRI-09 | La CI corre un escáner de secretos sobre cada PR (p. ej. `gitleaks`) y falla si encuentra uno. | job `secretos` |

✅ = la prueba ya existe y pasa.

## Escenarios

**PRI-02 · Un `git add .` descuidado**
- *Dado* un clon con `config.json`, `logs/` y `.venv`
- *Cuando* alguien hace `git add . && git status`
- *Entonces* ninguno aparece para subir.

**PRI-05 · Reportar un error**
- *Dado* un registro con `/home/frank/OneDrive - UTEC/…` y `https://utec.instructure.com`
- *Cuando* el usuario pulsa «Copiar para un issue»
- *Entonces* el portapapeles tiene `~/OneDrive - UTEC/…` y `canvas`, y un aviso dice «Revisa
  que no quede nada personal antes de pegarlo».

**Error · Un PR agrega un `log` con la cookie**
- *Cuando* la CI corre `test_registro_sin_secretos`
- *Entonces* falla con la línea exacta.

## Fuera de alcance

- Cifrar `config.json` (no tiene secretos).
- Proteger la PC del usuario contra otros programas con su misma cuenta.

## Preguntas abiertas

| # | Pregunta | Por defecto | Decide |
|---|---|---|---|
| 1 | ¿Anonimizar también los nombres de cursos al copiar el registro? Ayudan mucho a depurar. | No; el aviso pide revisarlos. | Frank |

## Historial

| Fecha | Cambio | Por qué |
|---|---|---|
| 2026-10-19 | Primera versión. | Repo público; requisito de Frank: solo datos necesarios. |
