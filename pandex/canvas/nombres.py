"""Reglas de texto compartidas: comparar nombres, limpiarlos y leer semanas."""

import re
import unicodedata
from pathlib import Path

INVALIDOS_WINDOWS = r'<>:"/\|?*'
RE_SEMANA = re.compile(r"(?:sem(?:ana)?|week)\s*(\d{1,2})", re.IGNORECASE)
RE_LAB = re.compile(r"\blab(?:oratorio)?\b")


def normalizar(texto):
    """Para comparar nombres ignorando tildes, espacios, signos y mayúsculas.

    ``"Teoría"``, ``"teoria"`` y ``"TEORÍA_"`` dan lo mismo: ``"teoria"``.
    """
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", texto.lower())


def palabras(texto):
    """``"Fundamentos_de_Cálculo"`` -> ``["fundamentos", "de", "calculo"]``."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return [p for p in re.split(r"[^a-z0-9]+", texto) if p]


def limpiar_nombre(nombre):
    """Quita lo que Windows no acepta en un nombre, pero respeta tildes y espacios."""
    limpio = "".join("-" if c in INVALIDOS_WINDOWS else c for c in str(nombre))
    limpio = limpio.replace("\t", " ").strip().rstrip(".")
    return limpio or "archivo"


def separar_extension(nombre_real):
    """La extensión de verdad, sacada del nombre del archivo en Canvas.

    No se puede confiar en ``Path(titulo).suffix``: muchos títulos traen puntos en
    medio (``"Olcina, J., (2011). MEGACIUDADES…"``) y Python los toma como extensión.
    """
    sufijo = Path(nombre_real or "").suffix
    return sufijo if re.fullmatch(r"\.[A-Za-z0-9]{1,6}", sufijo) else ""


def nombre_destino(titulo, nombre_real, limite=200):
    """El nombre que muestra Canvas en el módulo, con la extensión correcta garantizada."""
    base = limpiar_nombre(titulo) if titulo and titulo.strip() else limpiar_nombre(nombre_real)
    ext = separar_extension(nombre_real)
    if ext and not base.lower().endswith(ext.lower()):
        base += ext
    if len(base) > limite:  # Windows no acepta rutas muy largas
        base = base[: limite - len(ext)].strip().rstrip(".") + ext
    return base


def numero_de_semana(texto):
    """``"Semana 7"`` -> 7, ``"Week 03 - Intro"`` -> 3, ``"Sílabo"`` -> None."""
    encontrado = RE_SEMANA.search(texto or "")
    return int(encontrado.group(1)) if encontrado else None


def es_laboratorio(nombre_curso):
    """«Laboratorio 14» o «Lab. 11» como palabra; no el «lab» de «colaborativo»."""
    return RE_LAB.search(str(nombre_curso).lower()) is not None
