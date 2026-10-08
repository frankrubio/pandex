"""Cómo está organizado un curso en Canvas, leído de sus módulos.

En Canvas un curso tiene **módulos** (``"Semana 3"``, ``"Sílabo"``…) y cada
módulo una lista de **ítems**: archivos, enlaces, tareas y **subencabezados**
(``"Material de clase"``, ``"Actividades"``…) que agrupan a los ítems que siguen.
Pandex copia esa organización a carpetas: semana → (teoría/lab) → sección.

Muchas universidades dan teoría y laboratorio como **dos cursos** de Canvas
(``"Programación I - Teoría 1"`` y ``"Programación I - Laboratorio 14"``); aquí
se reconocen como pareja para que compartan una carpeta.
"""

import re
from collections import Counter
from dataclasses import dataclass, field

from .nombres import es_laboratorio, limpiar_nombre, normalizar, numero_de_semana


@dataclass
class Item:
    """Un archivo dentro de un módulo de Canvas."""

    modulo: str     # nombre del módulo ("Semana 3")
    seccion: str    # subencabezado vigente, o None si el archivo va antes de todos
    titulo: str     # como lo muestra el módulo
    file_id: int
    bloqueado: bool = False  # el docente lo publicó pero aún no te deja abrirlo
    abre: str = None         # cuándo se abre (ISO), si Canvas lo dice


def items_de_modulos(modulos):
    """Aplana los módulos de un curso en sus archivos (``Item``), en orden."""
    for modulo in modulos:
        seccion = None
        for item in modulo.get("items") or []:
            tipo = item.get("type")
            if tipo == "SubHeader":
                seccion = item.get("title") or ""
            elif tipo == "File" and item.get("content_id"):
                detalles = item.get("content_details") or {}
                yield Item(modulo.get("name") or "", seccion,
                           (item.get("title") or "").strip(), item["content_id"],
                           bool(detalles.get("locked_for_user")), detalles.get("unlock_at"))


# --------------------------------------------------------------------------
# emparejar la configuración con los cursos reales
# --------------------------------------------------------------------------


def emparejar_cursos(cursos, reglas):
    """Asocia cada curso de la configuración con su curso real de Canvas.

    Una regla nombra su curso por ``canvas_id`` (lo que escribe el asistente) o
    por ``codigo`` + ``tipo`` (cómodo para escribir a mano: el código aparece en
    el nombre del curso, y ``tipo`` distingue ``"teoria"`` de ``"laboratorio"``).
    """
    parejas = []
    for regla in reglas:
        if regla.get("canvas_id"):
            parejas += [(regla, c) for c in cursos if c.get("id") == regla["canvas_id"]]
            continue
        codigo = normalizar(regla.get("codigo", ""))
        tipo = (regla.get("tipo") or "").lower()
        for curso in cursos:
            crudo = f"{curso.get('name', '')} {curso.get('course_code', '')}"
            if not codigo or codigo not in normalizar(crudo):
                continue
            lab = es_laboratorio(crudo)
            if (tipo == "laboratorio" and not lab) or (tipo == "teoria" and lab):
                continue
            parejas.append((regla, curso))
    return parejas


def alias_curso(regla, curso):
    """Nombre corto para los mensajes: el ``alias`` de la regla o el de Canvas."""
    if regla.get("alias"):
        return regla["alias"]
    nombre = nombre_corto(curso.get("name") or regla.get("codigo", "curso"))
    return nombre + (" (lab)" if (regla.get("tipo") or "") == "laboratorio" else "")


# --------------------------------------------------------------------------
# análisis para el asistente
# --------------------------------------------------------------------------

# lo que distingue a dos cursos-pareja: «Teoría 1», «Teo. 1», «Laboratorio 14», «Lab. 11»
_MITAD = re.compile(r"\b(teor[ií]a|teo|laboratorio|lab)\b\.?\s*\d*", re.IGNORECASE)


def nombre_corto(nombre):
    """``"Programación I (CS6002) - Teoría 1 - 2026 - 2"`` -> ``"Programación I"``."""
    corto = nombre.split(" (")[0] if " (" in nombre else nombre.split(" - ")[0]
    return limpiar_nombre(corto.strip()) if corto.strip() else limpiar_nombre(nombre)


def clave_de_pareja(nombre):
    """El nombre del curso sin la parte teoría/lab: igual para los dos de una pareja."""
    return normalizar(_MITAD.sub(" ", nombre))


@dataclass
class Resumen:
    """Lo que el asistente muestra de cada curso."""

    curso: dict
    semanas: list = field(default_factory=list)      # números de semana con archivos
    otros: list = field(default_factory=list)        # módulos sin semana que tienen archivos
    secciones: Counter = field(default_factory=Counter)  # subencabezado -> nº de archivos
    archivos: int = 0

    @property
    def nombre(self):
        return self.curso.get("name") or str(self.curso.get("id"))

    @property
    def es_lab(self):
        return es_laboratorio(self.nombre)

    def describir(self):
        partes = []
        if self.semanas:
            partes.append(f"{len(self.semanas)} semana(s)")
        if self.otros:
            partes.append(f"{len(self.otros)} módulo(s) más")
        partes.append(f"{self.archivos} archivo(s)")
        return " · ".join(partes)


def resumir(curso, modulos):
    resumen = Resumen(curso)
    semanas, otros = set(), []
    for item in items_de_modulos(modulos):
        resumen.archivos += 1
        n = numero_de_semana(item.modulo)
        if n is not None:
            semanas.add(n)
        elif item.modulo not in otros:
            otros.append(item.modulo)
        if item.seccion:
            resumen.secciones[item.seccion.strip()] += 1
    resumen.semanas = sorted(semanas)
    resumen.otros = otros
    return resumen


def agrupar(resumenes):
    """Junta los cursos que son teoría y laboratorio de lo mismo.

    Devuelve una lista de grupos (listas de ``Resumen``). Un grupo de uno es un
    curso normal; uno de varios comparte carpeta con mitades «Teoría» y «Lab».
    Un curso que en su nombre trae ambas cosas (``"Teo. 1 - Lab. 11"``) queda solo.
    """
    grupos = {}
    for r in resumenes:
        grupos.setdefault(clave_de_pareja(r.nombre), []).append(r)
    salida = []
    for grupo in grupos.values():
        hay_teoria = any(not r.es_lab for r in grupo)
        hay_lab = any(r.es_lab for r in grupo)
        if len(grupo) > 1 and hay_teoria and hay_lab:
            salida.append(sorted(grupo, key=lambda r: r.es_lab))  # teoría primero
        else:
            salida.extend([r] for r in grupo)
    return salida
