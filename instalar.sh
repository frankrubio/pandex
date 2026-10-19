#!/usr/bin/env bash
# Instala Pandex en Linux: entorno virtual, dependencias y el acceso directo.
# Usa tu Firefox para Canvas (no descarga otro navegador).
# Uso:  ./instalar.sh      (si no abre:  bash instalar.sh)
set -u
cd "$(dirname "$0")"

case "$(uname -s 2>/dev/null)" in
    MINGW*|MSYS*|CYGWIN*)
        echo " Estás en Windows: usa instalar.bat (doble clic), no este archivo."
        exit 1 ;;
esac

fallo() { echo; echo " Algo falló. Lee el mensaje de arriba; si no se entiende, abre un issue en GitHub."; exit 1; }

echo
echo " ===  Instalando Pandex  ==="
echo

# 1. Python 3.12 o más nuevo
PY=""
for c in python3.14 python3.13 python3.12 python3; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
        PY="$c"; break
    fi
done
if [ -z "$PY" ]; then
    echo " No encontré Python 3.12 o más nuevo."
    echo " Debian/Ubuntu: sudo apt install python3 python3-venv   (Fedora: sudo dnf install python3)"
    fallo
fi

# 2. Entorno virtual propio, para no tocar el Python del sistema
if [ ! -x .venv/bin/python ]; then
    echo " Creando el entorno virtual..."
    "$PY" -m venv .venv || { echo " Falta el módulo venv. Debian/Ubuntu: sudo apt install python3-venv"; fallo; }
fi

# 3. Dependencias (lo básico: mascota, tareas y Canvas)
echo " Instalando dependencias: la primera vez tarda unos minutos..."
.venv/bin/python -m pip install --upgrade pip --quiet
.venv/bin/python -m pip install -r requirements.txt --quiet || fallo

# 4. «Convertir a Markdown» es opcional (unos 280 MB). Se puede añadir después en
#    Configuración → Tareas. Para no preguntar:  PANDEX_MARKDOWN=si ./instalar.sh  (o =no)
if .venv/bin/python -c "import markitdown" >/dev/null 2>&1; then
    QUIERE=si   # ya lo tenías: se actualiza
else
    QUIERE="${PANDEX_MARKDOWN:-}"
    if [ -z "$QUIERE" ]; then
        echo
        read -r -p " ¿Instalar también «Convertir a Markdown» (PDF, Word, PowerPoint a .md; unos 280 MB)? [s/N] " QUIERE
    fi
fi
case "$QUIERE" in
    s|S|si|sí|Si|Sí|SI|y|Y|yes)
        echo " Instalando «Convertir a Markdown»..."
        .venv/bin/python -m pip install -r requirements-markdown.txt --quiet || fallo ;;
    *) echo " Sin «Convertir a Markdown»: Pandex queda más liviano." ;;
esac

# Navegador para Canvas: tu Firefox (no se descarga ninguno)
if ! command -v firefox >/dev/null 2>&1 && ! command -v firefox-esr >/dev/null 2>&1; then
    echo
    echo " AVISO: no encontré Firefox. Pandex lo usa para que inicies sesión en Canvas."
    echo "   Instálalo con: sudo apt install firefox"
fi

# 5. Acceso directo (menú de aplicaciones y Escritorio)
.venv/bin/python -m pandex.accesos || fallo

# 6. Avisos sobre librerías del sistema que pip no puede instalar
if ! ldconfig -p 2>/dev/null | grep -q libxcb-cursor; then
    echo
    echo " AVISO: falta libxcb-cursor0, que necesita la ventana de Pandex."
    echo "   Debian/Ubuntu: sudo apt install libxcb-cursor0     Fedora/Arch: xcb-util-cursor"
fi
if ! command -v rclone >/dev/null 2>&1; then
    echo
    echo " Opcional: para usar tu OneDrive (Configuración → OneDrive): sudo apt install rclone fuse3"
fi
if .venv/bin/python -c "import markitdown" >/dev/null 2>&1 && ! command -v tesseract >/dev/null 2>&1; then
    echo
    echo " Opcional: para leer PDFs escaneados (OCR): sudo apt install tesseract-ocr tesseract-ocr-spa"
fi
if ! command -v gs >/dev/null 2>&1; then
    echo
    echo " Opcional: para aligerar PDFs al comprimir carpetas: sudo apt install ghostscript"
fi
echo
echo " Listo. Abre Pandex desde el menú de aplicaciones o con:  .venv/bin/python main.py"
echo " La primera vez te va a guiar para conectar tu Canvas."
echo
