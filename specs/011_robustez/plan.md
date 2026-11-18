# 011 · Plan

## Enfoque

- **ROB-01:** `pandex/errores.py` pone `sys.excepthook` y `threading.excepthook`. Con un
  manejador propio, PyQt6 ya no aborta el proceso. El aviso al usuario pasa por una señal de
  Qt (se puede emitir desde cualquier hilo). Se instala en `main.py`, no en `PandexApp`, para
  no tocar el proceso de las pruebas.
- **ROB-02/03:** `Config.cargar()` valida que el archivo sea un objeto; si no, lo aparta y
  recupera. `_mezclar` ignora un valor que no es objeto donde el valor de fábrica sí lo es.
  Cada arranque con un archivo bueno actualiza la copia `config-ultima-buena.json` (solo si
  cambió). Se descartó «empezar siempre de fábrica»: obliga a rehacer el asistente de Canvas.
- **ROB-04:** `main.py` envuelve la creación de la app; `arranque_fallido()` anota y avisa.
- **ROB-05/06:** `TaskContext` recibe un `threading.Event`; `ctx.cancelada`,
  `ctx.comprobar_cancelacion()` (lanza `tareas.Cancelada`) y `ctx.al_cancelar(f)` (lo que hay
  que cerrar ya: un proceso hijo). El `Ejecutor` traduce `Cancelada` a un resultado
  `{"cancelada": True}`. Las tareas que tardan revisan la cancelación en sus bucles.

## Principios

- **P3:** las copias van a la carpeta de datos y tienen límite (3). Al cancelar se borran los
  `.part`.
- **P4:** cancelar no borra nada que ya esté en la carpeta del usuario.
- **P8:** cada aviso dice qué pasó y qué hacer.
- **P5:** `errores.py` no importa nada pesado; la copia de la configuración es un archivo de
  pocos KB y solo se escribe si cambió.

## Archivos que se tocan

| Archivo | Cambio |
|---|---|
| `pandex/errores.py` | nuevo: manejadores globales |
| `pandex/config.py` | validar, recuperar, `fsync` |
| `main.py` | instala la red; `arranque_fallido()` |
| `pandex/tareas.py`, `pandex/ejecutor.py`, `pandex/app.py` | cancelar y salir limpio |
| `pandex/canvas/sesion.py`, `sincronizar.py`, `cliente.py` | revisan la cancelación |
| `pandex/markdown/proceso.py`, `lote.py`, `tasks/comprimir.py` | ídem |
| `tests/test_robustez.py`, `tests/test_nucleo.py` | pruebas nuevas |
| `docs/arquitectura.md`, `docs/crear-tareas.md`, `docs/privacidad.md`, `docs/ayuda.md` | lo nuevo |

## Medición

Antes (10/11/2026, Linux, PyQt6 6.11.0): error en un `QTimer` → código de salida 134;
`Config()` con archivo vacío → `JSONDecodeError`.

## Riesgos

| Riesgo | Qué se hace |
|---|---|
| Un error que se repite 60 veces por segundo llena el registro | la traza completa solo la primera vez; luego una línea cada 10, 100, 1000 repeticiones |
| Una tarea bloqueada en la red no ve la cancelación | al salir se espera 5 s y se cierra igual; el navegador que quede lo cierra SES-08 la próxima vez |
