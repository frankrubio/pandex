# 002 · Tareas

## T002.1 · Medir el peso y vigilarlo en la CI

- **Requisitos:** PES-01, PES-02, PES-03
- **Depende de:** —
- **Prueba primero:** `tests/test_extras.py::MedirPeso`
  - `test_suma_proyecto_venv_y_datos`: con una carpeta falsa de 3 archivos conocidos, el
    total es la suma exacta.
  - `test_excluye_personajes_del_usuario_y_cursos`.
  - `test_limite_falla_con_codigo_1`.
- **Cambio:** `herramientas/medir_peso.py`; `.github/workflows/peso.yml` (base y completo, en
  Windows y Linux; sube el resultado como artefacto).
- **Terminado cuando:** el job corre y publica las cuatro cifras; se anotan en `plan.md`.
  Al principio el job puede marcarse `continue-on-error: true` hasta cerrar T002.4; luego se
  quita.

## T002.2 · Extras en un solo lugar

- **Requisitos:** PES-05, PES-06, PES-09
- **Depende de:** —
- **Prueba primero:** `tests/test_extras.py::Catalogo`
  - `test_instaladores_no_nombran_extras`: `instalar.sh` e `instalar.bat` no contienen
    «Markdown» ni `requirements-markdown.txt`.
  - `test_cada_extra_tiene_su_archivo`: para cada `EXTRAS[id]` existe `requirements-<id>.txt`.
  - `test_instaladores_leen_pandex_extras`: `python -m pandex.extras --preguntar` con
    `PANDEX_EXTRAS=ninguno` no instala nada; con `PANDEX_MARKDOWN=si` instala markdown y avisa
    que la variable es obsoleta (se simula `pip` con `mock`).
- **Cambio:** `pandex/extras.py` (CLI) e instaladores.
- **Terminado cuando:** pruebas en verde; instalar con y sin extras funciona en los dos
  sistemas (CI).

## T002.3 · Quitar un extra desde Configuración

- **Requisitos:** PES-04
- **Depende de:** T002.2
- **Prueba primero:** `tests/test_extras.py::Quitar`
  - `test_instalar_guarda_lo_que_anadio`: con `pip freeze` simulado antes/después, se escribe
    `DATOS/extras/markdown.json` con la diferencia.
  - `test_quitar_extra_borra_sus_paquetes`: `quitar("markdown")` llama a `pip uninstall -y`
    solo con esa lista.
  - `test_instalacion_fallida_se_revierte`.
  - `tests/test_ui.py::test_configuracion_muestra_quitar_si_esta_instalado`.
- **Cambio:** `extras.quitar()`, botón en `ui/configuracion.py` con confirmación.
- **Terminado cuando:** pruebas en verde; job `peso` muestra que tras quitar se vuelve al base
  ± 5 MB.

## T002.4 · Bajar del límite de 600 MB

- **Requisitos:** PES-01
- **Depende de:** T002.1
- **Prueba primero:** el job `peso` con `--limite 600` (hoy falla en Linux: 648 MB).
- **Cambio:** aplicar en orden las opciones a → b → c del plan, una por PR, midiendo cada
  una. Detenerse cuando haya ≥ 30 MB de margen en los dos sistemas. Las opciones d y e
  necesitan el visto bueno de Frank (preguntas abiertas 3 y 4).
- **Terminado cuando:** el job `peso` pasa sin `continue-on-error`.

## T002.5 · Navegador en Windows sin descargas innecesarias

- **Requisitos:** PES-07
- **Depende de:** —
- **Prueba primero:** `tests/test_extras.py::Navegador`
  - `test_windows_prefiere_navegador_instalado`: con Chrome ausente y Edge presente
    (rutas simuladas), se elige `msedge` y no se llama a `playwright install`.
  - `test_chromium_va_a_la_carpeta_de_datos`: si hay que descargarlo,
    `PLAYWRIGHT_BROWSERS_PATH` apunta a `DATOS/navegadores`.
- **Cambio:** `canvas/sesion.py` e `instalar.bat`.
- **Terminado cuando:** pruebas en verde; prueba manual en Windows sin Chrome anotada en el PR.

## T002.6 · Pesos reales en la documentación

- **Requisitos:** PES-08
- **Depende de:** T002.4
- **Cambio:** README («unos N MB»), `docs/linux.md`, mensajes del instalador y
  `EXTRAS[...]["peso_mb"]` con lo que mide la CI.
- **Terminado cuando:** las cifras coinciden con el último artefacto del job `peso`.
