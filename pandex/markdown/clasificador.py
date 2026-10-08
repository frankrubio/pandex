"""¿Es material de estudio? Reglas fijas y legibles, sin IA.

Se usan en el botón «Material de estudio» de Convertir a Markdown para dejar
fuera tareas, evaluaciones, plantillas y trabajos propios.
"""

import re
import unicodedata
from pathlib import Path

# clasificación: ¿es material de estudio?
# --------------------------------------------------------------------------
#
# Reglas fijas, en este orden. Gana la PRIMERA que aplica:
#
#   1. formato     solo PDF, Word, PowerPoint, Excel y EPUB son material de estudio
#                  (HTML, CSV, JSON, XML e imágenes quedan para el botón «Todos»)
#   2. carpeta     dentro de «Trabajos…» o «Entregas…» es trabajo tuyo, no material
#   3. nombre NO   AP, TA, ED, EA, PC, EP, EF, tarea, evaluación, examen, preguía,
#                  ejercicios, plantilla, sílabo, horario…
#   4. nombre SÍ   clase, guía, resumen, lectura, teoría, semana, capítulo… o un
#                  título en inglés con guiones bajos como los que exporta NotebookLM
#                  (Trigonometry_Toolkit, Sinusoidal_Dynamics)
#   5. carpeta NO  dentro de «Actividades», «Tareas», «Evaluaciones»,
#                  «Información del curso» o «Syllabus»
#   6. si nada dice lo contrario, SÍ es material de estudio
#
# Los patrones se buscan en el nombre "normalizado": sin tildes, en minúsculas y
# con cualquier signo convertido en espacio («AP3_Sem4» -> «ap3 sem4»).

FORMATOS_ESTUDIO = {".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".epub"}

NOMBRE_NO = [
    ("actividad previa", r"\bap\d*\b|\bactividad(es)? previas?\b"),
    ("tarea", r"\bta\d*\b|\btareas?\d*\b|\benunciados?\b"),
    ("evaluación", r"\b(ed|ea|pc|ep|ef)\d*\b|\bevaluacion(es)?\b|\bexamen(es)?\b"
                   r"|\beva\d*\b|\bpractica calificada\b|\bsolucionario\b"),
    ("preguía de ejercicios", r"\bpre ?guias?\b"),
    ("administrativo", r"\bsilabos?\b|\bsyllabus\b|\bhorarios?\b|\bcronogramas?\b"
                       r"|\bplantillas?\b|\bformatos?\b|\bconsentimientos?\b|\brubricas?\b"),
]
# una lista de ejercicios es trabajo por hacer; "teoría y ejercicios" sí se estudia.
# En plural: «Traducción y ejercicio de Writing…» es una clase, no una lista.
# «Problema_Fun_Cuadratica» es un enunciado; «VRD_el PROBLEMA de investigación», no.
EJERCICIOS = re.compile(r"\bejercicios\b|^problemas?\b")
CON_TEORIA = re.compile(r"\bteo(ria)?\b")

NOMBRE_SI = [
    ("guía", r"\bguias?\b"),
    ("resumen", r"\bresumen(es)?\b|\bsintesis\b|\btoolkit\b|\barsenal\b|\bcheat ?sheet\b"
                r"|\bformulario\b|\binfografia\b|\bmapa conceptual\b|\bapuntes\b"
                r"|\bsummary\b|\boverview\b"),
    ("material de clase", r"\bclases?\b|\bsesion(es)?\b|\bteo(ria)?\b|\bsemana\d*\b"
                          r"|\bcapitulo\b|\bpresentacion\b|\btema\b|\bunidad\b"),
    ("lectura", r"\blecturas?\b|\bfuentes?\b|\blibros?\b|\bglosario\b"),
]
# «Trigonometry_Toolkit», «Calculus_Function_Arsenal_(5)»: así nombra NotebookLM
# a sus presentaciones-resumen, que no dicen «resumen» en ningún lado
TITULO_NOTEBOOKLM = re.compile(r"^[A-Z][a-z]+(?:_[A-Z][a-z]+)+(?:_?\(\d+\))?$")

CARPETA_PROPIA = ("trabajo", "entrega")
CARPETA_NO = ("actividad", "tarea", "evaluacion", "examen", "informacion del curso",
              "syllabus", "silabo")


def normalizar(texto):
    """«EVALUACIÓN DIRIGIDA 1 (ED1)» -> «evaluacion dirigida 1 ed1»."""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return " ".join(p for p in re.split(r"[^a-z0-9]+", t) if p)


def _frase(palabra):
    return r"\b" + r"\s+".join(re.escape(p) for p in normalizar(palabra).split()) + r"\b"


class Clasificador:
    """Decide si un archivo es material de estudio. Sin IA: reglas que puedes leer."""

    def __init__(self, cfg=None):
        cfg = cfg or {}
        formatos = cfg.get("formatos_estudio") or FORMATOS_ESTUDIO
        self.formatos = {("." + f.lstrip(".")).lower() for f in formatos}
        self.nombre_no = [(c, re.compile(p)) for c, p in NOMBRE_NO]
        self.nombre_si = [(c, re.compile(p)) for c, p in NOMBRE_SI]
        # tus palabras de config.json mandan sobre las reglas de fábrica: si pones
        # "ejercicios" en incluir_palabras, tus listas de ejercicios vuelven a entrar
        extra_no = [_frase(w) for w in cfg.get("excluir_palabras", []) if normalizar(w)]
        extra_si = [_frase(w) for w in cfg.get("incluir_palabras", []) if normalizar(w)]
        self.tuyas_no = re.compile("|".join(extra_no)) if extra_no else None
        self.tuyas_si = re.compile("|".join(extra_si)) if extra_si else None
        self.carpeta_no = CARPETA_NO + tuple(
            normalizar(c) for c in cfg.get("excluir_carpetas", []) if normalizar(c)
        )

    def clasificar(self, ruta):
        """(es_material_de_estudio, motivo en palabras)."""
        ruta = Path(ruta)
        ext = ruta.suffix.lower()
        if ext not in self.formatos:
            return False, f"formato {ext or 'sin extensión'}"

        carpetas = [(normalizar(p), p) for p in ruta.parent.parts]
        for c, _ in carpetas:
            if c.startswith(CARPETA_PROPIA):
                return False, "trabajo tuyo"

        nombre = normalizar(ruta.stem)
        if self.tuyas_no and self.tuyas_no.search(nombre):
            return False, "palabra tuya (excluir_palabras)"
        if self.tuyas_si and self.tuyas_si.search(nombre):
            return True, "palabra tuya (incluir_palabras)"
        for categoria, patron in self.nombre_no:
            if patron.search(nombre):
                return False, categoria
        if EJERCICIOS.search(nombre) and not CON_TEORIA.search(nombre):
            return False, "lista de ejercicios"

        for categoria, patron in self.nombre_si:
            if patron.search(nombre):
                return True, categoria
        if TITULO_NOTEBOOKLM.match(ruta.stem):
            return True, "resumen (título tipo NotebookLM)"

        for c, original in carpetas:
            if c.startswith(self.carpeta_no):
                return False, f"está en «{original}»"

        return True, "sin pistas: se asume material"
