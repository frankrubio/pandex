"""«Solo a la hora de sus tareas»: el sistema abre Pandex a su hora y Pandex se cierra al terminar.

Así Pandex no ocupa memoria el resto del día. Si a esa hora la PC estaba apagada o
suspendida, el sistema lo abre apenas vuelvas (y ``pendientes.py`` decide qué falta):

- Linux: un temporizador de systemd del usuario (``~/.config/systemd/user/pandex.timer``)
  con ``Persistent=true`` y un disparo al iniciar sesión.
- Windows: una tarea del Programador de tareas con «Ejecutar lo antes posible si se
  perdió un inicio programado» y un disparo al iniciar sesión.

Lo que se lanza es ``main.py --pendientes``: si no hay nada pendiente, termina en
milisegundos sin abrir la ventana.
"""

import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from .log import get_logger
from .rutas import RAIZ, WINDOWS

log = get_logger("pandex.despertador")

NOMBRE = "pandex"
CADA_15 = "*:0/15"  # para horarios que systemd no sabe expresar: se revisa cada 15 min
DIAS = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
DIAS_WIN = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class ErrorDespertador(Exception):
    pass


def modo_a_la_hora(config_datos):
    return (config_datos or {}).get("modo") == "a_la_hora"


# ---------- cron → systemd ----------

def _campo(texto, nombres=None):
    """Un campo de cron en sintaxis de systemd, o None si no se puede."""
    partes = []
    for parte in texto.split(","):
        if parte == "*":
            partes.append("*")
            continue
        m = re.fullmatch(r"\*/(\d+)", parte)
        if m:
            if nombres:
                return None
            partes.append(f"0/{m[1]}")
            continue
        m = re.fullmatch(r"(\d+)-(\d+)", parte)
        if m:
            a, b = int(m[1]), int(m[2])
            partes.append(f"{nombres[a]}..{nombres[b]}" if nombres else f"{a}..{b}")
            continue
        if parte.isdigit():
            partes.append(nombres[int(parte)] if nombres else parte)
            continue
        return None
    return ",".join(partes)


def a_oncalendar(cron):
    """``"0 19 * * 1-5"`` → ``"Mon..Fri *-*-* 19:00:00"``; None si systemd no lo expresa igual."""
    try:
        minuto, hora, dia, mes, semana = cron.split()
    except (AttributeError, ValueError):
        return None
    if dia != "*" and semana != "*":
        return None  # cron usa «o», systemd «y»: no es lo mismo
    try:
        campos = [_campo(minuto), _campo(hora), _campo(dia), _campo(mes),
                  None if semana == "*" else _campo(semana, DIAS)]
    except (IndexError, ValueError):
        return None
    minuto, hora, dia, mes, semana = campos
    if None in (minuto, hora, dia, mes) or (semana is None and cron.split()[4] != "*"):
        return None
    def dos(valor):
        return valor.zfill(2) if valor.isdigit() else valor

    return f"{semana + ' ' if semana else ''}*-{dos(mes)}-{dos(dia)} {dos(hora)}:{dos(minuto)}:00"


def unidades(horarios):
    """El texto de ``pandex.service`` y ``pandex.timer`` para esos ``{task_id: cron}``."""
    calendarios = sorted({a_oncalendar(c) or CADA_15 for c in horarios.values()})
    servicio = "\n".join([
        "[Unit]",
        "Description=Pandex: tareas a su hora",
        "",
        "[Service]",
        "Type=oneshot",
        f"WorkingDirectory={RAIZ}",
        f"ExecStart={shlex.quote(sys.executable)} {shlex.quote(str(RAIZ / 'main.py'))} --pendientes",
        "TimeoutStartSec=infinity",
        "",
    ])
    temporizador = "\n".join([
        "[Unit]",
        "Description=Pandex: tareas a su hora (y al volver, si la PC estaba apagada)",
        "",
        "[Timer]",
        *(f"OnCalendar={c}" for c in calendarios),
        "OnStartupSec=2min",
        "Persistent=true",
        "AccuracySec=1min",
        "",
        "[Install]",
        "WantedBy=timers.target",
        "",
    ])
    return servicio, temporizador


def _carpeta_systemd():
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "systemd" / "user"


def _systemctl(*args):
    r = subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise ErrorDespertador(r.stderr.strip() or f"systemctl {' '.join(args)} falló")
    return r


def _instalar_linux(horarios):
    if not shutil.which("systemctl"):
        raise ErrorDespertador("Este Linux no tiene systemd: deja Pandex en «Siempre en el escritorio».")
    carpeta = _carpeta_systemd()
    carpeta.mkdir(parents=True, exist_ok=True)
    servicio, temporizador = unidades(horarios)
    (carpeta / f"{NOMBRE}.service").write_text(servicio, encoding="utf-8")
    (carpeta / f"{NOMBRE}.timer").write_text(temporizador, encoding="utf-8")
    # que lo que abra el temporizador sepa dónde está tu pantalla (las sesiones de escritorio
    # lo hacen solas al iniciar; esto cubre la sesión actual)
    variables = [v for v in ("DISPLAY", "XAUTHORITY", "WAYLAND_DISPLAY") if os.environ.get(v)]
    if variables:
        try:
            _systemctl("import-environment", *variables)
        except ErrorDespertador:
            pass
    _systemctl("daemon-reload")
    _systemctl("enable", "--now", f"{NOMBRE}.timer")
    log.info("temporizador de systemd instalado: %s", ", ".join(sorted(horarios)))


def _quitar_linux():
    carpeta = _carpeta_systemd()
    if not (carpeta / f"{NOMBRE}.timer").exists():
        return
    try:
        _systemctl("disable", "--now", f"{NOMBRE}.timer")
    except (ErrorDespertador, OSError, subprocess.SubprocessError):
        pass
    for extension in ("timer", "service"):
        (carpeta / f"{NOMBRE}.{extension}").unlink(missing_ok=True)
    try:
        _systemctl("daemon-reload")
    except (ErrorDespertador, OSError, subprocess.SubprocessError):
        pass
    log.info("temporizador de systemd quitado")


# ---------- Windows ----------

def _ps(texto):
    return "'" + str(texto).replace("'", "''") + "'"


def disparadores_windows(horarios):
    """Los disparadores de PowerShell. Lo que no sea «a una hora, ciertos días» se cubre
    con el disparo al iniciar sesión."""
    salida = ["New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME"]
    for cron in sorted(set(horarios.values())):
        m = re.fullmatch(r"(\d{1,2}) (\d{1,2}) \* \* (\*|[\d,\-]+)", cron.strip())
        if not m:
            log.info("horario '%s': en Windows se revisa al iniciar sesión", cron)
            continue
        hora = f"{int(m[2]):02d}:{int(m[1]):02d}"
        if m[3] == "*":
            salida.append(f"New-ScheduledTaskTrigger -Daily -At '{hora}'")
            continue
        dias = set()
        for parte in m[3].split(","):
            a, _, b = parte.partition("-")
            dias.update(range(int(a), int(b or a) + 1))
        nombres = ",".join(sorted({DIAS_WIN[d] for d in dias if 0 <= d <= 7}))
        salida.append(f"New-ScheduledTaskTrigger -Weekly -DaysOfWeek {nombres} -At '{hora}'")
    return salida


def script_windows(horarios):
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    exe = pythonw if pythonw.exists() else Path(sys.executable)
    return ";".join([
        f"$a = New-ScheduledTaskAction -Execute {_ps(exe)} "
        f"-Argument {_ps(chr(34) + str(RAIZ / 'main.py') + chr(34) + ' --pendientes')} "
        f"-WorkingDirectory {_ps(RAIZ)}",
        "$t = @(" + ", ".join(f"({d})" for d in disparadores_windows(horarios)) + ")",
        "$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries "
        "-DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Seconds 0)",
        "Register-ScheduledTask -TaskName 'Pandex' -Action $a -Trigger $t -Settings $s -Force | Out-Null",
    ])


def _powershell(script):
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode != 0:
        raise ErrorDespertador(r.stderr.strip()[:300] or "el Programador de tareas no respondió")


# ---------- lo que usa la app ----------

def actualizar(config_datos, por_defecto=None):
    """Instala o quita el despertador según el modo elegido y los horarios actuales."""
    from .pendientes import horarios as leer_horarios

    horarios = leer_horarios(config_datos, por_defecto)
    if not modo_a_la_hora(config_datos) or not horarios:
        quitar()
        return False
    if WINDOWS:
        _powershell(script_windows(horarios))
        log.info("tarea de Windows «Pandex» registrada")
    else:
        _instalar_linux(horarios)
    return True


def quitar():
    if WINDOWS:
        try:
            _powershell("Unregister-ScheduledTask -TaskName 'Pandex' -Confirm:$false -ErrorAction SilentlyContinue")
        except (ErrorDespertador, OSError, subprocess.SubprocessError):
            pass
    else:
        _quitar_linux()
