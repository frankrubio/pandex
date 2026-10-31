"""Desinstalar Pandex: deja la PC como estaba, salvo la carpeta de tus cursos (RES-07/08/09).

Orden: despertador → arranque automático → accesos directos → OneDrive de Pandex → perfiles
de navegador de snap → carpeta de datos → ``.venv``. Antes muestra la lista exacta y pide
confirmación; puede conservar tu ``config.json`` para reinstalar. Lo que no se pudo borrar
se lista al final, con su ruta. La carpeta del proyecto se borra a mano (un programa no
puede borrarse a sí mismo mientras corre): se explica cómo.

Desde la terminal (lo usan ``desinstalar.sh`` y ``desinstalar.bat``)::

    python -m pandex.desinstalar            # muestra la lista y pregunta
    python -m pandex.desinstalar --si       # sin preguntar
    python -m pandex.desinstalar --borrar-config --sin-venv
"""

import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import inventario
from .log import get_logger
from .rutas import CONFIG_FILE, DATOS, RAIZ, WINDOWS

log = get_logger("pandex.desinstalar")


@dataclass
class Paso:
    nombre: str
    rutas: list = field(default_factory=list)
    accion: object = None  # función extra (p. ej. apagar el temporizador); recibe nada


def _accesos_conocidos():
    from . import accesos

    rutas = [accesos.ruta_inicio(), accesos.carpeta_inicio() / accesos.LEGADO]
    if WINDOWS:
        rutas += [Path.home() / d / f"{accesos.NOMBRE}.lnk" for d in ("Desktop", "Escritorio")]
        rutas += [Path.home() / "OneDrive" / d / f"{accesos.NOMBRE}.lnk" for d in ("Desktop", "Escritorio")]
    else:
        rutas.append(accesos._carpeta_menu() / accesos.DESKTOP)
        escritorio = accesos._carpeta_escritorio()
        if escritorio is not None:
            rutas.append(escritorio / accesos.DESKTOP)
    return rutas


def _perfiles_snap():
    if WINDOWS:
        return []
    return sorted((Path.home() / "snap").glob("*/common/pandex-perfil"))


def plan(raiz=RAIZ, conservar_config=True, con_venv=True):
    """La lista de pasos, con las rutas que existen de verdad (nada se borra todavía)."""
    from . import despertador, onedrive

    anotadas = [Path(d["ruta"]) for d in inventario.todo()]
    pasos = []

    if WINDOWS:  # la tarea programada no es un archivo: se quita siempre (si no existe, no pasa nada)
        pasos.append(Paso("Despertador (tarea programada «Pandex», si la activaste)", [], despertador.quitar))
    else:
        systemd = [despertador._carpeta_systemd() / f"{despertador.NOMBRE}.{e}" for e in ("timer", "service")]
        systemd = [r for r in systemd if r.exists()]
        if systemd:
            pasos.append(Paso("Despertador (abrir Pandex a la hora de sus tareas)", systemd, despertador.quitar))

    accesos_ = {r for r in _accesos_conocidos() + [a for a in anotadas if a.suffix in (".lnk", ".desktop")]}
    pasos.append(Paso("Accesos directos y arranque automático", sorted(r for r in accesos_ if r.exists())))

    if not WINDOWS and onedrive.disponible():
        cuentas = onedrive.cuentas()
        if cuentas:
            def desconectar():
                for cuenta in onedrive.cuentas():
                    onedrive.quitar(cuenta)  # tus archivos siguen en OneDrive
            pasos.append(Paso("Conexiones de OneDrive (tus archivos siguen en la nube)",
                              [Path(c.ruta) for c in cuentas], desconectar))

    perfiles = {*_perfiles_snap(), *(a for a in anotadas if a.name == "pandex-perfil")}
    pasos.append(Paso("Perfil del navegador de Pandex (fuera de la carpeta de datos)",
                      sorted(p for p in perfiles if p.exists())))

    pasos.append(Paso("Datos de Pandex: sesión del navegador, historial de Canvas, respaldos",
                      [DATOS] if DATOS.exists() else []))
    if not conservar_config:
        pasos.append(Paso("Tu configuración (config.json)", [p for p in [Path(raiz) / CONFIG_FILE.name] if p.exists()]))
    if con_venv:
        pasos.append(Paso("Entorno de Python de Pandex (.venv)", [p for p in [Path(raiz) / ".venv"] if p.exists()]))
    return [p for p in pasos if p.rutas or p.accion]


def _borrar(ruta):
    ruta = Path(ruta)
    if ruta.is_dir() and not ruta.is_symlink() and not os.path.ismount(ruta):
        shutil.rmtree(ruta)
    elif ruta.is_dir() and os.path.ismount(ruta):
        return  # un OneDrive montado: lo desmonta su paso, aquí nunca se borra
    else:
        ruta.unlink(missing_ok=True)


def ejecutar(pasos):
    """Hace los pasos en orden. Sigue aunque algo falle. Devuelve las rutas que quedaron."""
    quedan = []
    for paso in pasos:
        if paso.accion:
            try:
                paso.accion()
            except Exception as exc:
                log.warning("%s: %s", paso.nombre, exc)
        for ruta in paso.rutas:
            if paso.nombre.startswith("Conexiones de OneDrive"):
                try:
                    Path(ruta).rmdir()  # solo si quedó vacía al desmontar
                except OSError:
                    pass
                continue
            try:
                _borrar(ruta)
            except OSError as exc:
                log.warning("no pude borrar %s: %s", ruta, exc)
            if Path(ruta).exists() and not os.path.ismount(ruta):
                quedan.append(Path(ruta))
    log.info("Pandex desinstalado; quedan %d ruta(s)", len(quedan))
    return quedan


def como_borrar_la_carpeta(raiz=RAIZ):
    if WINDOWS:
        return f"Para terminar, borra la carpeta {raiz} (clic derecho → Eliminar)."
    return f"Para terminar, borra la carpeta {raiz}  (en la terminal: rm -rf \"{raiz}\")"


def cerrar_pandex_abierto():
    """Si Pandex está abierto, le pide que se cierre (para poder borrar sus archivos)."""
    try:
        import getpass

        from PyQt6.QtNetwork import QLocalSocket
    except ImportError:
        return False
    socket = QLocalSocket()
    socket.connectToServer(f"Pandex-{getpass.getuser()}")
    if not socket.waitForConnected(300):
        return False
    socket.write(b"salir")
    socket.flush()
    socket.waitForBytesWritten(300)
    socket.disconnectFromServer()
    return True


def _cli(argumentos):
    si = "--si" in argumentos
    con_venv = "--sin-venv" not in argumentos
    conservar = "--borrar-config" not in argumentos
    if not si and Path(RAIZ / CONFIG_FILE.name).exists() and "--borrar-config" not in argumentos:
        respuesta = input(" ¿Conservar tu configuración (config.json) para reinstalar después? [S/n] ")
        conservar = respuesta.strip().lower() not in ("n", "no")
    pasos = plan(RAIZ, conservar, con_venv)
    print()
    print(" Esto es lo que se va a quitar (tu carpeta de cursos no se toca):")
    for paso in pasos:
        print(f"  • {paso.nombre}")
        for ruta in paso.rutas:
            print(f"      {ruta}")
    if not con_venv:
        print(f"  • Entorno de Python: {RAIZ / '.venv'}")
    print()
    if not si and input(" ¿Desinstalar Pandex? [s/N] ").strip().lower() not in ("s", "si", "sí", "y", "yes"):
        print(" No toqué nada.")
        return 2
    if cerrar_pandex_abierto():
        import time

        print(" Cerré Pandex, que estaba abierto.")
        time.sleep(2)
    quedan = ejecutar(pasos)
    print()
    print(" Listo: Pandex se desinstaló.")
    if quedan:
        print(" No pude borrar (quizás está en uso; ciérralo y bórralo a mano):")
        for ruta in quedan:
            print(f"   {ruta}")
    if conservar and (RAIZ / CONFIG_FILE.name).exists():
        print(f" Tu configuración quedó en {RAIZ / CONFIG_FILE.name}.")
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
