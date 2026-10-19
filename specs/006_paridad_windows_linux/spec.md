# 006 · Igual en Windows y en Linux

> Estado: aprobada (con preguntas abiertas)  ·  Prefijo: `PLA`  ·  Principios: P7, P2, P3

## Por qué

Pandex es para cualquier estudiante, use Windows o Linux, y no debe chocar con la versión de
su sistema. Hoy hay instalador para cada uno (`instalar.bat`, `instalar.sh`) y la CI corre en
`windows-latest` y `ubuntu-latest` con Python 3.12 y 3.13. Faltan algunas piezas.

## Qué existe hoy

- Instaladores para Windows y Linux; guía de Linux en `docs/linux.md`.
- Código dependiente del sistema detrás de `rutas.WINDOWS`; pruebas de Linux en
  `tests/test_linux.py`.
- Dependencias con versión fija y marcadores de plataforma (`playwright`, `winrt-*` solo en
  Windows; `selenium` solo fuera de Windows).
- XWayland por defecto en Linux para que la mascota se pueda mover y quede encima.

**Huecos encontrados:**

| # | Hueco |
|---|---|
| H1 | Pandex exige Python ≥ 3.12, pero **Ubuntu 22.04 y Linux Mint 21 traen 3.10, y Debian 12 trae 3.11**: ahí `instalar.sh` se detiene. |
| H2 | `requirements.txt` dice «probado con Python 3.12 a 3.14», pero la CI no prueba 3.14. |
| H3 | La CI instala con `pip` directo: **nunca ejecuta** `instalar.sh` ni `instalar.bat`. Un error en un instalador no se detecta. |
| H4 | No hay desinstalador en ningún sistema (ver 003). |
| H5 | La plantilla de issue «Algo falla» solo ofrece Windows 10/11. |
| H6 | No hay prueba de que, con el mismo Canvas, Windows y Linux dejan **el mismo árbol de carpetas**. |
| H7 | Windows en ARM no está documentado (PyQt6 puede no tener paquete para esa arquitectura). |

## Sistemas soportados

| Sistema | Versiones | Python |
|---|---|---|
| Windows | 10 (22H2) y 11, x64 | 3.12 – 3.14 de python.org |
| Ubuntu / Linux Mint / Debian | Ubuntu 22.04+, Mint 21+, Debian 12+ | el del sistema si es ≥ 3.12; si no, el portátil (PLA-03) |
| Fedora / Arch | Fedora 40+, Arch actual | el del sistema |

## Requisitos

| Id | Requisito | Se comprueba con |
|---|---|---|
| PLA-01 | La CI prueba Windows y Ubuntu (22.04 y 24.04) con Python 3.12, 3.13 y 3.14. | `.github/workflows/pruebas.yml` |
| PLA-02 | La CI ejecuta **los instaladores reales** sin preguntas (`PANDEX_EXTRAS=ninguno` y `=markdown`) y luego `main.py --test`. | job `instaladores` |
| PLA-03 | Si el Python del sistema es menor que 3.12, `instalar.sh` ofrece descargar un Python portátil **dentro de la carpeta de Pandex** (sin `sudo`, sin tocar el Python del sistema, sin cachés fuera). | job `instaladores` en `ubuntu-22.04` |
| PLA-04 | Con el mismo Canvas falso, Windows y Linux crean exactamente el mismo árbol de carpetas y nombres de archivo. | `tests/test_paridad.py::test_mismo_arbol` (compara con `tests/datos/arbol_esperado.txt`) |
| PLA-05 | Rutas con espacios, tildes, ñ y guiones (`OneDrive - Universidad`, `Diseño`, `Año 1`) funcionan en sincronizar, convertir, comprimir y accesos directos. | `test_rutas_raras` |
| PLA-06 | Cada dependencia tiene versión fija (`==`) y ninguna se instala en un sistema que no la usa. | `tests/test_principios.py::Dependencias` ✅ |
| PLA-07 | Hay desinstalador en los dos sistemas (ver 003, RES-07). | 003 |
| PLA-08 | La plantilla de issue pregunta el sistema (Windows 10, Windows 11, Linux + distribución). | revisión |
| PLA-09 | Lo que no se soporta (Windows ARM, macOS, Python < 3.12 sin portátil) lo dice el instalador con un mensaje claro y el README lo lista. | revisión |
| PLA-10 | Todo texto que ve el usuario es el mismo en los dos sistemas, salvo los nombres propios del sistema (Explorador / Archivos, Chrome / Firefox). | revisión |

✅ = la prueba ya existe y pasa.

## Escenarios

**PLA-03 · Linux Mint 21**
- *Dado* Linux Mint 21 con Python 3.10
- *Cuando* ejecuta `./instalar.sh`
- *Entonces* le dice «Tu Linux trae Python 3.10 y Pandex necesita 3.12. ¿Descargo un Python
  solo para Pandex (unos 40 MB, dentro de esta carpeta)? [S/n]», y al aceptar termina igual
  que en un sistema nuevo.

**PLA-04 · Mismo resultado**
- *Dado* el Canvas falso de `tests/apoyo.py` con cursos de teoría y laboratorio
- *Cuando* se sincroniza en Windows y en Linux
- *Entonces* la lista de rutas relativas creadas es idéntica.

## Fuera de alcance

- macOS.
- Paquetes de distribución (`.deb`, Flatpak, instalador `.msi`).

## Preguntas abiertas

| # | Pregunta | Por defecto | Decide |
|---|---|---|---|
| 1 | Para PLA-03, ¿usar `uv` (descarga Python y se puede dejar todo dentro de la carpeta de Pandex) o pedir al usuario instalar Python 3.12 con su gestor? | `uv`, con `UV_CACHE_DIR` y `UV_PYTHON_INSTALL_DIR` dentro de la carpeta de Pandex (P3). | Frank |
| 2 | ¿Bajar el mínimo a Python 3.10 en vez de PLA-03? Hay que revisar qué del código necesita 3.12. | No: más trabajo y más casos que probar. | Frank |

## Historial

| Fecha | Cambio | Por qué |
|---|---|---|
| 2026-10-19 | Primera versión con los huecos H1–H7. | Requisito de Frank: sin conflictos con su versión de Windows ni de Linux. |
