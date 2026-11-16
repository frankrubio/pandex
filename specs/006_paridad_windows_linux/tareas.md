# 006 · Tareas

## T006.0 · Dependencias fijas y por sistema ✅

- **Requisitos:** PLA-06
- **Hecho:** `tests/test_principios.py::Dependencias`.
- PLA-07 (desinstaladores) se cumple con T003.7.

## T006.1 · Matriz completa en la CI

- **Requisitos:** PLA-01
- **Depende de:** —
- **Prueba primero:** la CI misma: el PR debe mostrar 9 jobs (3 sistemas × 3 versiones).
- **Cambio:** `pruebas.yml`. Si 3.14 falla, se abre una tarea por cada error y se corrige el
  comentario de `requirements.txt` hasta que pase.
- **Terminado cuando:** los 9 jobs en verde.

## T006.2 · La CI ejecuta los instaladores

- **Requisitos:** PLA-02
- **Depende de:** T002.2 (`PANDEX_EXTRAS`)
- **Prueba primero:** job `instaladores` que hoy fallaría si un instalador tuviera un error
  (comprobar rompiendo a propósito una línea en una rama de prueba).
- **Cambio:** `.github/workflows/instaladores.yml`.
- **Terminado cuando:** corre en Windows y Ubuntu, con y sin Markdown.
- **Hecho en la rama:** el job corre los dos instaladores con `PANDEX_MARKDOWN=no` (Python del
  sistema) y `=si` (Python portátil), comprueba que `instalar.sh` no deja nada nuevo en `~/.cache`
  y abre Pandex con `main.py --test`. Falta verlo en verde en la CI (y la prueba de romper una línea
  a propósito).

## T006.3 · Python portátil cuando no hay Python 3.12+ (Linux y Windows)

- **Requisitos:** PLA-03
- **Depende de:** T006.2; pregunta abierta 1 (resuelta: Python portátil, sí)
- **Prueba primero:** `tests/test_instaladores.py` (huellas fijas y `python_portatil.sh` con un
  `curl` falso: descarga, huella distinta, «no», equipo sin portátil, archivo sin Python) y el job
  `instaladores` con `PANDEX_PYTHON=portatil`.
- **Cambio:** `herramientas/python_portatil.{txt,sh,bat}`, `instalar.sh`, `instalar.bat`,
  `.gitignore`, `actualizar.PROTEGIDOS`, desinstaladores, `medir_peso.py`, docs.
- **Terminado cuando:** las pruebas pasan, el job pasa en los dos sistemas y no deja nada en
  `~/.cache`.

## T006.4 · Mismo árbol en los dos sistemas

- **Requisitos:** PLA-04
- **Depende de:** —
- **Prueba primero:** `tests/test_paridad.py::test_mismo_arbol` + `tests/datos/arbol_esperado.txt`
  generado una vez en Linux y revisado a mano.
- **Cambio:** solo si Windows da otro árbol.
- **Terminado cuando:** pasa en los dos sistemas.

## T006.5 · Rutas con espacios, tildes y ñ

- **Requisitos:** PLA-05
- **Depende de:** —
- **Prueba primero:** `test_rutas_raras` (sincronizar, convertir a Markdown con un `.txt`,
  comprimir y crear acceso directo dentro de `OneDrive - Año Diseño`).
- **Cambio:** solo si falla.
- **Terminado cuando:** pasa en los dos sistemas.

## T006.6 · Plantilla de issue y sistemas no soportados

- **Requisitos:** PLA-08, PLA-09, PLA-10
- **Depende de:** —
- **Cambio:** `error.yml` con sistema operativo; README con «Funciona en / No funciona en»;
  mensajes claros en instaladores para ARM y macOS.
- **Terminado cuando:** revisión de Frank.

## T006.7 · Un solo Pandex: también el despertador y las copias de antes

- **Requisitos:** PLA-11, PLA-12
- **Depende de:** —
- **Prueba primero:** en `tests/test_linux.py`, que instalar otra copia reescriba
  `pandex.service` con la carpeta nueva (y no lo cree si no estaba), que reconozca una copia
  sin `instalacion.json` por el `Path=` del menú, y su par en Windows con PowerShell simulado.
- **Cambio:** `despertador.mover_aqui()` (solo cambia qué se abre, no los horarios) y
  `accesos.instalacion_anterior()` con la lectura de los accesos; versión 2.4.1.
- **Terminado cuando:** las pruebas pasan en Windows y Ubuntu.
