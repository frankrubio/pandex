# 010 · Plan

## Enfoque

- `navegador.en_uso(nombre)`: ¿hay un navegador abierto con el perfil de Pandex? Solo lee el
  candado del perfil. En Windows, `lockfile` (Chrome y Edge) o `parent.lock` (Firefox) existe y
  no se puede abrir para escribir. En Linux, el enlace `SingletonLock` (`equipo-pid`) o `lock`
  (`ip:+pid`) apunta a un proceso vivo.
- `navegador.hay_sesion`: además del perfil, pide que ese navegador sea el recordado (o que no
  haya ninguno anotado).
- `_Pestana` y `Contexto`: solo cuentan como cerrado los errores de ventana o sesión inexistente
  (o 10 fallos seguidos). `goto` solo corta por errores de red. `cookies()` reintenta. El user
  agent se lee una vez.
- `sesion._esperar_sesion(..., quieto=6)`: corta si la URL no cambia en 6 s. Registra el sitio y
  la ruta donde se quedó.
- `sesion._entrar_en_ventana_normal`: espera a que el proceso termine **y** el perfil quede
  libre. Si el perfil ya estaba en uso, avisa que Canvas se abrió en esa ventana.

## Archivos que se tocan

| Archivo | Cambio |
|---|---|
| `pandex/canvas/navegador.py` | `en_uso`, `hay_sesion`, errores pasajeros |
| `pandex/canvas/sesion.py` | corte rápido, espera del perfil, motivo en el mensaje |
| `tests/test_navegador.py` | pruebas |
| `docs/sincronizar-canvas.md`, `CHANGELOG.md`, `pandex/__init__.py` | 2.6.2 |

## Riesgos

| Riesgo | Qué se hace |
|---|---|
| Cortar a los 6 s un SSO lento que habría entrado solo | Se abre la ventana. Con la sesión de Google viva, entra solo ahí: la persona solo la cierra. |
| Un candado viejo de un navegador que se cerró mal | En Windows, el archivo se puede abrir: libre. En Linux, el pid ya no existe: libre. |
| El perfil ocupado por un navegador invisible (Pandex cerrado a la fuerza a mitad) | Se avisa que la ventana ya estaba abierta y, si no se ve, que cierres el navegador. El límite de espera sigue. |
| No se probó en Windows real | La CI corre las pruebas en Windows; la prueba con Google se hace con la alumna. |
