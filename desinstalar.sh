#!/usr/bin/env bash
# Desinstala Pandex en Linux: muestra la lista exacta de lo que va a quitar y pregunta antes.
# Tu carpeta de cursos no se toca. Uso:  ./desinstalar.sh      (si no abre:  bash desinstalar.sh)
set -u
cd "$(dirname "$0")"

PY=.venv/bin/python
[ -x "$PY" ] || PY=python3

# todo menos .venv y .python (son el Python que está corriendo): se borran al final
"$PY" -m pandex.desinstalar --sin-venv "$@"
case $? in
    0) ;;
    2) exit 0 ;;   # dijiste que no: no se tocó nada
    *) echo; echo " Algo falló. Lee el mensaje de arriba."; exit 1 ;;
esac
rm -rf .venv && echo " Entorno de Python (.venv) borrado."
if [ -d .python ]; then rm -rf .python && echo " Python que bajó el instalador (.python) borrado."; fi
echo
echo " Para terminar, borra esta carpeta:  rm -rf \"$PWD\""
echo
