"""Abre Pandex con doble clic (sin ventana de consola).

Puedes crear un acceso directo a este archivo en tu Escritorio: clic derecho →
«Enviar a» → «Escritorio (crear acceso directo)». O, más fácil: en Pandex,
Configuración → Comportamiento → «Crear acceso directo en el Escritorio» (lleva el
ícono de Rusty).

Usa el Python del entorno de Pandex (``.venv``). Si Pandex ya está abierto, la
mascota solo se asoma.
"""

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent


def _avisar(texto):
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, texto, "Pandex", 0x40)
    except Exception:
        print(texto)


def main():
    for candidato in (RAIZ / ".venv" / "Scripts" / "pythonw.exe", RAIZ / ".venv" / "bin" / "python"):
        if candidato.exists():
            subprocess.Popen([str(candidato), str(RAIZ / "main.py")], cwd=str(RAIZ),
                             creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
            return 0
    _avisar("Falta instalar Pandex: haz doble clic en instalar.bat (solo la primera vez).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
