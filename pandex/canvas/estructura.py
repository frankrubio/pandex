"""Cómo está organizado un curso en Canvas, leído de sus módulos.

En Canvas un curso tiene **módulos** (``"Semana 3"``, ``"Sílabo"``…) y cada
módulo una lista de **ítems**: archivos, enlaces, tareas y **subencabezados**
(``"Material de clase"``, ``"Actividades"``…) que agrupan a los ítems que siguen.
Pandex copia esa organización a carpetas: semana → (teoría/lab) → sección.

Muchas universidades dan teoría y laboratorio como **dos cursos** de Canvas
(``"Programación I - Teoría 1"`` y ``"Programación I - Laboratorio 14"``); aquí
se reconocen como pareja para que compartan una carpeta.
"""

import html
import re
from collections import Counter
from dataclasses import dataclass, field

from . import drive
from .destinos import es_material_adicional
from .nombres import es_laboratorio, es_teoria, limpiar_nombre, normalizar, numero_de_semana

_RE_ARCHIVO_CANVAS = re.compile(r"(?:/courses/\d+)?/files/(\d+)(?=/|\?|$)", re.IGNORECASE)
_RE_ENLACE_HTML = re.compile(r'<a\b[^>]*?\bhref=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
_RE_ETIQUETAS = re.compile(r"<[^>]+>")


@dataclass
class Item:
    """Un archivo dentro de un módulo de Canvas (o enlazado en Google Drive)."""

    modulo: str     # nombre del módulo ("Semana 3")
    seccion: str    # subencabezado vigente, o None si el archivo va antes de todos
    titulo: str     # como lo muestra el módulo
    file_id: int | str
    bloqueado: bool = False  # el docente lo publicó pero aún no te deja abrirlo
    abre: str = None         # cuándo se abre (ISO), si Canvas lo dice
    url_externa: str = None  # enlace a Google Drive, si viene de ExternalUrl o de una página


def _id_archivo_canvas(url):
    m = _RE_ARCHIVO_CANVAS.search(str(url or ""))
    return int(m.group(1)) if m else None


def _texto_enlace(fragmento, respaldo=""):
    limpio = html.unescape(_RE_ETIQUETAS.sub(" ", fragmento or "")).strip()
    limpio = " ".join(limpio.split())
    return limpio or (respaldo or "").strip()


def enlaces_de_html(cuerpo_html, titulo_respaldo=""):
    """Extrae ``[(titulo, file_id, url_externa)]`` de los enlaces a Canvas o Google Drive en un HTML."""
    salida = []
    for href, contenido in _RE_ENLACE_HTML.findall(cuerpo_html or ""):
        url = html.unescape(href).strip()
        titulo = _texto_enlace(contenido, titulo_respaldo)
        info_drive = drive.extraer_drive(url)
        if info_drive:
            salida.append((titulo, f"drive_{info_drive['id']}", info_drive["url"]))
            continue
        fid = _id_archivo_canvas(url)
        if fid:
            salida.append((titulo, fid, None))
    return salida


def items_de_modulos(modulos):
    """Aplana los módulos de un curso en sus archivos (``Item``), en orden."""
    for modulo in modulos:
        nombre_mod = modulo.get("name") or ""
        seccion = None
        for item in modulo.get("items") or []:
            tipo = item.get("type")
            titulo = (item.get("title") or "").strip()
            detalles = item.get("content_details") or {}
            bloqueado = bool(detalles.get("locked_for_user"))
            abre = detalles.get("unlock_at")
            if tipo == "SubHeader":
                seccion = titulo
            elif tipo == "File":
                fid = item.get("content_id") or _id_archivo_canvas(item.get("url") or item.get("html_url"))
                if fid:
                    yield Item(nombre_mod, seccion, titulo, int(fid), bloqueado, abre)
            elif tipo in ("ExternalUrl", "ExternalTool"):
                url = (item.get("external_url") or item.get("url") or "").strip()
                info_drive = drive.extraer_drive(url)
                if info_drive:
                    yield Item(nombre_mod, seccion, titulo, f"drive_{info_drive['id']}",
                               bloqueado, abre, info_drive["url"])
                    continue
                fid = _id_archivo_canvas(url)
                if fid:
                    yield Item(nombre_mod, seccion, titulo, fid, bloqueado, abre)
            elif tipo in ("Page", "Assignment"):
                cuerpo = item.get("body") or item.get("description") or ""
                if not cuerpo:
                    continue
                seccion_item = titulo if (es_material_adicional(titulo) or not seccion) else seccion
                for t_enlace, fid, url_ext in enlaces_de_html(cuerpo, titulo):
                    yield Item(nombre_mod, seccion_item, t_enlace, fid, bloqueado, abre, url_ext)


# --------------------------------------------------------------------------
# emparejar la configuración con los cursos reales
# --------------------------------------------------------------------------


_TIPOS_TEORIA = {"teoria", "teo", "teor", "theory", "theo", "lecture", "lectures", "lec"}
_TIPOS_LAB = {"laboratorio", "laboratorios", "labo", "laboratory", "laboratories", "lab", "labs"}


def emparejar_cursos(cursos, reglas):
    """Asocia cada curso de la configuración con su curso real de Canvas.

    Una regla nombra su curso por ``canvas_id`` (lo que escribe el asistente) o
    por ``codigo`` + ``tipo`` (cómodo para escribir a mano: el código aparece en
    el nombre del curso, y ``tipo`` distingue ``"teoria"``/``"theory"``/``"lecture"``
    de ``"laboratorio"``/``"laboratory"``/``"lab"``).
    """
    parejas = []
    for regla in reglas:
        if regla.get("canvas_id"):
            parejas += [(regla, c) for c in cursos if c.get("id") == regla["canvas_id"]]
            continue
        codigo = normalizar(regla.get("codigo", ""))
        tipo = normalizar(regla.get("tipo") or "")
        es_tipo_lab = tipo in _TIPOS_LAB
        es_tipo_teo = tipo in _TIPOS_TEORIA
        for curso in cursos:
            crudo = f"{curso.get('name', '')} {curso.get('course_code', '')}"
            if not codigo or codigo not in normalizar(crudo):
                continue
            lab = es_laboratorio(crudo)
            teo = es_teoria(crudo)
            combinado = lab and teo
            if (es_tipo_lab and not lab) or (es_tipo_teo and lab and not combinado):
                continue
            parejas.append((regla, curso))
    return parejas


def alias_curso(regla, curso):
    """Nombre corto para los mensajes: el ``alias`` de la regla o el de Canvas."""
    if regla.get("alias"):
        return regla["alias"]
    nombre = nombre_corto(curso.get("name") or regla.get("codigo", "curso"))
    return nombre + (" (lab)" if normalizar(regla.get("tipo") or "") in _TIPOS_LAB else "")


# --------------------------------------------------------------------------
# análisis para el asistente
# --------------------------------------------------------------------------

# lo que distingue a dos cursos-pareja: «Teoría 1», «Laboratorio 1.01», «Lab. 11»
_MITAD = re.compile(
    r"(?<![a-z])(teor[ií]a|teo|theory|theo|lectures?|lec|laboratorio|laboratory|labs?)(?![a-z])"
    r"\.?\s*\d*(?:[.-]\d+)*[a-z]?(?![a-z0-9])",
    re.IGNORECASE,
)


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
