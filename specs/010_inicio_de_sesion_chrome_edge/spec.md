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
| SES-01 | Si el intento sin ventana falla, se sigue con la ventana para iniciar sesión. | `tests/test_navegador.py::IniciarSesionConVentanaNormal::test_si_el_intento_sin_ventana_falla_se_sigue_con_la_ventana_normal` |
| SES-02 | El intento sin ventana solo se hace con el navegador con el que ya se entró a Canvas: el anotado, o el Chrome de las versiones 2.x si no hay uno anotado. Con otro, va directo a la ventana. | `tests/test_navegador.py::HaySesion` |
| SES-03 | Si la página se queda 6 s en el mismo lugar sin que la sesión valga (pide iniciar sesión o elegir cuenta), el intento sin ventana termina ahí, sin esperar los 20 s. | `tests/test_navegador.py::EsperarSesion` |
| SES-04 | Un error pasajero de Selenium mientras la página redirige no corta el intento. Solo cuenta como cerrado si la ventana o el navegador ya no existen, o si falla 10 veces seguidas. | `tests/test_navegador.py::ErroresPasajeros` |
| SES-05 | En Chrome y Edge, Pandex comprueba la sesión recién cuando el navegador suelta su perfil, no cuando termina el proceso que abrió. Si la ventana de Pandex ya estaba abierta, Canvas se abre en ella y se espera a que la cierres. En Firefox, lo dice. | `tests/test_navegador.py::EnUso` y `::IniciarSesionConVentanaNormal` |
| SES-06 | El mensaje genérico de error trae el motivo técnico en una línea. El registro dice en qué página se quedó: solo el sitio y la ruta, sin parámetros (P1). | `tests/test_navegador.py::EsperarSesion`, `::IniciarSesionConVentanaNormal` |
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
