"""Pruebas de Pandex. Ninguna usa internet ni toca tus datos reales.

    .venv\\Scripts\\python.exe -m unittest discover -s tests -t .

Antes de importar nada de Pandex se apunta su carpeta de datos a una carpeta
temporal y Qt a una pantalla invisible.
"""

import logging
import os
import tempfile

os.environ["PANDEX_DATOS"] = tempfile.mkdtemp(prefix="pandex-pruebas-")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandex.log  # noqa: E402

# las pruebas no escriben en logs/pandex.log ni ensucian la consola
pandex.log._CONFIGURADO = True
logging.getLogger("pandex").addHandler(logging.NullHandler())
logging.getLogger("pandex").propagate = False
