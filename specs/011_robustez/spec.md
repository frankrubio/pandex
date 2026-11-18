# 011 · Robustez: Pandex no se cae ni se queda colgado

> Estado: en curso  ·  Prefijo de requisitos: `ROB`
> Principios que toca: P3, P4, P8

## Por qué

Pandex se abre con `pythonw` (sin consola): si algo falla al arrancar o en la interfaz, la
mascota desaparece y nadie sabe por qué. En la revisión del 10/11/2026 (Linux, PyQt6 6.11.0)
se reprodujo:

- un error no controlado en un clic o en un reloj **cierra Pandex de golpe** (Qt aborta el
  proceso, código 134), porque no hay un manejador global de errores;
- un `config.json` vacío, cortado o con una sección de otro tipo hace que **Pandex no abra**
  (`JSONDecodeError` o `AttributeError` antes de mostrar la mascota);
- una tarea en curso **no se puede cancelar** (un inicio de sesión espera hasta 5 minutos), y
  «Salir» cierra sin esperar al hilo de la tarea (`Ejecutor.esperar` existe y nadie la llama).

## Qué existe hoy

- `pandex/ejecutor.py` atrapa los errores de `run(ctx)` y de `preparar(ctx)`; `app.py`, los de
  `configurar` y `necesita_configurar`. Lo demás (ventanas, relojes, señales) no tiene red.
- `pandex/config.py` guarda con archivo temporal y `replace`, pero sin `fsync`, y lee sin
  validar.
- `pandex/limpieza.py::limitar` ya limita las copias que se acumulan (RES-04, RES-05).

## Requisitos

| Id | Requisito | Se comprueba con |
|---|---|---|
| ROB-01 | Un error que nadie atrapó en la interfaz (un clic, un reloj, una señal) o en un hilo **no cierra Pandex**: queda en el registro con su traza y la mascota lo avisa una vez (como mucho un globo cada 30 s; un error que se repite no llena el registro). | `tests/test_robustez.py::ErroresInesperados` |
| ROB-02 | Si `config.json` está vacío, cortado, no es un objeto o trae una sección de otro tipo, Pandex **abre igual**: usa la última configuración buena (`DATOS/config-ultima-buena.json`) o, si no hay, los valores de fábrica. El archivo dañado se guarda en `DATOS/config-danado-<fecha>.json` (quedan 3) y la mascota dice qué pasó. | `tests/test_robustez.py::ConfiguracionDanada` |
| ROB-03 | `config.json` se guarda de forma que un corte de luz no lo deje vacío (temporal + `fsync` + `replace`). | `::ConfiguracionDanada::test_guardar_fuerza_la_escritura` |
| ROB-04 | Si Pandex no puede arrancar, no muere en silencio: lo anota en el registro y muestra una ventana que dice qué hacer. Sin persona delante (`--test`, `--pendientes`) solo lo anota y sale con código 1. | `tests/test_robustez.py::ArranqueFallido` |
| ROB-05 | Mientras corre una tarea, el menú ofrece **Cancelar «tarea»**. La tarea para en su siguiente paso (entre archivos, en cada trozo de una descarga, en cada vuelta de la espera del inicio de sesión), cierra lo que abrió (navegador, proceso de conversión, temporales) y la mascota dice «Cancelé…». Lo que ya se guardó se queda (P4). | `tests/test_robustez.py::Cancelar` |
| ROB-06 | «Salir» con una tarea corriendo la cancela y espera hasta 5 s a que termine antes de cerrar. Si no termina, Pandex se cierra igual y lo anota. | `::Cancelar::test_salir_cancela_y_espera` |
| ROB-07 | Un error en un gancho de una tarea (`preparar`, `configurar`, `necesita_configurar`) no tumba la app (007, EXT-08). | `tests/test_nucleo.py::Ganchos` |

## Escenarios

**ROB-01 · Un error en un clic**
- *Dado* Pandex abierto
- *Cuando* un botón lanza un error que nadie esperaba
- *Entonces* Pandex sigue abierto, el registro tiene la traza y el globo dice «Algo falló y lo
  anoté. Si se repite, mira «Ver registro».»

**ROB-02 · El archivo de configuración quedó vacío**
- *Dado* un `config.json` de 0 bytes y una copia buena de ayer
- *Cuando* se abre Pandex
- *Entonces* abre con la copia de ayer, guarda el vacío en la carpeta de datos y avisa:
  «Tu configuración estaba dañada. Recuperé la última copia buena.»

**ROB-02 · Dañado y sin copia**
- *Entonces* abre con los valores de fábrica, avisa y vuelve a ofrecer el asistente de Canvas.

**ROB-05 · Cancelar un inicio de sesión**
- *Dado* Pandex esperando a que inicies sesión en Canvas
- *Cuando* eliges «Cancelar «Sincronizar Canvas»»
- *Entonces* el navegador de Pandex se cierra y el globo dice «Cancelé «Sincronizar Canvas».»

**Error · La tarea no responde al salir**
- *Cuando* pasan 5 s sin que la tarea termine
- *Entonces* Pandex se cierra y el registro dice que la tarea no alcanzó a terminar.

## Fuera de alcance

- Reanudar una descarga cortada (se vuelve a bajar en la siguiente sincronización).
- Cancelar un PDF que Ghostscript ya empezó a aligerar: se cancela al terminar ese archivo.
- Reparar a mano un `config.json` dañado: se guarda la copia para quien quiera mirarla.

## Preguntas abiertas

Ninguna.

## Historial

| Fecha | Cambio | Por qué |
|---|---|---|
| 2026-11-10 | Primera versión. | Revisión del proyecto: tres fallos reproducidos (ver «Por qué»). Frank pidió corregirlos. |
