"""Accesos directos: en el Escritorio y en el arranque del sistema.

- Windows: archivos ``.lnk`` (se crean con PowerShell).
- Linux: archivos ``.desktop`` (menú de aplicaciones, Escritorio y ``~/.config/autostart``).

Uso desde la terminal (lo llaman ``instalar.bat`` y ``instalar.sh``)::

    .venv\\Scripts\\python.exe -m pandex.accesos      (Windows)
    .venv/bin/python -m pandex.accesos               (Linux)
"""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from .log import get_logger
from .rutas import ASSETS_DIR, CONFIG_FILE, DATOS, ICONO, RAIZ, WINDOWS

log = get_logger("pandex.accesos")

NOMBRE = "Pandex"
LEGADO = "MascotaUTEC.lnk"  # nombre que usaban las primeras versiones
DESKTOP = "pandex.desktop"


def carpeta_inicio():
    if not WINDOWS:
        return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "autostart"
    appdata = os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def ruta_inicio():
    return carpeta_inicio() / (f"{NOMBRE}.lnk" if WINDOWS else DESKTOP)


def _pythonw():
    exe = Path(sys.executable)
    sin_consola = exe.with_name("pythonw.exe")
    return sin_consola if sin_consola.exists() else exe


def icono_elegido():
    """El ``.ico`` del logo que elegiste (Configuración → Apariencia), sin abrir Qt.

    Se lee ``config.json`` directo: ``instalar.bat`` e ``instalar.sh`` también lo usan.
    """
    try:
        mascota = json.loads(CONFIG_FILE.read_text(encoding="utf-8")).get("mascota", {})
    except (OSError, ValueError, AttributeError):
        mascota = {}
    for ident in (mascota.get("logo"), mascota.get("personaje")):
        if isinstance(ident, str) and ident and ident == Path(ident).name:
            ico = ASSETS_DIR / "personajes" / ident / "icono.ico"
            if ico.exists():
                return ico
    return ICONO


# ---------- Windows (.lnk) ----------

def _ps(texto):
    """Literal de PowerShell entre comillas simples (las internas se duplican)."""
    return "'" + str(texto).replace("'", "''") + "'"


def _crear(carpeta_ps, nombre_lnk, icono=None):
    """Crea el acceso con PowerShell y devuelve la ruta real donde quedó.

    ``carpeta_ps`` es una expresión de PowerShell: así el Escritorio se resuelve con
    ``[Environment]::GetFolderPath``, que sabe si OneDrive lo redirigió.
    """
    icono = Path(icono) if icono else icono_elegido()
    script = (
        f"$d = {carpeta_ps};"
        f"$lnk = Join-Path $d {_ps(nombre_lnk)};"
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk);"
        f"$s.TargetPath = {_ps(_pythonw())};"
        f"$s.Arguments = {_ps(chr(34) + str(RAIZ / 'main.py') + chr(34))};"
        f"$s.WorkingDirectory = {_ps(RAIZ)};"
        "$s.Description = 'Pandex, tu mascota de escritorio';"
        + (f"$s.IconLocation = {_ps(str(icono) + ',0')};" if icono.exists() else "")
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


# ---------- Linux (.desktop) ----------

def _carpeta_menu():
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "applications"


def _carpeta_escritorio():
    """El Escritorio real (``xdg-user-dir``), o ``~/Escritorio`` / ``~/Desktop``; None si no hay."""
    try:
        salida = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True,
                                timeout=5).stdout.strip()
        if salida and Path(salida).is_dir() and Path(salida) != Path.home():
            return Path(salida)
    except (OSError, subprocess.SubprocessError):
        pass
    return next((d for d in (Path.home() / "Escritorio", Path.home() / "Desktop") if d.is_dir()), None)


def _icono_png(icono):
    """Los lanzadores de Linux prefieren PNG: convierte el ``.ico`` (su tamaño más grande)."""
    icono = Path(icono)
    if icono.suffix.lower() != ".ico" or not icono.exists():
        return icono
    destino = DATOS / "iconos" / f"{icono.parent.name}.png"
    try:
        if not destino.exists() or destino.stat().st_mtime < icono.stat().st_mtime:
            from PIL import Image

            destino.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(icono) as img:
                if hasattr(img, "ico"):
                    img.size = max(img.ico.sizes())
                img.load()
                img.convert("RGBA").save(destino, "PNG")
        return destino
    except Exception as exc:  # sin ícono es mejor que sin acceso
        log.warning("no pude convertir el ícono %s: %s", icono, exc)
        return icono


def _entrada_desktop(icono):
    lineas = [
        "[Desktop Entry]",
        "Type=Application",
        f"Name={NOMBRE}",
        "Comment=Pandex, tu mascota de escritorio",
        f"Exec={shlex.quote(sys.executable)} {shlex.quote(str(RAIZ / 'main.py'))}",
        f"Path={RAIZ}",
        "Terminal=false",
        "Categories=Utility;",
        f"StartupWMClass={NOMBRE}",
    ]
    if icono and Path(icono).exists():
        lineas.append(f"Icon={_icono_png(icono)}")
    return "\n".join(lineas) + "\n"


def _escribir_desktop(carpeta, icono, ejecutable=True):
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / DESKTOP
    ruta.write_text(_entrada_desktop(icono), encoding="utf-8")
    if ejecutable:
        ruta.chmod(0o755)
        try:  # GNOME pide «Permitir lanzar» salvo que el archivo esté marcado como de confianza
            subprocess.run(["gio", "set", str(ruta), "metadata::trusted", "true"],
                           capture_output=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            pass
    return ruta


def _crear_linux(icono=None):
    """Lo deja en el menú de aplicaciones y, si hay Escritorio, también ahí."""
    icono = Path(icono) if icono else icono_elegido()
    ruta = _escribir_desktop(_carpeta_menu(), icono, ejecutable=False)
    escritorio = _carpeta_escritorio()
    if escritorio is not None:
        ruta = _escribir_desktop(escritorio, icono)
    log.info("acceso directo creado en %s", ruta)
    return ruta


def _cambiar_icono_linux(icono):
    """Reescribe la línea ``Icon=`` de los accesos que ya existen."""
    destino = _icono_png(icono)
    escritorio = _carpeta_escritorio()
    for ruta in (_carpeta_menu() / DESKTOP, ruta_inicio(), *([escritorio / DESKTOP] if escritorio else [])):
        if not ruta.exists():
            continue
        lineas = [ln for ln in ruta.read_text(encoding="utf-8").splitlines() if not ln.startswith("Icon=")]
        ruta.write_text("\n".join([*lineas, f"Icon={destino}"]) + "\n", encoding="utf-8")
    log.info("ícono de los accesos directos: %s", icono)


# ---------- lo que usa la app ----------

def crear_en_escritorio(icono=None):
    """El acceso «Pandex» en tu Escritorio (el real, aunque OneDrive lo haya movido).

    En Linux también queda en el menú de aplicaciones.
    """
    if not WINDOWS:
        return _crear_linux(icono)
    return _crear("[Environment]::GetFolderPath('Desktop')", f"{NOMBRE}.lnk", icono)


def cambiar_icono(icono):
    """Cambia el ícono de los accesos directos que ya existen (Escritorio y arranque).

    En Windows no espera a PowerShell (tarda casi un segundo): la ventana no se congela.
    Si no hay accesos, no hace nada.
    """
    if not WINDOWS:
        _cambiar_icono_linux(icono)
        return None
    script = (
        f"$ico = {_ps(str(icono) + ',0')};"
        f"$rutas = @((Join-Path ([Environment]::GetFolderPath('Desktop')) {_ps(NOMBRE + '.lnk')}), "
        f"{_ps(ruta_inicio())});"
        "$shell = New-Object -ComObject WScript.Shell;"
        "foreach ($r in $rutas) { if (Test-Path -LiteralPath $r) {"
        " $s = $shell.CreateShortcut($r); $s.IconLocation = $ico; $s.Save() } }"
    )
    log.info("ícono de los accesos directos: %s", icono)
    return subprocess.Popen(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def arranca_con_el_sistema():
    if not WINDOWS:
        return ruta_inicio().exists()
    return ruta_inicio().exists() or (carpeta_inicio() / LEGADO).exists()


arranca_con_windows = arranca_con_el_sistema  # nombre de las versiones anteriores


def activar_arranque():
    carpeta_inicio().mkdir(parents=True, exist_ok=True)
    if not WINDOWS:
        _escribir_desktop(carpeta_inicio(), icono_elegido())
        return ruta_inicio().exists()
    (carpeta_inicio() / LEGADO).unlink(missing_ok=True)
    _crear(_ps(carpeta_inicio()), f"{NOMBRE}.lnk")
    return ruta_inicio().exists()


def desactivar_arranque():
    for acceso in (ruta_inicio(), carpeta_inicio() / LEGADO):
        if acceso.exists():
            acceso.unlink()
            log.info("acceso directo de inicio eliminado: %s", acceso.name)
    return not arranca_con_el_sistema()


if __name__ == "__main__":
    print(f"Acceso directo creado: {crear_en_escritorio()}")
