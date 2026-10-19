# 001 · Plan

## Enfoque

Primero **medir bien**, luego atacar las dos fases que más pesan, de la más rentable a la
menos. Cada paso se mide antes y después; si un paso no mejora, se descarta.

1. **Medición fina** (REN-08): contar pedidos por fase y separar el inicio de sesión manual
   (REN-07). Sin esto no se sabe qué optimizar.
2. **Atajo de sesión** (REN-02, la mayor ganancia, ~4 s): al terminar un inicio de sesión
   válido se guardan las cookies en `DATOS/sesion_canvas.json`. La siguiente vez se prueba
   `GET /api/v1/users/self` con `requests` (≈0,3 s). Si responde 200, no se abre el
   navegador. Si responde otra cosa, se borra el archivo y se sigue como hoy (navegador sin
   ventana → ventana).
   - Permisos: `0600` en Linux; en Windows, la carpeta de usuario ya es privada.
   - El registro dice «sesión: atajo» o «sesión: navegador», nunca el contenido.
   - Hay que medir **cuánto dura** la sesión de Canvas en UTEC (spike T001.2): si caduca en
     minutos, el atajo no sirve y se pasa a la pregunta abierta 3 (token).
3. **Módulos** (REN-02/03, ~3,5 s): hoy son 9 cursos con 6 hilos (dos tandas). Pasos, en
   orden, midiendo cada uno:
   - `HILOS_API` = número de cursos, con tope de 10.
   - Una sola conexión HTTP reutilizada por hilo ya existe; verificar que no se abre una
     sesión TLS nueva por pedido.
   - Pedir `/courses` y los módulos en cuanto haya cookies (sin esperar a cerrar el
     navegador).
4. **Consultas en la primera vez** (REN-01, 10,1 s para 104 archivos): subir la concurrencia
   de forma adaptativa leyendo `X-Rate-Limit-Remaining` de Canvas (bajar si cae de 200,
   subir hasta 12 si sobra), y probar primero `/courses/{id}/files` cuando Canvas lo permita
   (ya existe el intento; recordar en el historial qué cursos lo permiten).
5. **Descargas** (REN-04): mantener 4 simultáneas como piso; no subir sin medir (más hilos
   no aceleran si la red ya está llena).

Alternativas descartadas:

- *Mantener el navegador abierto entre sincronizaciones:* gasta 150–300 MB de memoria todo
  el día (rompe P5).
- *Raspar HTML en vez de la API:* más lento y frágil (ver `docs/arquitectura.md`).

## Principios

- P1: el archivo de cookies vive solo en `DATOS`, nunca en el proyecto ni en el registro; se
  borra al cerrar sesión, al fallar y al desinstalar (003).
- P3: no se crean cachés fuera de `DATOS`.
- P5: no se añaden dependencias.

## Archivos que se tocan

| Archivo | Cambio |
|---|---|
| `pandex/canvas/sesion.py` | atajo de cookies (`intentar_atajo`, `guardar_atajo`, `olvidar_atajo`) |
| `pandex/canvas/cliente.py` | contador de pedidos; lectura de `X-Rate-Limit-Remaining` |
| `pandex/canvas/sincronizar.py` | fases con pedidos; `HILOS_API` dinámico; fase `inicio de sesión manual` |
| `tests/apoyo.py` | `CanvasFalso.latencia` (segundos por pedido) y `limite` (simular 429) |
| `tests/test_rendimiento.py` | nuevo |
| `docs/sincronizar-canvas.md` | tabla de fases con cifras medidas y fecha |

No se tocan: `destinos.py`, `estructura.py`, `adoptar.py` (las reglas de dónde va cada
archivo no cambian).

## Medición

- **Automática (CI, Windows y Linux):** Canvas falso con `latencia = 0,15 s` por pedido,
  10 cursos, 300 archivos, sesión simulada. Presupuestos: primera vez, tiempo propio ≤ 10 s;
  sin novedades ≤ 6 s. Es una cota del **diseño** (cuántas tandas de pedidos hay), no de la
  red real.
- **Manual (PC de referencia):** 5 corridas sin novedades y 1 primera vez con
  `historial_canvas.json` borrado. Se copian las líneas `fases:` al PR.

| Antes (18/10/2026, Linux) | sesión | módulos | consultas | total |
|---|---|---|---|---|
| Sin novedades (mediana de 3) | 4,8 s | 3,7 s | 0,0 s | 9 s |
| Primera vez | 5,3 s | 3,7 s | 10,1 s | 66 s (19,1 s propio) |

## Riesgos

| Riesgo | Qué se hace |
|---|---|
| La sesión de Canvas caduca muy rápido y el atajo casi nunca sirve | Spike T001.2 antes de programar; si no sirve, se discute el token (pregunta 3). |
| Subir la concurrencia provoca 429 | Concurrencia adaptativa + REN-06. |
| La prueba con latencia es inestable en la CI | Medir con `time.monotonic`, márgenes del 20 % y repetir 3 veces tomando la mediana. |
| La cookie robada de `DATOS` da acceso a Canvas | Mismo riesgo que el perfil del navegador, que ya está ahí. Permisos `0600` y borrado al desinstalar. Se documenta en `docs/privacidad.md`. |
