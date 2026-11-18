#!/usr/bin/env bash
# Baja un Python solo para Pandex en .python/ (dentro de esta carpeta) cuando el sistema no tiene
# Python 3.12 o más nuevo (spec 006, PLA-03). Sin sudo, sin tocar el Python del sistema, sin
# PATH y sin cachés fuera. La versión y su huella (SHA-256) están fijas en python_portatil.txt:
# si lo descargado no coincide, no se usa.
# Lo llama instalar.sh desde la carpeta de Pandex. Con PANDEX_PYTHON=portatil no pregunta.
set -u
FIJO="$(dirname "$0")/python_portatil.txt"
ARCHIVO=".python-descarga.tar.gz"
NUEVO=".python-nuevo"

MAQUINA="$(uname -m 2>/dev/null)"
case "$MAQUINA" in
    x86_64|amd64) SISTEMA=linux-x86_64 ;;
    aarch64|arm64) SISTEMA=linux-aarch64 ;;
    *)
        echo " No hay un Python portátil para este equipo ($MAQUINA)."
        echo " Instala Python 3.12 o más nuevo con el gestor de paquetes de tu Linux."
        exit 1 ;;
esac
read -r _ HUELLA URL < <(grep "^$SISTEMA " "$FIJO")
if [ -z "${URL:-}" ]; then
    echo " No encontré qué Python descargar (herramientas/python_portatil.txt)."
    exit 1
fi

if [ "${PANDEX_PYTHON:-}" != portatil ]; then
    echo
    read -r -p " ¿Descargo un Python solo para Pandex? Ocupa unos 105 MB dentro de esta carpeta (.python) y no toca tu sistema. [S/n] " SI
    case "$SI" in
        n|N|no|No|NO)
            echo " Instala Python 3.12 o más nuevo con tu gestor de paquetes y vuelve a ejecutar ./instalar.sh."
            exit 1 ;;
    esac
fi

rm -rf "$ARCHIVO" "$NUEVO"
trap 'rm -rf "$ARCHIVO" "$NUEVO"' EXIT  # pase lo que pase, nada a medias
echo " Descargando Python..."
if command -v curl >/dev/null 2>&1; then
    curl -fL --retry 2 --proto '=https' --proto-redir '=https' -o "$ARCHIVO" "$URL"
elif command -v wget >/dev/null 2>&1; then
    wget -q --https-only -O "$ARCHIVO" "$URL"
else
    echo " Necesito curl o wget para descargar Python. Debian/Ubuntu: sudo apt install curl"
    exit 1
fi || { echo " No pude descargar Python. Revisa tu conexión y vuelve a intentar."; exit 1; }

if command -v sha256sum >/dev/null 2>&1; then
    REAL="$(sha256sum "$ARCHIVO" | cut -d' ' -f1)"
else
    REAL="$(shasum -a 256 "$ARCHIVO" | cut -d' ' -f1)"
fi
if [ "$REAL" != "$HUELLA" ]; then
    echo " Lo descargado no coincide con su huella (SHA-256): no lo uso. Vuelve a intentar."
    exit 1
fi

mkdir "$NUEVO" && tar -xzf "$ARCHIVO" -C "$NUEVO" && [ -x "$NUEVO/python/bin/python3" ] || {
    echo " No pude descomprimir Python. Vuelve a intentar."
    exit 1
}
rm -rf .python && mv "$NUEVO/python" .python || exit 1
echo " Python listo en .python (solo para Pandex)."
