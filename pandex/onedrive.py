"""OneDrive en Linux: tu OneDrive como una carpeta más, con rclone.

Microsoft no tiene app de OneDrive para Linux. Pandex usa ``rclone`` para *montar* cada
cuenta en una carpeta de tu casa, igual que en Windows:

- cuenta personal → ``~/OneDrive``
- cuenta de la universidad (u otra) → ``~/OneDrive - <nombre>``

Así todo lo demás (bajar de Canvas, ordenar, convertir a Markdown) funciona igual, directo
en tu OneDrive. Lo que escribe Pandex se sube en segundo plano.

Pandex usa su propio archivo de rclone (``rclone.conf`` en su carpeta de datos), así que no
toca otras configuraciones de rclone que tengas. Tu contraseña la escribes tú en la página de
Microsoft: Pandex nunca la ve.

En Windows no hace falta nada de esto: la app de OneDrive ya crea esas carpetas.
"""

import configparser
import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from .log import get_logger
from .rutas import DATOS, WINDOWS

log = get_logger("pandex.onedrive")

CONF = DATOS / "rclone.conf"
CUENTAS = DATOS / "onedrive.json"
ENLACE = re.compile(r"https?://127\.0\.0\.1:\d+/auth\S*")
INSTALAR = "sudo apt install rclone fuse3"


@dataclass
class Cuenta:
    remoto: str  # nombre de la cuenta dentro de rclone.conf
    nombre: str  # lo que ves: «UTEC», «Personal»…
    tipo: str  # "personal" o "business" (lo dice Microsoft)
    carpeta: str

    @property
    def ruta(self):
        return Path(self.carpeta)


class ErrorOneDrive(Exception):
    """Un problema que se le puede decir al usuario tal cual."""


# ---------- disponibilidad ----------

def rclone():
    return shutil.which("rclone")


def disponible():
    """Solo en Linux (y macOS) y con rclone instalado."""
    return not WINDOWS and rclone() is not None


def _rclone(*args):
    return [rclone() or "rclone", "--config", str(CONF), *args]


# ---------- cuentas guardadas ----------

def cuentas():
    try:
        datos = json.loads(CUENTAS.read_text(encoding="utf-8"))
        return [Cuenta(**c) for c in datos]
    except (OSError, ValueError, TypeError):
        return []


def _guardar(lista):
    CUENTAS.parent.mkdir(parents=True, exist_ok=True)
    temporal = CUENTAS.with_suffix(".tmp")
    temporal.write_text(json.dumps([asdict(c) for c in lista], ensure_ascii=False, indent=2),
                        encoding="utf-8")
    temporal.replace(CUENTAS)


def _slug(nombre):
    base = re.sub(r"[^a-z0-9]+", "-", nombre.casefold()).strip("-") or "cuenta"
    usados = {c.remoto for c in cuentas()}
    remoto, n = f"pandex-{base}", 2
    while remoto in usados:
        remoto, n = f"pandex-{base}-{n}", n + 1
    return remoto


def _limpiar_nombre(nombre):
    """Sirve como nombre de carpeta: sin barras ni espacios de más."""
    nombre = re.sub(r"[/\\:*?\"<>|]+", " ", str(nombre or "")).strip()
    return re.sub(r"\s+", " ", nombre)[:40]


def carpeta_para(nombre, tipo, casa=None):
    """``~/OneDrive`` para la primera cuenta personal; ``~/OneDrive - <nombre>`` para el resto.

    Es el mismo nombre que usa Windows, así el resto de Pandex (y tú) las reconoce igual.
    """
    casa = Path(casa or Path.home())
    ocupadas = {c.ruta for c in cuentas()}
    if tipo == "personal" and casa / "OneDrive" not in ocupadas:
        return casa / "OneDrive"
    return casa / f"OneDrive - {_limpiar_nombre(nombre) or 'Cuenta'}"


def _tipo(remoto):
    conf = configparser.ConfigParser(interpolation=None)
    try:
        conf.read(CONF, encoding="utf-8")
        return conf.get(remoto, "drive_type", fallback="personal")
    except configparser.Error:
        return "personal"


# ---------- conectar ----------

class Conexion:
    """Inicia sesión en Microsoft (en tu navegador) y monta la cuenta.

    ``ejecutar()`` corre en un hilo aparte: tarda lo que tardes en iniciar sesión.
    ``cancelar()`` se puede llamar desde la ventana mientras tanto.
    """

    def __init__(self, nombre):
        self.nombre = _limpiar_nombre(nombre)
        self.proceso = None
        self.cancelada = False

    def cancelar(self):
        self.cancelada = True
        if self.proceso is not None and self.proceso.poll() is None:
            self.proceso.kill()

    def ejecutar(self, al_enlace=None):
        """Devuelve la ``Cuenta``. rclone abre el navegador solo; ``al_enlace(url)`` recibe el
        enlace por si no se abrió."""
        if not self.nombre:
            raise ErrorOneDrive("Ponle un nombre a la cuenta, por ejemplo «UTEC» o «Personal».")
        if not disponible():
            raise ErrorOneDrive(f"Falta rclone. Instálalo con: {INSTALAR}")
        remoto = _slug(self.nombre)
        CONF.parent.mkdir(parents=True, exist_ok=True)
        self.proceso = subprocess.Popen(_rclone("config", "create", remoto, "onedrive"),
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        text=True, encoding="utf-8", errors="replace")
        salida = []
        with self.proceso:
            for linea in self.proceso.stdout:
                salida.append(linea.rstrip())
                enlace = ENLACE.search(linea)
                if enlace and al_enlace:
                    al_enlace(enlace.group(0))
        if self.cancelada:
            _borrar_remoto(remoto)
            raise ErrorOneDrive("Cancelaste la conexión con OneDrive.")
        if self.proceso.returncode != 0:
            _borrar_remoto(remoto)
            log.error("rclone config create falló:\n%s", "\n".join(salida[-20:]))
            raise ErrorOneDrive("No pude conectar tu OneDrive. El motivo exacto está en «Ver registro».")

        tipo = _tipo(remoto)
        cuenta = Cuenta(remoto, self.nombre, tipo, str(carpeta_para(self.nombre, tipo)))
        _guardar([*cuentas(), cuenta])
        log.info("OneDrive conectado: %s (%s) en %s", self.nombre, tipo, cuenta.carpeta)
        montar(cuenta)
        return cuenta


def _borrar_remoto(remoto):
    try:
        subprocess.run(_rclone("config", "delete", remoto), capture_output=True, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError):
        pass


def quitar(cuenta):
    """Desconecta la cuenta. Tus archivos siguen en OneDrive; solo deja de verse aquí."""
    desmontar(cuenta)
    _borrar_remoto(cuenta.remoto)
    _guardar([c for c in cuentas() if c.remoto != cuenta.remoto])
    try:
        cuenta.ruta.rmdir()  # solo si quedó vacía
    except OSError:
        pass
    log.info("OneDrive desconectado: %s", cuenta.nombre)


# ---------- montar ----------

def montada(cuenta):
    return os.path.ismount(cuenta.ruta)


def montar(cuenta):
    """Monta la cuenta en su carpeta. Si ya está montada, no hace nada."""
    if montada(cuenta):
        return
    if not disponible():
        raise ErrorOneDrive(f"Falta rclone. Instálalo con: {INSTALAR}")
    carpeta = cuenta.ruta
    carpeta.mkdir(parents=True, exist_ok=True)
    if any(carpeta.iterdir()):
        raise ErrorOneDrive(f"La carpeta «{carpeta}» no está vacía, así que no monto ahí tu OneDrive. "
                            "Mueve lo que tiene a otro lado e inténtalo de nuevo.")
    registro = DATOS / f"rclone-{cuenta.remoto}.log"
    comando = _rclone("mount", f"{cuenta.remoto}:", str(carpeta),
                      "--vfs-cache-mode", "full",  # se puede abrir, editar y mover como en un disco
                      "--daemon", "--log-file", str(registro), "--log-level", "NOTICE")
    try:
        # sin capturar la salida: el rclone que queda en segundo plano heredaría la tubería
        # y esto esperaría para siempre. Lo que diga queda en su archivo de registro.
        r = subprocess.run(comando, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=90, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ErrorOneDrive("OneDrive tardó demasiado en responder. Revisa tu internet.") from exc
    if r.returncode != 0 or not montada(cuenta):
        try:
            detalle = registro.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-5:]
        except OSError:
            detalle = []
        log.error("rclone mount falló (%s): %s", r.returncode, detalle or "sin salida")
        texto = " ".join(detalle).lower()
        if "fusermount" in texto or "fuse" in texto:
            raise ErrorOneDrive(f"Falta FUSE para montar OneDrive. Instálalo con: {INSTALAR}")
        if "token" in texto or "unauthorized" in texto or "invalid_grant" in texto:
            raise ErrorOneDrive("Tu sesión de OneDrive caducó: quita la cuenta y conéctala de nuevo.")
        raise ErrorOneDrive("No pude abrir tu OneDrive. El motivo exacto está en «Ver registro».")
    log.info("OneDrive montado: %s en %s", cuenta.nombre, carpeta)


def desmontar(cuenta):
    if not montada(cuenta):
        return
    for comando in (["fusermount3", "-u"], ["fusermount", "-u"], ["umount"]):
        if shutil.which(comando[0]):
            subprocess.run([*comando, str(cuenta.ruta)], capture_output=True, timeout=30, check=False)
            if not montada(cuenta):
                return
    log.warning("no pude desmontar %s (¿hay un archivo abierto ahí?)", cuenta.ruta)


def montar_todas():
    """Al abrir Pandex. Devuelve los errores (para avisar), sin lanzar excepciones."""
    errores = []
    if WINDOWS:
        return errores
    for cuenta in cuentas():
        try:
            montar(cuenta)
        except (ErrorOneDrive, OSError) as exc:
            log.warning("OneDrive %s: %s", cuenta.nombre, exc)
            errores.append(f"{cuenta.nombre}: {exc}")
    return errores


def asegurar(ruta):
    """Antes de escribir en ``ruta``: si está dentro de un OneDrive, que esté montado.

    Sin esto, con el OneDrive sin montar Pandex escribiría en la carpeta vacía de tu PC y no
    en la nube. Devuelve un mensaje de error, o ``None`` si se puede seguir.
    """
    ruta = Path(ruta)
    for cuenta in cuentas():
        if ruta == cuenta.ruta or cuenta.ruta in ruta.parents:
            try:
                montar(cuenta)
            except (ErrorOneDrive, OSError) as exc:
                return f"Tu OneDrive «{cuenta.nombre}» no está disponible: {exc}"
    return None
