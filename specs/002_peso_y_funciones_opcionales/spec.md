# 002 · Peso máximo y funciones opcionales

> Estado: aprobada (con preguntas abiertas)  ·  Prefijo: `PES`  ·  Principios: P5, P3, P7

## Por qué

Pandex tiene que caber en la PC de cualquier estudiante: **máximo 600 MB con todo**. Quien no
quiere «Convertir a Markdown» (u otra función futura) no la descarga y el sistema queda más
liviano.

Medido el 19/10/2026 en Linux (entorno virtual limpio, Python 3.13, `pip --no-cache-dir`):

| Instalación | Peso de `.venv` |
|---|---|
| Base (`requirements.txt`) | **341 MB** |
| Base + «Convertir a Markdown» | **648 MB** (se pasa por 48 MB) |

Lo que más pesa (Linux): PyQt6 261 MB (de eso, unos 172 MB son librerías de Qt, y muchas no
se usan: Quick, QML, 3D, Pdf, Designer, multimedia), pandas 72 MB, numpy 70 MB, onnxruntime
68 MB (lo trae `magika`, el modelo de MarkItDown **que Pandex no usa**), selenium 34 MB.

En Windows **no se ha medido** una instalación real. Lo que se sabe de los paquetes
descomprimidos: PyQt6 + Qt ≈ 217 MB y Playwright ≈ 110 MB (más el Chromium que descarga si no
tienes Chrome). Es probable que Windows pese más que Linux.

## Qué existe hoy

- `pandex/extras.py`: catálogo `EXTRAS` con «markdown»; una tarea declara `requiere = "markdown"`
  y no aparece si no está instalado. Se instala desde Configuración → Tareas.
- `instalar.sh` / `instalar.bat` preguntan por «Convertir a Markdown» (el nombre está escrito
  a mano en los dos).
- No hay forma de **quitar** un extra, ni de medir el peso.

## Definición de «peso de Pandex»

Suma de: la carpeta del proyecto (incluye `.venv`) + la carpeta de datos **sin** contar
`personajes/` añadidos por el usuario + todo navegador o driver que Pandex haya descargado.
**No** cuenta: Python del sistema, tu Chrome/Firefox/Edge, la carpeta de tus cursos.

## Requisitos

| Id | Requisito | Se comprueba con |
|---|---|---|
| PES-01 | Con **todas** las funciones opcionales, el peso es **≤ 600 MB** en Windows y en Linux. | `herramientas/medir_peso.py` en la CI (job `peso`) |
| PES-02 | Sin funciones opcionales, el peso es **≤ 350 MB** en Windows y en Linux. | ídem |
| PES-03 | Sin una función opcional, **ninguno** de sus paquetes está instalado. | job `peso` de la CI: `medir_peso.py --base` falla si `pip freeze` incluye `markitdown`, `pandas`, `onnxruntime`… |
| PES-04 | Cada función opcional se puede **instalar y quitar** desde Configuración → Tareas, y quitarla libera su espacio (vuelve al peso base ± 5 MB). | `test_quitar_extra_borra_sus_paquetes` + job `peso` |
| PES-05 | Una función opcional nueva se declara en **un solo lugar** (`EXTRAS` + su `requirements-<id>.txt`); instaladores, Configuración y menú la recogen solos, sin editar `.sh` ni `.bat`. | `test_instaladores_no_nombran_extras` |
| PES-06 | Los instaladores preguntan por cada función opcional con su **peso medido**; la respuesta por defecto es «no». Sin preguntar: `PANDEX_EXTRAS=markdown` o `PANDEX_EXTRAS=ninguno`. | `test_instaladores_leen_pandex_extras` + prueba manual |
| PES-07 | En Windows no se descarga un navegador si hay Chrome **o Edge** (Edge viene con Windows 10/11). Si hiciera falta uno, va a la carpeta de datos y cuenta para el peso. | `test_windows_prefiere_navegador_instalado` |
| PES-08 | El README y el instalador muestran pesos **medidos** por la CI, no estimados. | revisión |
| PES-09 | La compatibilidad hacia atrás con `PANDEX_MARKDOWN=si/no` se mantiene un ciclo (aviso de obsoleto). | `test_instaladores_leen_pandex_extras` |

## Escenarios

**PES-01 · Todo instalado**
- *Dado* una PC con Windows 11 sin Chrome
- *Cuando* se instala con `PANDEX_EXTRAS=markdown`
- *Entonces* `medir_peso.py` informa ≤ 600 MB, y Pandex usa Edge para Canvas.

**PES-04 · Quitar una función**
- *Dado* Pandex con «Convertir a Markdown»
- *Cuando* el usuario pulsa Configuración → Tareas → Convertir a Markdown → **Quitar**
- *Entonces* confirma («Libera unos N MB. Puedes volver a instalarla cuando quieras.»), se
  desinstalan solo sus paquetes, la tarea desaparece del menú y el peso vuelve al base.

**Error · Sin internet al instalar un extra**
- *Cuando* pulsa Instalar sin conexión
- *Entonces* el mensaje dice «No pude instalar «…». ¿Hay internet?» y no queda nada a medias
  (se revierten los paquetes que alcanzaron a instalarse).

## Fuera de alcance

- Cambiar de PyQt6 a otro framework de interfaz.
- Empaquetar Pandex como ejecutable (PyInstaller, etc.).
- Reducir la carpeta de cursos del usuario.

## Preguntas abiertas

| # | Pregunta | Por defecto | Decide |
|---|---|---|---|
| 1 | ¿600 MB es con todas las funciones opcionales (como se especifica) o solo la base? | Con todas. | Frank |
| 2 | ¿Se acepta podar las librerías de Qt que Pandex no usa (QML, Quick, 3D, Pdf, Designer, multimedia) después de instalar? Ahorra mucho, pero hay que volver a podar tras cada actualización de PyQt6. | Sí, con la lista en un archivo y prueba de humo de toda la interfaz. | Frank |
| 3 | ¿Se reemplaza Playwright por Selenium también en Windows (con Edge/Chrome)? Ahorra ~75 MB, unifica el código de los dos sistemas (P7) y evita descargar Chromium. | Evaluar en T002.5 con medición; decidir con datos. | Frank |
| 4 | ¿«Convertir a Markdown» puede dejar de usar MarkItDown (que obliga a instalar magika + onnxruntime + pandas) y llamar directo a sus conversores? | No por ahora; primero las opciones de menor riesgo. | Frank |

## Historial

| Fecha | Cambio | Por qué |
|---|---|---|
| 2026-10-19 | Primera versión con mediciones en Linux. | Requisito de Frank: máximo 600 MB. |
