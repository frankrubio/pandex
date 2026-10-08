"""Accesos directos de Windows: en el Escritorio y en el arranque del sistema.

Uso desde la terminal (lo llama ``instalar.bat``)::

    .venv\\Scripts\\python.exe -m pandex.accesos
"""

import os
import subprocess
import sys
from pathlib import Path

from .log import get_logger
from .rutas import ICONO, RAIZ

log = get_logger("pandex.accesos")

NOMBRE = "Pandex"
LEGADO = "MascotaUTEC.lnk"  # nombre que usaban las primeras versiones


def carpeta_inicio():
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def ruta_inicio():
    return carpeta_inicio() / f"{NOMBRE}.lnk"


def _pythonw():
    exe = Path(sys.executable)
    sin_consola = exe.with_name("pythonw.exe")
    return sin_consola if sin_consola.exists() else exe


def _ps(texto):
    """Literal de PowerShell entre comillas simples (las internas se duplican)."""
    return "'" + str(texto).replace("'", "''") + "'"


def _crear(carpeta_ps, nombre_lnk):
    """Crea el acceso con PowerShell y devuelve la ruta real donde quedó.

    ``carpeta_ps`` es una expresión de PowerShell: así el Escritorio se resuelve con
    ``[Environment]::GetFolderPath``, que sabe si OneDrive lo redirigió.
    """
    script = (
        f"$d = {carpeta_ps};"
        f"$lnk = Join-Path $d {_ps(nombre_lnk)};"
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk);"
        f"$s.TargetPath = {_ps(_pythonw())};"
        f"$s.Arguments = {_ps(chr(34) + str(RAIZ / 'main.py') + chr(34))};"
        f"$s.WorkingDirectory = {_ps(RAIZ)};"
        "$s.Description = 'Pandex, tu panda robot de escritorio';"
        + (f"$s.IconLocation = {_ps(str(ICONO) + ',0')};" if ICONO.exists() else "")
        + "$s.Save(); Write-Output $lnk"
    )
    salida = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    ruta = Path(salida.stdout.strip().splitlines()[-1])
    log.info("acceso directo creado en %s", ruta)
    return ruta


def crear_en_escritorio():
    """``Pandex.lnk`` en tu Escritorio (el real, aunque OneDrive lo haya movido)."""
    return _crear("[Environment]::GetFolderPath('Desktop')", f"{NOMBRE}.lnk")


def arranca_con_windows():
    return ruta_inicio().exists() or (carpeta_inicio() / LEGADO).exists()


def activar_arranque():
    carpeta_inicio().mkdir(parents=True, exist_ok=True)
    (carpeta_inicio() / LEGADO).unlink(missing_ok=True)
    _crear(_ps(carpeta_inicio()), f"{NOMBRE}.lnk")
    return ruta_inicio().exists()


def desactivar_arranque():
    for acceso in (ruta_inicio(), carpeta_inicio() / LEGADO):
        if acceso.exists():
            acceso.unlink()
            log.info("acceso directo de inicio eliminado: %s", acceso.name)
    return not arranca_con_windows()


if __name__ == "__main__":
    print(f"Acceso directo creado: {crear_en_escritorio()}")
