"""Volver a adaptar Pandex a tu carpeta de cursos cuando la renombraste o la moviste (spec 009).

``adaptar`` solo calcula: no escribe nada, no mueve ni renombra carpetas y no modifica lo que
recibe. La ventana de Configuración muestra el resumen y, si confirmas, guarda el resultado.
Los cursos se emparejan por el nombre de carpeta que ya tiene cada regla (y su nombre en
Canvas), sin iniciar sesión.
"""

import copy
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import adoptar


class ErrorReconectar(Exception):
    """Algo que se le puede decir al usuario tal cual."""


@dataclass
class Informe:
    destino: str
    parejas: list = field(default_factory=list)      # [(nombre anterior, carpeta que encontró)]
    sin_pareja: list = field(default_factory=list)   # nombres anteriores sin carpeta (se crearán al sincronizar)
    estilo: str = ""

    def texto(self):
        lineas = [f"Carpeta de cursos: {self.destino}", ""]
        for antes, ahora in self.parejas:
            lineas.append(f"✓ {antes} → {ahora}" if antes != ahora else f"✓ {ahora}")
        if self.sin_pareja:
            lineas += ["", "No encontré carpeta para (se creará al sincronizar):"]
            lineas += [f"• {nombre}" for nombre in self.sin_pareja]
        if self.estilo:
            lineas += ["", self.estilo]
        return "\n".join(lineas)


def _subcarpetas(raiz):
    try:
        return sorted((h for h in Path(raiz).iterdir() if h.is_dir()), key=lambda h: h.name.casefold())
    except OSError as exc:
        raise ErrorReconectar(f"No puedo leer esa carpeta: {exc.strerror or exc}") from exc


def _emparejar(reglas, carpetas):
    """``{nombre anterior: carpeta}``. Una carpeta sirve a un solo curso."""
    textos = {}
    for regla in reglas:
        propios = textos.setdefault(regla["carpeta"], [regla["carpeta"]])
        propios += [t for t in (regla.get("nombre_canvas"), regla.get("alias")) if t]
    puntajes = sorted(
        ((max(adoptar.parecido(t, c.name) for t in propios), antes, c)
         for antes, propios in textos.items() for c in carpetas),
        key=lambda x: -x[0])
    salida, usadas = {}, set()
    for puntaje, antes, carpeta in puntajes:
        if puntaje < 0.5:
            break
        if antes not in salida and carpeta not in usadas:
            salida[antes] = carpeta
            usadas.add(carpeta)
    return salida


def adaptar(params, nueva):
    """``(params nuevos, Informe)`` para esa carpeta. Lanza ``ErrorReconectar`` si no sirve."""
    nueva = Path(nueva)
    if not nueva.is_dir():
        raise ErrorReconectar("Esa carpeta no existe. Elige la carpeta donde están las carpetas de tus cursos.")
    carpetas = _subcarpetas(nueva)

    nuevos = copy.deepcopy(params)
    nuevos["destino"] = str(nueva)
    reglas = nuevos.get("cursos", [])
    parejas = _emparejar(reglas, carpetas)
    informe = Informe(str(nueva))
    vistos = set()
    for regla in reglas:
        antes = regla["carpeta"]
        if antes in parejas:
            regla["carpeta"] = parejas[antes].name
        if antes not in vistos:
            vistos.add(antes)
            if antes in parejas:
                informe.parejas.append((antes, parejas[antes].name))
            else:
                informe.sin_pareja.append(antes)

    conv = adoptar.detectar_convenciones([parejas[a] for a in vistos if a in parejas])
    if conv.detectada:
        nuevos["formato_semana"] = conv.formato_semana
        nuevos["estilo_carpetas"] = "propio"
        informe.estilo = f"Tu estilo: {conv.describir()}."
    nuevos.pop("carpetas_sin_tildes", None)
    return nuevos, informe


def guardar_copia(params, datos):
    """Copia de la configuración de Canvas anterior, por si no te gusta el resultado."""
    from ..limpieza import COPIAS_DE_CONFIG_QUE_QUEDAN, limitar

    datos = Path(datos)
    datos.mkdir(parents=True, exist_ok=True)
    copia = datos / f"config-canvas-anterior-{datetime.now():%Y%m%d-%H%M%S}.json"
    copia.write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")
    limitar(datos, "config-canvas-anterior-*.json", COPIAS_DE_CONFIG_QUE_QUEDAN)
    return copia
