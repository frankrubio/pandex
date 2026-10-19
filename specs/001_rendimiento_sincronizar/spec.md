# 001 · Sincronizar Canvas rápido

> Estado: aprobada (con preguntas abiertas)  ·  Prefijo: `REN`  ·  Principios: P6, P2, P1

## Por qué

Sincronizar es lo que más usa un estudiante y lo hace varias veces por semana. Hoy tarda más
de lo que promete la documentación (`docs/sincronizar-canvas.md` dice «~6 s»).

Medido en la PC de Frank (Linux Mint, 9 cursos, 137 archivos, registro del 18/10/2026):

| Corrida | Total | sesión | módulos | consultas | revisar disco | descargas |
|---|---|---|---|---|---|---|
| Primera vez (104 nuevos) | 66 s | 5,3 s | 3,7 s | 10,1 s | 0,0 s | 46,7 s |
| Sin novedades | 11 s | 4,8 s | 3,5 s | 2,5 s | 0,0 s | — |
| Sin novedades | 9 s | 5,1 s | 3,9 s | 0,0 s | 0,0 s | — |
| Sin novedades | 8 s | 4,3 s | 3,7 s | 0,0 s | 0,0 s | — |

Tiempo propio de Pandex en la primera vez (todo menos `descargas`): **19,1 s**. Sin
novedades: **8–11 s**. El cuello de botella es abrir el navegador para renovar la sesión
(~4–5 s) y leer los módulos (~3,5–3,9 s).

## Qué existe hoy

- Fases cronometradas en el registro (`pandex/canvas/sincronizar.py`, `_fases`).
- Historial que evita consultar lo ya conocido (`canvas/historial.py`).
- 6 hilos para la API y 4 para descargas (`HILOS_API`, `HILOS_DESCARGA`).
- Sesión: navegador sin ventana con el perfil guardado, que se cierra al confirmar
  `/api/v1/users/self` (`canvas/sesion.py`).

## Definiciones

- **Tiempo total:** el que muestra el globo final (`· 6 s`).
- **Tiempo propio:** tiempo total menos la fase `descargas`. Es lo que depende de Pandex; la
  transferencia depende de los MB y de tu internet.
- **PC de referencia:** la que se anota en `plan.md` (sistema, CPU, RAM, tipo de conexión).
  Las cifras se toman como la **mediana de 5 corridas**.
- **Escenario tipo:** hasta 10 cursos y 300 archivos en Canvas.

## Requisitos

| Id | Requisito | Se comprueba con |
|---|---|---|
| REN-01 | En la **primera** sincronización del escenario tipo, el tiempo propio es **≤ 10 s**. | medición en PC de referencia + `tests/test_rendimiento.py::Presupuesto::test_primera_vez_tiempo_propio` (Canvas falso con latencia) |
| REN-02 | **Sin novedades**, el tiempo total es **≤ 6 s** con sesión ya guardada. | medición + `test_sin_novedades_total` |
| REN-03 | Con novedades pero **sin necesidad de revisar todo Canvas** (el historial ya conoce los archivos viejos), el tiempo propio es ≤ 6 s. | `test_con_historial_tiempo_propio` |
| REN-04 | Durante `descargas`, siempre hay **al menos 4** descargas en curso mientras queden archivos (no hay esperas en serie). | `test_descargas_en_paralelo` |
| REN-05 | Ninguna fase pide a Canvas algo que el historial ya sabe. | `test_canvas_piezas` (existe) + `test_sin_consultas_repetidas` |
| REN-06 | Si Canvas responde 429/«rate limit», Pandex espera y reintenta sin fallar la sincronización y sin superar el doble del presupuesto. | `test_limite_de_peticiones` |
| REN-07 | Si la sesión venció, el tiempo de iniciar sesión **a mano** no cuenta para REN-01/02 (depende de la persona), pero sí se registra como fase aparte: `inicio de sesión manual`. | `test_fase_login_manual_aparte` |
| REN-08 | Cada sincronización deja en el registro sus fases **y** el número de pedidos a Canvas por fase. | `test_registro_con_pedidos` |
| REN-09 | Ninguna optimización guarda contraseñas ni muestra cookies/tokens en el registro (P1). | `tests/test_principios.py` + revisión del PR |
| REN-10 | `docs/sincronizar-canvas.md` muestra cifras medidas, con fecha y sistema. | revisión |

## Escenarios

**REN-01 · Primera vez**
- *Dado* un usuario recién configurado con 9 cursos y 150 archivos en Canvas, y la sesión
  guardada en el perfil
- *Cuando* pulsa «Sincronizar Canvas»
- *Entonces* las fases `sesión + módulos + consultas + revisar disco` suman ≤ 10 s y el globo
  muestra el total.

**REN-02 · Sin novedades**
- *Dado* que todo ya está en disco y el historial lo sabe
- *Cuando* sincroniza
- *Entonces* el globo dice `✓ Todo al día · … · N s` con N ≤ 6.

**REN-06 · Canvas pide calma**
- *Dado* que Canvas responde 429 a 3 pedidos seguidos
- *Cuando* sincroniza
- *Entonces* reintenta con espera creciente, termina bien y el registro dice cuántas veces
  esperó.

**Error · Sin internet**
- *Dado* que no hay conexión
- *Cuando* sincroniza
- *Entonces* en ≤ 15 s el globo dice «No hay conexión: no pude llegar a Canvas.» y no se
  crea nada en disco.

**Error · La sesión guardada ya no sirve**
- *Dado* que el atajo de sesión (ver plan) devuelve 401
- *Cuando* sincroniza
- *Entonces* cae al navegador sin ventana como hoy, y si tampoco alcanza, abre la ventana
  para iniciar sesión. Nunca falla por culpa del atajo.

## Fuera de alcance

- La velocidad de la red o de Canvas. Una descarga de 500 MB tarda lo que tarde.
- Bajar adjuntos de tareas, anuncios o páginas (sigue siendo «solo archivos de módulos»).
- Cambiar la estructura de carpetas o las reglas de duplicados.

## Preguntas abiertas

| # | Pregunta | Por defecto | Decide |
|---|---|---|---|
| 1 | «10 s cuando descarga todo Canvas»: ¿es el tiempo propio (sin contar la transferencia) o el total? El total no se puede garantizar: 46,7 s de los 66 s medidos fueron solo bajar bytes. | Tiempo propio (REN-01). | Frank |
| 2 | ¿Se acepta guardar las cookies de la sesión en la carpeta de datos (con permisos solo para tu usuario) para no abrir el navegador cada vez? El perfil del navegador ya guarda algo equivalente en la misma carpeta. | Sí, con P1: nunca en el proyecto, nunca en el registro, se borran al desinstalar. | Frank |
| 3 | ¿Se ofrece un **token de acceso de Canvas** opcional (Configuración → Canvas → «Modo rápido»)? Evita el navegador del todo, pero algunas universidades no dejan crearlos y es un dato más sensible. | No por ahora; se evalúa si el atajo de cookies no alcanza REN-02. | Frank |
| 4 | ¿Cuál es la PC de referencia? | La de Frank (Linux Mint) y un runner Windows de la CI para la prueba con Canvas falso. | Frank |

## Historial

| Fecha | Cambio | Por qué |
|---|---|---|
| 2026-10-19 | Primera versión. | Requisitos de Frank: 10 s con descargas, 6 s sin. |
