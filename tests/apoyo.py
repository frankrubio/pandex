"""Piezas compartidas por las pruebas: un Canvas de mentira y un ctx de mentira."""

import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from pandex.canvas import sincronizar
from pandex.canvas.cliente import CanvasError


def modulo(nombre, *items):
    """``modulo("Semana 6", ("sub", "Material de clase"), ("file", "Clase.pdf", 101))``."""
    salida = []
    for item in items:
        if item[0] == "sub":
            salida.append({"type": "SubHeader", "title": item[1]})
        else:
            salida.append({"type": "File", "title": item[1], "content_id": item[2]})
    return {"name": nombre, "items": salida}


class CanvasFalso:
    """Imita ``pandex.canvas.cliente.Canvas`` con datos fijos.

    ``archivos`` es ``{file_id: (nombre real, tamaño)}``. Cuenta las llamadas y
    puede hacer fallar descargas a propósito.
    """

    cursos_ = []
    modulos_ = {}
    archivos = {}
    fallar = set()       # estas descargas fallan
    incompletos = set()  # estas llegan con menos bytes
    llamadas = {}
    _candado = threading.Lock()

    def __init__(self, *_args):
        pass

    @classmethod
    def reiniciar(cls, cursos, modulos, archivos):
        cls.cursos_, cls.modulos_, cls.archivos = cursos, modulos, archivos
        cls.fallar, cls.incompletos = set(), set()
        cls.contar_cero()

    @classmethod
    def contar_cero(cls):
        cls.llamadas = {"archivo": 0, "listado": 0, "modulos": 0, "descargar": 0}

    def _contar(self, clave):
        with self._candado:
            self.llamadas[clave] += 1

    def cursos(self):
        return list(self.cursos_)

    def modulos(self, curso_id):
        self._contar("modulos")
        return self.modulos_.get(curso_id, [])

    def archivos_del_curso(self, _curso_id):
        self._contar("listado")
        return None  # como en UTEC: 403

    def archivo(self, _curso_id, file_id):
        self._contar("archivo")
        nombre, tamano = self.archivos[file_id]
        return {"nombre": nombre, "tamano": tamano}

    def descargar(self, _curso_id, file_id, destino_tmp, espera_html=False):
        self._contar("descargar")
        if file_id in self.fallar:
            raise CanvasError("Canvas devolvió una página, no el archivo")
        tamano = self.archivos[file_id][1] - (100 if file_id in self.incompletos else 0)
        Path(destino_tmp).write_bytes(bytes([file_id % 251]) * tamano)
        return tamano


class CtxFalso:
    """Lo mínimo de ``TaskContext`` que usan las tareas."""

    def __init__(self, params, entrada=None):
        self.params = params
        self.config = {}
        self.entrada = entrada
        self.globos = []
        self.registro = []

    def log(self, mensaje, nivel="info"):
        self.registro.append((nivel, mensaje))

    def decir(self, texto):
        self.globos.append(texto)

    def progreso(self, _n, _total):
        pass

    def guardar(self):
        pass


class ConCarpetaTemporal(unittest.TestCase):
    """Cada prueba trabaja en su propia carpeta temporal, y con Canvas falso."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pandex-prueba-"))
        self._originales = (sincronizar.Canvas, sincronizar.sesion.iniciar_sesion,
                            sincronizar.TEMPORAL)
        sincronizar.Canvas = CanvasFalso
        sincronizar.sesion.iniciar_sesion = lambda *a, **k: ([], "ua")
        sincronizar.TEMPORAL = self.tmp / "_tmp"

    def tearDown(self):
        (sincronizar.Canvas, sincronizar.sesion.iniciar_sesion,
         sincronizar.TEMPORAL) = self._originales
        shutil.rmtree(self.tmp, ignore_errors=True)
        historial = sincronizar.Historial().ruta
        historial.unlink(missing_ok=True)  # el historial vive en la carpeta de datos de prueba

    def sincronizar(self, params, entrada=None):
        CanvasFalso.contar_cero()
        ctx = CtxFalso(params, entrada)
        return sincronizar.Sincronizacion(ctx).ejecutar(), ctx
