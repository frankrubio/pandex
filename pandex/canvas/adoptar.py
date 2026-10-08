"""Usar una carpeta donde ya tenías tus cursos, y ordenarla como Canvas.

Tres pasos; el asistente muestra cada uno antes de hacer nada:

1. **Emparejar**: qué subcarpeta tuya corresponde a cada curso de Canvas
   (``Fundamentos_de_Calculo`` ↔ "Fundamentos del Cálculo").
2. **Convenciones**: cómo nombras tus semanas (``Sem 3``, ``Semana 03``…), tus
   mitades (``Teoría``/``Lab``) y tus secciones, para que lo nuevo se vea como lo tuyo.
3. **Reordenar**: cada archivo que viene de Canvas y está en otro lugar se mueve a
   donde Canvas dice que va. Las reglas:

   - se reconoce un archivo de Canvas por **nombre y tamaño exacto**; lo que no
     coincide (tu propio trabajo, tus notas) no se toca;
   - nunca se borra, se pisa ni se renombra nada: si el destino está ocupado o
     hay dos copias, el archivo se queda donde está;
   - cada movimiento se anota en ``%LOCALAPPDATA%\\Pandex\\reordenamientos\\`` y
     ``deshacer()`` lo devuelve a su lugar.
"""

import json
import re
import shutil
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..rutas import DATOS
from .destinos import carpeta_destino, ruta_vetada
from .nombres import limpiar_nombre, nombre_destino, normalizar, palabras

DIARIOS = DATOS / "reordenamientos"
MARCA_MD = "<!-- Pandex:"  # primera línea de los .md que genera «Convertir a Markdown»

# --------------------------------------------------------------------------
# 1. emparejar tus carpetas con los cursos
# --------------------------------------------------------------------------

_VACIAS = {"de", "del", "la", "las", "el", "los", "y", "e", "a", "en", "para", "por", "al", "con"}


def _fichas(texto):
    return [p for p in palabras(texto) if p not in _VACIAS]


def _siglas(fichas):
    """Iniciales de 2 a 4 palabras seguidas: "ciencia datos" -> "cd"."""
    salida = set()
    for largo in (2, 3, 4):
        for i in range(len(fichas) - largo + 1):
            salida.add("".join(f[0] for f in fichas[i:i + largo]))
    return salida


def parecido(nombre_curso, nombre_carpeta):
    """De 0 a 1: cuánto se parece el nombre de una carpeta al de un curso.

    Cuentan las palabras compartidas, las siglas (``CD`` = Ciencia de Datos) y el
    código del curso si la carpeta lo trae. Una letra suelta («I», «II») no
    alcanza sola para emparejar.
    """
    curso, carpeta = _fichas(nombre_curso), _fichas(nombre_carpeta)
    if not curso or not carpeta:
        return 0.0
    codigos = {f for f in curso if re.fullmatch(r"[a-z]+\d+[a-z0-9]*", f)}
    if codigos & set(carpeta):
        return 1.0
    siglas = _siglas(curso)
    peso = acierto = largas = 0.0
    for f in carpeta:
        p = 1.0 if len(f) >= 3 else 0.5
        peso += p
        if f in curso or f in siglas or (len(f) >= 4 and any(c.startswith(f) for c in curso)):
            acierto += p
            largas += len(f) >= 3 or f in siglas
    if not largas:
        return 0.0
    cubierto = sum(1 for c in curso if c in carpeta) / len(curso)
    return 0.75 * (acierto / peso) + 0.25 * cubierto


def emparejar_carpetas(nombres, carpetas, minimo=0.5):
    """``{clave: carpeta o None}``: a cada curso, la carpeta que más se le parece.

    ``nombres`` es ``{clave: nombre del curso}``. Cada carpeta se usa una sola vez.
    """
    puntajes = sorted(
        ((parecido(nombre, c.name), clave, c) for clave, nombre in nombres.items() for c in carpetas),
        key=lambda x: -x[0],
    )
    salida = dict.fromkeys(nombres)
    usadas = set()
    for puntaje, clave, carpeta in puntajes:
        if puntaje < minimo:
            break
        if salida[clave] is None and carpeta not in usadas:
            salida[clave] = carpeta
            usadas.add(carpeta)
    return salida


# --------------------------------------------------------------------------
# 2. tus convenciones
# --------------------------------------------------------------------------

PREFIJOS_SEMANA = {"sem", "semana", "s", "week", "w"}
TEORIA = {"teoria", "teo", "theory", "teorico", "teorica"}
LAB = {"lab", "labs", "laboratorio", "laboratorios", "practica", "practicas"}
_RE_CARPETA_SEMANA = re.compile(r"^(?P<pre>\D*?)(?P<num>\d{1,2})$")


@dataclass
class Convenciones:
    formato_semana: str = "Sem {n}"
    teoria: str = "Teoría"
    lab: str = "Lab"
    alias_teoria: list = field(default_factory=list)
    alias_lab: list = field(default_factory=list)
    secciones: list = field(default_factory=list)  # nombres de carpetas de sección que ya usas

    def describir(self):
        ejemplo = self.formato_semana.format(n=3)
        texto = f"semanas como «{ejemplo}» · mitades «{self.teoria}» y «{self.lab}»"
        if self.secciones:
            texto += " · secciones: " + ", ".join(f"«{s}»" for s in self.secciones[:4])
        return texto


def formato_de_carpeta_semana(nombre):
    """``"Semana 03"`` -> ``"Semana {n:02d}"``; None si no parece una semana."""
    m = _RE_CARPETA_SEMANA.match(nombre.strip())
    if not m or normalizar(m["pre"]) not in PREFIJOS_SEMANA:
        return None
    relleno = "{n:02d}" if len(m["num"]) == 2 and m["num"].startswith("0") else "{n}"
    return m["pre"] + relleno


def _subcarpetas(carpeta):
    try:
        return [h for h in carpeta.iterdir() if h.is_dir()]
    except OSError:
        return []


def detectar_convenciones(carpetas_curso):
    """Lee cómo tienes organizadas tus carpetas de curso (sin tocarlas)."""
    formatos, teorias, labs, secciones = Counter(), Counter(), Counter(), Counter()

    def mirar_secciones(carpeta):
        for s in _subcarpetas(carpeta):
            if normalizar(s.name) not in TEORIA | LAB and not formato_de_carpeta_semana(s.name):
                secciones[s.name] += 1

    for curso in carpetas_curso:
        for semana in _subcarpetas(curso):
            formato = formato_de_carpeta_semana(semana.name)
            if not formato:
                continue
            formatos[formato] += 1
            for hijo in _subcarpetas(semana):
                clave = normalizar(hijo.name)
                if clave in TEORIA:
                    teorias[hijo.name] += 1
                    mirar_secciones(hijo)
                elif clave in LAB:
                    labs[hijo.name] += 1
                    mirar_secciones(hijo)
            mirar_secciones(semana)

    conv = Convenciones()
    if formatos:
        conv.formato_semana = formatos.most_common(1)[0][0]
    if teorias:
        conv.teoria = teorias.most_common(1)[0][0]
        conv.alias_teoria = [n for n, _ in teorias.most_common()[1:]]
    if labs:
        conv.lab = labs.most_common(1)[0][0]
        conv.alias_lab = [n for n, _ in labs.most_common()[1:]]
    conv.secciones = [n for n, _ in secciones.most_common()]
    return conv


def _misma_seccion(a, b):
    """«Material de clase» y «Material de clases» son la misma sección."""
    na, nb = normalizar(a), normalizar(b)
    corto, largo = sorted((na, nb), key=len)
    return bool(corto) and largo.startswith(corto) and len(largo) - len(corto) <= 2


def mapa_secciones(subencabezados, existentes=()):
    """``{subencabezado de Canvas: carpeta}``.

    ``subencabezados`` es un ``Counter`` (los más usados primero). Usa tu nombre
    si ya tienes una carpeta para esa sección; si no, el de Canvas. Variantes casi
    iguales («Material de clase/clases») van a la misma carpeta.
    """
    mapa = {}
    for sub, _ in Counter(subencabezados).most_common():
        if not normalizar(sub):
            continue
        tuya = next((e for e in existentes if _misma_seccion(sub, e)), None)
        ya = next((carpeta for previo, carpeta in mapa.items() if _misma_seccion(sub, previo)), None)
        mapa[sub] = tuya or ya or limpiar_nombre(sub)
    return mapa


# --------------------------------------------------------------------------
# 3. reordenar
# --------------------------------------------------------------------------


@dataclass
class Movimiento:
    origen: Path
    destino: Path
    alias: str
    file_id: int
    tamano: int = None


@dataclass
class Plan:
    movimientos: list = field(default_factory=list)
    en_su_lugar: list = field(default_factory=list)  # (file_id, ruta, tamaño)
    dudosos: list = field(default_factory=list)      # (alias, nombre, motivo)


def _indice_por_nombre(carpeta, prohibidas):
    """nombre normalizado -> [(ruta, tamaño)] de los archivos del curso (sin los .md)."""
    indice = {}
    vetadas = {normalizar(p) for p in prohibidas}
    for ruta in carpeta.rglob("*"):
        if not ruta.is_file() or ruta.suffix.lower() == ".md" or ruta.name.lower() == "desktop.ini":
            continue
        if any(normalizar(parte) in vetadas for parte in ruta.parts):
            continue
        try:
            tamano = ruta.stat().st_size
        except OSError:
            continue
        indice.setdefault(normalizar(ruta.name), []).append((ruta, tamano))
    return indice


def planificar(candidatos, metas, carpetas, secciones, formato="Sem {n}"):
    """Qué mover y a dónde. No toca el disco.

    ``candidatos`` son los archivos de Canvas (``sincronizar.Candidato``),
    ``metas`` su ``{file_id: {"nombre", "tamano"}}`` y ``carpetas`` la carpeta de
    cada curso: ``{nombre de carpeta en la regla: Path}``.
    """
    plan = Plan()
    indices = {}
    por_ruta = {}  # ruta en disco -> [(candidato, carpeta destino, tamaño)]

    for c in candidatos:
        regla = c.regla
        carpeta = carpetas[regla["carpeta"]]
        prohibidas = regla.get("nunca_escribir", [])
        if carpeta not in indices:
            indices[carpeta] = _indice_por_nombre(carpeta, prohibidas)
        meta = metas.get(c.file_id) or {}
        tamano = meta.get("tamano")
        nombres = {normalizar(nombre_destino(c.item.titulo, meta.get("nombre")))}
        if meta.get("nombre"):
            nombres.add(normalizar(meta["nombre"]))
        mismos = [(r, t) for n in nombres for r, t in indices[carpeta].get(n, [])]
        if not mismos:
            continue  # no lo tienes: la sincronización lo bajará
        if not tamano:
            plan.dudosos.append((c.alias, mismos[0][0].name, "Canvas no informó su tamaño"))
            continue
        iguales = list({r: t for r, t in mismos if t == tamano})
        if not iguales:
            continue  # mismo nombre, otro contenido: es tuyo, no se toca
        if len(iguales) > 1:
            plan.dudosos.append((c.alias, iguales[0].name, f"tienes {len(iguales)} copias"))
            continue
        destino = carpeta_destino(carpeta, regla, c.item, c.semana, secciones, formato, crear=False)
        if destino is None or ruta_vetada(destino, prohibidas):
            continue
        por_ruta.setdefault(iguales[0], []).append((c, destino, tamano))

    reservados = set()
    for ruta, opciones in por_ruta.items():
        # el mismo archivo puede estar publicado en teoría y en lab: si ya está
        # en cualquiera de sus lugares válidos, se queda
        lugares = [d for _, d, _ in opciones]
        c, destino, tamano = opciones[0]
        if any(ruta.parent == d or str(ruta.parent).casefold() == str(d).casefold() for d in lugares):
            plan.en_su_lugar.append((c.file_id, ruta, tamano))
            continue
        final = destino / ruta.name
        clave = str(final).casefold()
        if final.exists() or clave in reservados:
            plan.dudosos.append((c.alias, ruta.name, "ya hay otro archivo con ese nombre donde va"))
            continue
        reservados.add(clave)
        plan.movimientos.append(Movimiento(ruta, final, c.alias, c.file_id, tamano))
    plan.movimientos.sort(key=lambda m: str(m.destino).casefold())
    return plan


def _md_de(ruta):
    """El .md que «Convertir a Markdown» generó junto a ese archivo, si existe."""
    for candidato in (ruta.with_suffix(".md"), ruta.with_name(f"{ruta.stem} ({ruta.suffix[1:].lower()}).md")):
        try:
            with open(candidato, encoding="utf-8", errors="replace") as fh:
                if fh.read(len(MARCA_MD) + 4).lstrip("﻿").startswith(MARCA_MD):
                    return candidato
        except OSError:
            continue
    return None


def aplicar(plan, historial=None, avance=None):
    """Hace los movimientos del plan. Devuelve ``(hechos, saltados, diario)``.

    Cada movimiento se anota en el diario en el momento: aunque algo se corte a
    mitad, ``deshacer`` sabe exactamente qué devolver.
    """
    DIARIOS.mkdir(parents=True, exist_ok=True)
    diario = DIARIOS / f"{datetime.now():%Y%m%d-%H%M%S}.jsonl"
    hechos, saltados = [], []
    with open(diario, "a", encoding="utf-8") as fh:
        for i, m in enumerate(plan.movimientos, start=1):
            if avance:
                avance(i, len(plan.movimientos))
            if not m.origen.exists() or m.destino.exists():
                saltados.append((m, "el origen ya no está o el destino se ocupó"))
                continue
            md = _md_de(m.origen)
            try:
                m.destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(m.origen), str(m.destino))
            except OSError as exc:
                saltados.append((m, str(exc)))
                continue
            fh.write(json.dumps([str(m.origen), str(m.destino)], ensure_ascii=False) + "\n")
            fh.flush()
            hechos.append(m)
            if historial is not None:
                historial.anotar(m.file_id, m.destino, m.tamano)
            if md is not None:
                destino_md = m.destino.parent / md.name
                if not destino_md.exists():
                    try:
                        shutil.move(str(md), str(destino_md))
                        fh.write(json.dumps([str(md), str(destino_md)], ensure_ascii=False) + "\n")
                    except OSError:
                        pass
    if historial is not None:
        for file_id, ruta, tamano in plan.en_su_lugar:
            historial.anotar(file_id, ruta, tamano)
    if not hechos:
        diario.unlink(missing_ok=True)
        diario = None
    return hechos, saltados, diario


def ultimo_diario():
    diarios = sorted(DIARIOS.glob("*.jsonl")) if DIARIOS.is_dir() else []
    return diarios[-1] if diarios else None


def deshacer(diario=None):
    """Devuelve a su lugar lo que movió un reordenamiento (el último, por defecto).

    Devuelve ``(devueltos, saltados)``. Un archivo que ya no está donde quedó, o
    cuyo lugar original volvió a ocuparse, se deja como está.
    """
    diario = diario or ultimo_diario()
    if diario is None:
        return 0, 0
    movimientos = [json.loads(l) for l in Path(diario).read_text(encoding="utf-8").splitlines() if l.strip()]
    devueltos = saltados = 0
    for origen, destino in reversed(movimientos):
        origen, destino = Path(origen), Path(destino)
        if not destino.exists() or origen.exists():
            saltados += 1
            continue
        origen.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(destino), str(origen))
        devueltos += 1
    Path(diario).replace(Path(diario).with_suffix(".deshecho"))
    return devueltos, saltados
