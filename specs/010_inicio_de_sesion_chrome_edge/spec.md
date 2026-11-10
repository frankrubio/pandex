# 010 · Iniciar sesión sin trabas en Chrome y Edge

> Estado: en curso  ·  Prefijo de requisitos: `SES`
> Principios que toca: P1 (privacidad), P7 (Windows y Linux igual)

## Por qué

El 04/11/2026 una alumna con Windows probó la 2.6.0 con Chrome y luego con Edge. En el asistente
le salió «No pude abrir el navegador para entrar a Canvas» y no llegó a la ventana para iniciar
sesión. Ese mensaje sale cuando Selenium falla **después** de abrir el navegador. Pasa en el
intento sin ventana, antes de la ventana normal. No hay registro suyo, así que la causa exacta no
está medida. El código tenía cuatro puntos que podían dar ese resultado:

1. Un fallo del intento sin ventana cortaba todo (corregido en la 2.6.1).
2. Un error pasajero de Selenium mientras Canvas redirige al login de la universidad (SSO) se
   tomaba como «cerraste el navegador». Con Playwright eso no pasaba.
3. El intento sin ventana se hacía con cualquier perfil que existiera, aunque nunca se hubiera
   entrado con él. El perfil de Edge que dejó el intento rechazado por Google en la 2.5 cuenta.
   Eran unos 25 s perdidos antes de la ventana.
4. En Chrome y Edge se comprobaba la sesión apenas terminaba el proceso que Pandex abrió. Ese
   proceso puede terminar antes que el navegador: si ya había una ventana con ese perfil, le pasa
   la dirección y sale; también sale cuando el navegador se reinicia para actualizarse. Pandex
   comprobaba con la ventana abierta y el perfil ocupado.

## Qué existe hoy

- `pandex/canvas/sesion.py`: atajo de cookies, luego el navegador sin ventana con el perfil,
  luego la ventana. En Chrome y Edge, la ventana es normal (sin Selenium) y se comprueba al cerrarla.
- `pandex/canvas/navegador.py`: `elegir`, `recordar`/`recordado`, `hay_sesion`, `abrir`,
  `abrir_ventana_normal`.
- `docs/sincronizar-canvas.md`: la cookie de Canvas no sobrevive a cerrar el navegador; el SSO la
  renueva solo en unos segundos.

## Requisitos

| Id | Requisito | Se comprueba con |
|---|---|---|
| SES-01 | Si el intento sin ventana no encuentra la sesión o falla por otro motivo (un perfil viejo, un error de un momento), se sigue con la ventana para iniciar sesión. Si falla porque no hay internet, o falta el navegador, Selenium o su driver, se dice enseguida: la ventana no lo arreglaría. | `tests/test_navegador.py::IniciarSesionConVentanaNormal` (`test_si_el_intento_sin_ventana_falla_se_sigue_con_la_ventana_normal`, `test_sin_red_no_abre_la_ventana`, `test_si_falta_algo_por_instalar_no_abre_la_ventana`) y `::Abrir::test_sin_driver_lo_dice_y_no_se_toma_como_perfil_viejo` |
| SES-02 | El intento sin ventana solo se hace con el navegador con el que ya se entró a Canvas: el anotado, o el Chrome de las versiones 2.x si no hay uno anotado. Con otro, va directo a la ventana. | `tests/test_navegador.py::HaySesion` |
| SES-03 | Si la página se queda 6 s en el mismo lugar sin que la sesión valga (pide iniciar sesión o elegir cuenta), el intento sin ventana termina ahí, sin esperar los 20 s. Si no se puede leer la dirección, el conteo vuelve a empezar. Solo vale para el intento sin ventana: la comprobación tras cerrar la ventana espera los 20 s, porque ya iniciaste sesión. | `tests/test_navegador.py::EsperarSesion`, `::ErroresPasajeros::test_una_lectura_fallida_olvida_la_direccion`, `::IniciarSesionConVentanaNormal::test_tras_la_ventana_no_corta_a_los_6_s` |
| SES-04 | Un error pasajero de Selenium mientras la página redirige no corta el intento. Solo cuenta como cerrado si la ventana o el navegador ya no existen, o si falla 10 veces seguidas. | `tests/test_navegador.py::ErroresPasajeros` |
| SES-05 | En Chrome y Edge, Pandex comprueba la sesión recién cuando el navegador suelta su perfil, no cuando termina el proceso que abrió. Si la ventana de Pandex ya estaba abierta, Canvas se abre en ella y se espera a que la cierres. En Firefox, lo dice. Antes de abrir la ventana, en los tres navegadores, espera a que el navegador sin ventana suelte el perfil. En Linux el candado cuenta solo si su proceso existe y abre ese perfil (tras reiniciar, el número puede ser de otro programa). La carpeta del perfil se busca una vez. | `tests/test_navegador.py::EnUso` y `::IniciarSesionConVentanaNormal` |
| SES-06 | El mensaje genérico de error es corto y sin jerga; el motivo técnico va al registro y al detalle del informe (IU-06, IU-07). El registro dice en qué página se quedó: solo el sitio y la ruta. Nada de lo que va al registro lleva parámetros de direcciones, tampoco los de la ruta (`;jsessionid=`) ni los que traen los errores de Selenium (P1, PRI-03). | `tests/test_navegador.py::EsperarSesion`, `::RegistroSinDatos`, `::IniciarSesionConVentanaNormal::test_el_mensaje_generico_es_corto_y_sin_jerga` |
| SES-08 | Si el perfil lo tiene un navegador sin ventana que quedó abierto, Pandex lo cierra y sigue: nunca le pasa Canvas a una ventana que no se ve. Una ventana que se ve no se cierra. Si es de otra tarea de Pandex que está entrando a Canvas, no la toca y dice que esperes. | `tests/test_navegador.py::ProcesosDelPerfil`, `::IniciarSesionConVentanaNormal` (`test_un_navegador_sin_ventana_que_quedo_abierto_se_cierra`, `test_una_ventana_que_se_ve_no_se_cierra`, `test_si_otra_tarea_esta_entrando_lo_dice`) |
| SES-07 | La ventana para iniciar sesión en Chrome y Edge no lleva puerto de depuración ni otro control remoto: con `--remote-debugging-port`, Chrome marca `navigator.webdriver` y Google rechaza el inicio de sesión. | `tests/test_navegador.py::VentanaNormal::test_la_ventana_normal_no_lleva_ningun_control_remoto` |

## Escenarios

**SES-02 · Edge sin haber entrado nunca con él**
- *Dado* el perfil de Edge que dejó un intento rechazado y Chrome anotado como el de antes
- *Cuando* eliges Edge y conectas
- *Entonces* se abre la ventana de Edge enseguida, sin intento sin ventana.

**SES-03 · La sesión de Google venció**
- *Dado* un perfil con el que ya entraste, pero la sesión de Google venció
- *Cuando* sincronizas
- *Entonces* la ventana para iniciar sesión se abre unos 6 s después del navegador sin ventana, no 20 s.

**SES-05 · La ventana de Pandex ya estaba abierta**
- *Dado* una ventana de Chrome de Pandex abierta de un intento anterior
- *Cuando* reintentas
- *Entonces* Canvas se abre en esa ventana, Pandex dice que la cierres al ver tu Canvas y
  comprueba al cerrarla.

**SES-01 · Sin internet**
- *Dado* un perfil con el que ya entraste y la PC sin internet
- *Cuando* sincronizas
- *Entonces* «No hay conexión: no pude llegar a Canvas.», sin abrir la ventana para iniciar sesión.

**SES-08 · Quedó un navegador sin ventana abierto**
- *Dado* un Edge sin ventana con el perfil de Pandex, de un Pandex que se cerró de golpe
- *Cuando* sincronizas
- *Entonces* Pandex lo cierra y sigue como siempre; no dice «tu ventana ya estaba abierta».

**Error · No entraste**
- *Dado* que cierras la ventana sin iniciar sesión
- *Entonces* «No pude confirmar tu sesión…», y el registro dice en qué página se quedó.

## Fuera de alcance

- Detectar el inicio de sesión con la ventana abierta y cerrarla sola en Chrome y Edge. Necesita
  el puerto de depuración, y con él Google rechaza el inicio de sesión (SES-07).
- El token de acceso de Canvas (pregunta 3 de la spec 001).

## Preguntas abiertas

Ninguna.

## Historial

| Fecha | Cambio | Por qué |
|---|---|---|
| 2026-11-04 | Primera versión. | Error de una alumna con Chrome y Edge en Windows (2.6.0). |
| 2026-11-08 | SES-01, 03, 05 y 06 precisados; SES-08. | Revisión de código de la 2.6.2: sin red se abría la ventana, el corte de 6 s se activaba con lecturas fallidas y tras la ventana, el registro podía guardar `;jsessionid=`, un número de proceso reusado bloqueaba el perfil, un navegador sin ventana recibía Canvas y el mensaje del globo traía jerga. |
