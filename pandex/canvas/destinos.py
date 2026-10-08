"""A qué carpeta va cada archivo de Canvas, y si ya lo tienes.

Estructura que se arma dentro de la carpeta de cada curso::

    <Curso>/
      Sem 3/                    semana del módulo (el formato es configurable)
        Teoría/ | Lab/          solo si el curso tiene teoría y laboratorio en Canvas
          Material de clase/    el subencabezado del módulo
            archivo.pdf
      Sílabo y anexo/           módulos sin número de semana (si se activó)

Las carpetas no están escritas a fuego: siempre se busca primero una que ya
exista con un nombre parecido (``"Sem 3"`` = ``"Semana 3"``, ``"Lab"`` =
``"Laboratorio"`` si así se configuró) y solo se crea si no hay ninguna.
"""

from .nombres import limpiar_nombre, normalizar

# --------------------------------------------------------------------------
# carpetas
# --------------------------------------------------------------------------


def buscar_subcarpeta(padre, nombre, alias=()):
    """La subcarpeta que ya existe con ese nombre (o un alias), comparando flexible."""
    if not padre.is_dir():
        return None
    objetivos = {normalizar(nombre)} | {normalizar(a) for a in alias}
    for hijo in padre.iterdir():
        if hijo.is_dir() and normalizar(hijo.name) in objetivos:
            return hijo
    return None


def resolver_subcarpeta(padre, nombre, alias=(), crear=True):
    """Usa la carpeta que ya exista (aunque se llame algo distinto); si no, la crea.

    Con ``crear=False`` solo calcula la ruta (para vistas previas).
    """
    existente = buscar_subcarpeta(padre, nombre, alias)
    if existente:
        return existente
    nueva = padre / nombre
    if crear:
        nueva.mkdir(parents=True, exist_ok=True)
    return nueva


def nombre_semana(n, formato="Sem {n}"):
    """``nombre_semana(3, "Semana {n:02d}")`` -> ``"Semana 03"``."""
    try:
        return formato.format(n=n)
    except (KeyError, IndexError, ValueError):
        return f"Sem {n}"


def alias_semana(n):
    return [f"Sem {n}", f"Semana {n}", f"Sem {n:02d}", f"Semana {n:02d}", f"Week {n}"]


def carpeta_de_seccion(seccion, secciones):
    """Traduce un subencabezado de Canvas a su carpeta según el mapa ``secciones``.

    El mapa va de una etiqueta a una carpeta (``"material de clase": "Material de
    clase"``) y la etiqueta vale como prefijo: también cubre ``"Material de clases"``.
    Si varias etiquetas sirven, gana la más larga (la más específica).
    """
    clave = normalizar(seccion)
    for etiqueta in sorted(secciones, key=lambda e: -len(normalizar(e))):
        if clave.startswith(normalizar(etiqueta)):
            return secciones[etiqueta]
    return None


def modo_de(regla):
    """``"semanas"`` (lo normal) o ``"lista"``: un módulo plano repartido por el calendario."""
    modo = regla.get("modo") or "semanas"
    return "lista" if modo in ("lista", "lab_comunicacion") else "semanas"


def carpeta_destino(carpeta, regla, item, semana, secciones, formato="Sem {n}", crear=True):
    """La carpeta donde va ``item`` dentro de la ``carpeta`` de su curso, o None.

    ``semana`` es la del módulo (o la del calendario, en modo ``"lista"``); None
    para módulos sin número de semana. Devuelve None si el subencabezado no se
    reconoce y la regla no permite crear carpetas de sección nuevas.
    """
    def sub(padre, nombre, alias=()):
        return resolver_subcarpeta(padre, nombre, alias, crear)

    def base():
        if semana is None:
            return sub(carpeta, limpiar_nombre(item.modulo))
        return sub(carpeta, nombre_semana(semana, formato), alias_semana(semana))

    if modo_de(regla) == "lista":
        raiz = sub(carpeta, regla["subcarpeta_raiz"]) if regla.get("subcarpeta_raiz") else carpeta
        return sub(raiz, nombre_semana(semana, formato), alias_semana(semana))

    fija = regla.get("subcarpeta_fija")  # "Teoría" / "Lab" cuando el curso tiene las dos mitades
    alias_fija = regla.get("alias_subcarpeta", [])

    if regla.get("crear_secciones"):
        # lo que arma el asistente: copia la organización de Canvas tal cual
        destino = base()
        if fija:
            destino = sub(destino, fija, alias_fija)
        if not (item.seccion or "").strip():
            return destino
        return sub(destino, carpeta_de_seccion(item.seccion, secciones) or limpiar_nombre(item.seccion))

    # modo clásico (configuraciones escritas a mano): solo las secciones del mapa
    seccion = item.seccion if item.seccion is not None else item.modulo
    nombre_seccion = carpeta_de_seccion(seccion, secciones)
    if not fija and not nombre_seccion:
        return None  # se descarta ANTES de crear nada: si no, quedan carpetas vacías
    destino = base()
    if not fija:
        return sub(destino, nombre_seccion)
    destino = sub(destino, fija, alias_fija)
    # dentro de la mitad se usa la carpeta de sección solo si ya la tienes
    if nombre_seccion:
        propia = buscar_subcarpeta(destino, nombre_seccion)
        if propia is not None:
            return propia
    return destino


def ruta_vetada(destino, prohibidas):
    """True si la ruta pasa por una carpeta de ``nunca_escribir``."""
    vetadas = {normalizar(p) for p in prohibidas}
    return any(normalizar(parte) in vetadas for parte in destino.parts)


# --------------------------------------------------------------------------
# teoría y laboratorio comparten carpeta
# --------------------------------------------------------------------------


def marcas_de(regla):
    """Carpetas que identifican una mitad del curso: Teoría, Lab, Material de Laboratorio…"""
    nombres = [regla.get("subcarpeta_fija"), regla.get("subcarpeta_raiz"),
               *regla.get("alias_subcarpeta", [])]
    return {normalizar(n) for n in nombres if n}


def mitad_de(ruta, carpeta, hermanas):
    """Qué regla (teoría o lab) es dueña de un archivo del curso; None si es común.

    Lo dice el camino: ``Sem 4\\Lab\\…`` es del lab y ``Sem 4\\Teoría\\…`` de teoría.
    Si una de las dos no tiene carpeta propia, es dueña de todo lo que no sea de
    la otra.
    """
    try:
        partes = {normalizar(p) for p in ruta.relative_to(carpeta).parts[:-1]}
    except ValueError:
        return None
    for regla in hermanas:
        if marcas_de(regla) & partes:
            return regla
    sin_marca = [r for r in hermanas if not marcas_de(r)]
    return sin_marca[0] if len(sin_marca) == 1 else None


# --------------------------------------------------------------------------
# ¿ya lo tienes?
# --------------------------------------------------------------------------


class IndiceCurso:
    """Todo lo que ya está en disco dentro de la carpeta de un curso.

    Se compara contra el curso entero (no solo la carpeta destino) porque es
    común tener el mismo archivo en otra semana, otra sección o renombrado a mano.
    Dos reglas para no saltar de más:

    - el nombre se compara **con extensión**: la misma clase en .pptx y en .pdf
      son dos archivos que quieres;
    - el tamaño solo cuenta **desde 4 KB**: los accesos .url pesan todos casi lo
      mismo y chocarían entre sí.
    """

    TAMANO_MINIMO = 4096

    def __init__(self, carpeta, excluir=(), tamano_minimo=None):
        self.por_nombre = {}   # nombre normalizado -> [(ruta, tamaño)]
        self.por_tamano = {}   # tamaño exacto -> ruta
        self.tamano_minimo = self.TAMANO_MINIMO if tamano_minimo is None else int(tamano_minimo)
        vetadas = {normalizar(x) for x in excluir}
        for ruta in carpeta.rglob("*"):
            if not ruta.is_file() or ruta.name.lower() == "desktop.ini":
                continue
            if any(normalizar(parte) in vetadas for parte in ruta.parts):
                continue
            self.agregar(ruta)

    def agregar(self, ruta, tamano=None):
        es_md = ruta.suffix.lower() == ".md"
        if tamano is None and not es_md:
            try:
                tamano = ruta.stat().st_size
            except OSError:
                tamano = None
        self.por_nombre.setdefault(normalizar(ruta.name), []).append((ruta, tamano))
        if es_md:
            # los .md que genera «Convertir a Markdown» no vienen de Canvas: su
            # peso podría coincidir con el de un PDF nuevo
            return
        if tamano and tamano >= self.tamano_minimo:
            self.por_tamano.setdefault(tamano, ruta)

    def buscar(self, nombre, tamano=None, por_tamano=True, ajena=None):
        """``(motivo, ruta)`` si ya lo tienes, o None.

        ``ajena(ruta)`` dice si esa ruta es de la otra mitad del curso (teoría vs.
        laboratorio). Ahí el nombre solo no basta: cada docente sube su propio
        «semana 9.pptx» y son materiales distintos. Cuenta si además pesa igual.
        """
        for previo, peso in self.por_nombre.get(normalizar(nombre), ()):
            if ajena is None or not ajena(previo):
                return "mismo nombre", previo
            if tamano and peso == tamano:
                return "mismo nombre y tamaño", previo
        if por_tamano and tamano and tamano >= self.tamano_minimo:
            previo = self.por_tamano.get(tamano)
            if previo is not None:
                return "mismo contenido (bytes idénticos)", previo
        return None
