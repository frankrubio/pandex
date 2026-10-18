# Pandex en Linux

Funciona igual que en Windows, con tres diferencias: inicias sesión en Canvas con
**Firefox** (no hace falta Chrome ni Chromium), el acceso directo es un archivo `.desktop` y
el OCR de PDFs escaneados usa **Tesseract**.

## Instalar

En Debian, Ubuntu, Linux Mint o parecidos:

```bash
sudo apt install python3 python3-venv git libxcb-cursor0
git clone https://github.com/frankrubio/pandex.git
cd pandex
./instalar.sh
```

¿Sin git? Descarga el ZIP desde GitHub (**Code → Download ZIP**), extráelo, abre una terminal
en esa carpeta y ejecuta `bash instalar.sh`.

`instalar.sh` crea un entorno propio (`.venv`), instala las dependencias, descarga Firefox para
Canvas (unos 80 MB, es una copia aparte: no toca tu Firefox) y crea el acceso directo en el menú
de aplicaciones y en el Escritorio. Necesita **Python 3.12 o más nuevo**.

En Fedora usa `sudo dnf install python3 git xcb-util-cursor`; en Arch,
`sudo pacman -S python git xcb-util-cursor`.

## Abrirlo

Busca **Pandex** en el menú de aplicaciones, o ejecuta `.venv/bin/python main.py`.
La primera vez te guía para conectar tu Canvas.

## Lo que cambia

| | Windows | Linux |
|---|---|---|
| Navegador para iniciar sesión | Chrome | **Firefox** (el de Playwright) |
| Tus datos (sesión, historial) | `%LOCALAPPDATA%\Pandex` | `~/.local/share/Pandex` |
| Acceso directo | `.lnk` | `.desktop` |
| Arrancar con el sistema | Carpeta *Inicio* | `~/.config/autostart` |
| OCR de PDFs escaneados | El de Windows | Tesseract (opcional) |

Para forzar un navegador en cualquier sistema, en `config.json`, dentro de la tarea de Canvas,
`"navegador": "firefox"` o `"navegador": "chrome"`. Con `"auto"` (lo normal) Linux usa Firefox.

## OCR (opcional)

Solo hace falta para PDFs escaneados o imágenes. Sin él, Pandex convierte todo lo demás y avisa
cuáles quedaron sin texto.

```bash
sudo apt install tesseract-ocr tesseract-ocr-spa
```

## Si algo falla

| Qué pasa | Qué hacer |
|---|---|
| No abre y dice algo de `xcb` o `libxcb-cursor` | `sudo apt install libxcb-cursor0` |
| *"Falta Firefox para iniciar sesión"* | `.venv/bin/python -m playwright install firefox` |
| *"A Firefox le faltan librerías del sistema"* | `sudo .venv/bin/python -m playwright install-deps firefox` |
| No veo el ícono junto al reloj (GNOME) | GNOME no muestra íconos de bandeja por defecto. Instala la extensión *AppIndicator and KStatusNotifierItem Support*. Mientras tanto, clic derecho sobre la mascota abre el mismo menú. |
| El acceso del Escritorio dice "no confiable" | Clic derecho sobre el ícono → **Permitir lanzar**. |
| Quiero probar en Wayland puro | `QT_QPA_PLATFORM=wayland .venv/bin/python main.py`. Ahí el sistema no deja que la mascota se mueva ni quede siempre encima; por eso Pandex usa XWayland por defecto. |

## Para programadores

```bash
.venv/bin/python -m pip install ruff
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -t .
QT_QPA_PLATFORM=offscreen .venv/bin/python main.py --test
```

Las dependencias `winrt-*` solo se instalan en Windows. La CI corre en Windows y en Ubuntu.
