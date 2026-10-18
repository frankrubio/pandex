#!/usr/bin/env bash
# Instala Pandex en Linux: entorno virtual, dependencias, Firefox para Canvas y el acceso directo.
# Uso:  ./instalar.sh      (si no abre:  bash instalar.sh)
set -u
cd "$(dirname "$0")"

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

# 3. Dependencias
echo " Instalando dependencias: la primera vez tarda unos minutos..."
.venv/bin/python -m pip install --upgrade pip --quiet
.venv/bin/python -m pip install -r requirements.txt --quiet || fallo

# 4. Firefox para iniciar sesión en Canvas (el de Playwright; no toca tu Firefox)
echo " Descargando Firefox para iniciar sesión en Canvas (unos 80 MB, solo esta vez)..."
.venv/bin/python -m playwright install firefox || fallo

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
if ! command -v tesseract >/dev/null 2>&1; then
    echo
    echo " Opcional: para leer PDFs escaneados (OCR): sudo apt install tesseract-ocr tesseract-ocr-spa"
fi
echo
echo " Si Firefox no abre al conectar Canvas, falta alguna librería del sistema:"
echo "   sudo .venv/bin/python -m playwright install-deps firefox"
echo
echo " Listo. Abre Pandex desde el menú de aplicaciones o con:  .venv/bin/python main.py"
echo " La primera vez te va a guiar para conectar tu Canvas."
echo
