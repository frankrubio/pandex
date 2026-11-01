#!/usr/bin/env bash
# Desinstala Pandex en Linux: muestra la lista exacta de lo que va a quitar y pregunta antes.
# Tu carpeta de cursos no se toca. Uso:  ./desinstalar.sh      (si no abre:  bash desinstalar.sh)
set -u
cd "$(dirname "$0")"

PY=.venv/bin/python
[ -x "$PY" ] || PY=python3

# todo menos .venv (es el Python que está corriendo); .venv se borra al final
"$PY" -m pandex.desinstalar --sin-venv "$@"
case $? in
    0) ;;
    2) exit 0 ;;   # dijiste que no: no se tocó nada
    *) echo; echo " Algo falló. Lee el mensaje de arriba."; exit 1 ;;
esac
rm -rf .venv && echo " Entorno de Python (.venv) borrado."
echo
echo " Para terminar, borra esta carpeta:  rm -rf \"$PWD\""
echo
