"""Convertir a Markdown en un proceso aparte, para que Pandex vuelva a quedar liviano.

MarkItDown y sus lectores (PDF, Office, imágenes) ocupan unos 110 MB en memoria, y
Python no puede descargarlos una vez cargados. Si la conversión corriera dentro de
Pandex, la mascota quedaría con esos 110 MB hasta cerrarla. Por eso corre en un
proceso hijo: al terminar, el hijo se cierra y Windows recupera toda esa memoria.

Comunicación: el padre manda ``{"params", "entrada"}`` en JSON por stdin; el hijo
responde por stdout, una línea por mensaje con el prefijo ``MARCA``:
``{"log": [msg, nivel]}``, ``{"decir": texto}``, ``{"progreso": [n, total]}`` y, al
final, ``{"resultado": {...}}``. Cualquier otra línea (avisos de alguna librería) va al
registro.
"""

import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

from ..rutas import RAIZ

MARCA = "\x1ePANDEX "
_SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _python():
    """``python.exe`` junto al intérprete actual (con ``pythonw`` no hay stdout fiable)."""
    actual = Path(sys.executable)
    consola = actual.with_name("python.exe")
    return str(consola) if actual.name.lower() == "pythonw.exe" and consola.exists() else str(actual)


def convertir_aparte(ctx):
    """Igual que ``lote.convertir(ctx)``, pero en un proceso hijo. Si no puede lanzarlo,
    convierte aquí mismo (más memoria, mismo resultado)."""
    pedido = json.dumps({"params": ctx.params, "entrada": ctx.entrada}, default=str, ensure_ascii=False)
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    try:
        hijo = subprocess.Popen(
            [_python(), "-m", "pandex.markdown.proceso"], cwd=str(RAIZ), env=entorno,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", creationflags=_SIN_VENTANA,
        )
    except OSError as exc:
        ctx.log(f"no pude abrir el proceso de conversión ({exc}); convierto aquí", "warning")
        from .lote import convertir

        return convertir(ctx)

    resultado = None
    with hijo:  # cierra los canales y espera al hijo al salir
        hijo.stdin.write(pedido)
        hijo.stdin.close()
        for linea in hijo.stdout:
            if not linea.startswith(MARCA):
                if linea.strip():
                    ctx.log(f"conversión: {linea.rstrip()}", "warning")
                continue
            mensaje = json.loads(linea[len(MARCA):])
            if "progreso" in mensaje:
                ctx.progreso(*mensaje["progreso"])
            elif "decir" in mensaje:
                ctx.decir(mensaje["decir"])
            elif "log" in mensaje:
                ctx.log(*mensaje["log"])
            elif "resultado" in mensaje:
                resultado = mensaje["resultado"]
    codigo = hijo.returncode
    if resultado is None:
        return {"ok": False, "resumen": "La conversión se cerró de golpe. Mira el registro.",
                "detalle": [f"el proceso de conversión terminó con código {codigo}"]}
    return resultado


# ---------- el proceso hijo ----------


class _CtxHijo:
    def __init__(self, params, entrada):
        self.params = params
        self.entrada = entrada
        self.config = {}

    @staticmethod
    def _enviar(**mensaje):
        sys.stdout.write(MARCA + json.dumps(mensaje, default=str, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    def log(self, msg, nivel="info"):
        self._enviar(log=[str(msg), nivel])

    def decir(self, texto):
        self._enviar(decir=str(texto))

    def progreso(self, n, total):
        self._enviar(progreso=[int(n), int(total)])

    def guardar(self):
        pass  # el hijo no toca config.json


def _main():
    pedido = json.loads(sys.stdin.read())
    ctx = _CtxHijo(pedido.get("params") or {}, pedido.get("entrada"))
    try:
        from .lote import convertir

        resultado = convertir(ctx)
    except Exception as exc:
        resultado = {"ok": False, "resumen": f"Error: {exc}", "detalle": traceback.format_exc().splitlines()}
    ctx._enviar(resultado=resultado)
    return 0


if __name__ == "__main__":
    sys.exit(_main())
