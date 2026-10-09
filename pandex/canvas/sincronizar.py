"""Sincronizar Canvas: baja el material nuevo y lo ordena en tu carpeta.

Fases (cada una se cronometra y queda en el registro):

1. **sesión**        el navegador entra con tu sesión guardada y se cierra.
2. **módulos**       se leen los módulos de todos tus cursos a la vez.
3. **consultas**     nombre real y tamaño, solo de lo que el historial no conoce.
4. **revisar disco** para cada archivo: ¿ya lo tienes? ¿a qué carpeta va?
5. **descargas**     en paralelo a una carpeta temporal; se mueve a la carpeta
                     final de a uno y solo si el destino sigue libre.

Reglas que nunca se rompen:

- solo **crea** archivos: no borra, mueve, sobrescribe ni renombra nada tuyo;
- un archivo a medias nunca llega a tu carpeta (se verifica el tamaño);
- nunca escribe dentro de las carpetas de ``nunca_escribir``.
"""

import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .. import horas
from ..rutas import DATOS
from . import sesion
from .cliente import Canvas, CanvasError, SinConexion
from .destinos import (
    IndiceCurso,
    buscar_subcarpeta,
    carpeta_destino,
    mitad_de,
    modo_de,
    ruta_vetada,
)
from .estructura import Item, alias_curso, emparejar_cursos, items_de_modulos
from .historial import Historial
from .nombres import nombre_destino, normalizar, numero_de_semana

TEMPORAL = DATOS / "descargas"
HILOS_API = 6        # peticiones de lectura simultáneas a Canvas
HILOS_DESCARGA = 4   # descargas simultáneas


def esta_configurado(params):
    """True si ya hay carpeta destino y al menos un curso elegido."""
    return bool(params.get("destino")) and bool(params.get("cursos"))


def semana_de_hoy(calendario, hoy=None):
    """El número de semana del ciclo según el ``calendario`` del config, o None."""
    hoy = hoy or date.today()
    for tramo in calendario:
        inicio = datetime.strptime(tramo["inicio"], "%Y-%m-%d").date()
        fin = datetime.strptime(tramo["fin"], "%Y-%m-%d").date()
        if inicio <= hoy <= fin:
            return int(tramo["semana"])
    return None


@dataclass
class Candidato:
    """Un archivo de Canvas que corresponde a uno de tus cursos."""

    regla: dict
    curso: dict
    alias: str
    item: Item
    semana: int  # None: módulo sin número de semana

    @property
    def file_id(self):
        return self.item.file_id


@dataclass
class Descarga:
    candidato: Candidato
    nombre: str
    destino: Path
    tamano: int = None
    carpeta_curso: Path = None


def candidatos_de(parejas, modulos, semana_hoy=None, log=None):
    """Los archivos de los módulos que corresponden a cada curso configurado.

    ``parejas`` son ``(regla, curso)`` y ``modulos`` los módulos de cada pareja,
    en el mismo orden. Un archivo enlazado en varios módulos cuenta una vez.
    """
    vistos, salida = set(), []
    for (regla, curso), mods in zip(parejas, modulos):
        lista = modo_de(regla) == "lista"
        esperada = normalizar(regla.get("seccion_unica", ""))
        for item in items_de_modulos(mods):
            if item.file_id in vistos:
                continue
            if lista:
                seccion = item.seccion if item.seccion is not None else item.modulo
                if not normalizar(seccion).startswith(esperada):
                    continue
                if semana_hoy is None:
                    if log:
                        log("modo «lista» sin calendario: no sé en qué semana va", "warning")
                    continue
                semana = semana_hoy
            else:
                semana = numero_de_semana(item.modulo)
                if semana is None and not regla.get("otros_modulos"):
                    continue
            vistos.add(item.file_id)
            salida.append(Candidato(regla, curso, alias_curso(regla, curso), item, semana))
    return salida


def metadatos(canvas, candidatos, historial=None):
    """``{file_id: {"nombre", "tamano"}}`` de esos archivos, preguntando lo mínimo.

    Primero intenta el listado completo de cada curso (una llamada); si Canvas lo
    niega, pregunta archivo por archivo, varios a la vez.
    """
    if not candidatos:
        return {}
    metas = {}
    cursos = {c.curso["id"] for c in candidatos}
    probar = [cid for cid in cursos if historial is None or not historial.listado_prohibido(cid)]
    with ThreadPoolExecutor(HILOS_API) as ex:
        for cid, listado in zip(probar, ex.map(canvas.archivos_del_curso, probar)):
            if listado is None:
                if historial is not None:
                    historial.prohibir_listado(cid)
            else:
                metas.update(listado)
        faltan = [c for c in candidatos if c.file_id not in metas]
        futuros = {ex.submit(canvas.archivo, c.curso["id"], c.file_id): c for c in faltan}
        for futuro in as_completed(futuros):
            metas[futuros[futuro].file_id] = futuro.result()
    return metas


class Sincronizacion:
    """Una corrida de la tarea. ``ejecutar()`` devuelve el resultado para Pandex."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.p = ctx.params
        self.entrada = ctx.entrada or {}
        self.reglas = self.p.get("cursos", [])
        self.secciones = self.p.get("secciones", {})
        self.formato = self.p.get("formato_semana", "Sem {n}")
        self.dedupe_por_tamano = bool(self.p.get("dedupe_por_tamano", True))
        self._indices = {}
        self._carpetas = {}
        self._fases = {}
        self._res = {"nuevos": [], "fallidos": [], "bloqueados": [], "sin_seccion": [], "ya": 0, "omitidos": 0,
                     "coincidencias": [], "cursos_error": [], "sin_conexion": False}

    # ------------------------------------------------------------------ inicio

    def ejecutar(self):
        inicio = time.monotonic()
        ctx, p = self.ctx, self.p
        base_url = p.get("canvas_url", "").rstrip("/")
        self.raiz = Path(p.get("destino", ""))

        if not esta_configurado(p) or not base_url:
            return {"ok": False, "resumen": "Falta configurar Canvas: clic derecho → Configurar Canvas.",
                    "detalle": ["sin canvas_url, destino o cursos en config.json"]}
        if not self.raiz.is_dir():
            return {"ok": False, "resumen": "No encuentro tu carpeta de cursos.",
                    "detalle": [f"no existe: {self.raiz}"]}

        # el calendario es opcional: solo lo necesitan los cursos en modo "lista"
        calendario = p.get("calendario") or []
        self.semana_hoy = semana_de_hoy(calendario) if calendario else None
        if calendario and self.semana_hoy is None:
            return {"ok": False, "resumen": "Hoy no cae en ninguna semana del ciclo, no toco nada.",
                    "detalle": [f"fecha de hoy: {date.today().isoformat()}"]}
        if self.semana_hoy:
            ctx.log(f"semana en curso: {self.semana_hoy}")

        TEMPORAL.mkdir(parents=True, exist_ok=True)
        _limpiar_temporales()
        historial = Historial()
        parejas = []

        # ---- 1. entrar (el navegador se cierra enseguida)
        t = time.monotonic()
        try:
            cookies, ua = sesion.iniciar_sesion(
                ctx, base_url, p.get("usar_chrome_instalado", True),
                p.get("espera_login_segundos", 300), p.get("headless", True),
            )
        except CanvasError as exc:
            return {"ok": False, "resumen": str(exc), "detalle": [str(exc)]}
        except sesion.error_navegador() as exc:
            primera = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
            return {"ok": False, "resumen": sesion.mensaje_de_error(exc), "detalle": [primera]}
        self._fases["sesión"] = time.monotonic() - t
        canvas = Canvas(base_url, cookies, ua)

        try:
            # ---- 2. cursos y módulos (todos a la vez)
            t = time.monotonic()
            parejas = emparejar_cursos(canvas.cursos(), self.reglas)
            if not parejas:
                return {"ok": False, "resumen": "No reconocí ninguno de tus cursos en Canvas.",
                        "detalle": ["¿cambió el ciclo? Vuelve a correr Configurar Canvas"]}
            candidatos = self._candidatos(canvas, parejas)
            candidatos = self._aplicar_descarga_inicial(candidatos, historial)
            self._fases["módulos"] = time.monotonic() - t

            # ---- 3. qué no conocemos todavía, y sus datos (en paralelo)
            t = time.monotonic()
            desconocidos = [c for c in candidatos if historial.conocido(c.file_id) is None]
            self._res["ya"] += len(candidatos) - len(desconocidos)
            metas = metadatos(canvas, desconocidos, historial)
            self._fases["consultas"] = time.monotonic() - t

            # ---- 4. decidir: ¿ya lo tienes? ¿dónde va? (en orden, contra tu disco)
            t = time.monotonic()
            descargas = self._decidir(desconocidos, metas, historial)
            self._fases["revisar disco"] = time.monotonic() - t

            # ---- 5. bajar lo nuevo (en paralelo) y moverlo uno por uno
            t = time.monotonic()
            self._descargar(canvas, descargas, historial)
            self._fases["descargas"] = time.monotonic() - t
        except SinConexion:
            self._res["sin_conexion"] = True
        except CanvasError as exc:
            self._res["cursos_error"].append(("Canvas", str(exc)))
        finally:
            historial.guardar()

        return self._resultado(len(parejas), time.monotonic() - inicio)

    # ------------------------------------------------------------------ fase 2

    def _candidatos(self, canvas, parejas):
        """Los archivos de los módulos que corresponden a cada curso configurado."""
        with ThreadPoolExecutor(HILOS_API) as ex:
            futuros = [ex.submit(canvas.modulos, curso["id"]) for _, curso in parejas]
            modulos = []
            for (regla, curso), futuro in zip(parejas, futuros):
                try:
                    modulos.append(futuro.result())
                except SinConexion:
                    raise
                except CanvasError as exc:
                    self._res["cursos_error"].append(
                        (alias_curso(regla, curso), f"no pude leer los módulos ({exc})"))
                    modulos.append([])

        return candidatos_de(parejas, modulos, self.semana_hoy, self.ctx.log)

    def _aplicar_descarga_inicial(self, candidatos, historial):
        """Lo que elegiste no bajar en la configuración inicial se anota y se salta."""
        inicial = self.entrada.get("inicial")
        desde = int(self.entrada.get("desde_semana") or 0)
        quedan = []
        for c in candidatos:
            if historial.omitido(c.file_id):
                self._res["omitidos"] += 1
                continue
            omitir = (inicial == "nada" or (inicial == "desde" and c.semana is not None
                                             and c.semana < desde))
            if omitir and historial.conocido(c.file_id) is None:
                historial.omitir(c.file_id)
                self._res["omitidos"] += 1
                continue
            quedan.append(c)
        return quedan

    # ------------------------------------------------------------------ fase 4

    def _carpeta_curso(self, regla):
        nombre = regla["carpeta"]
        if nombre not in self._carpetas:
            carpeta = buscar_subcarpeta(self.raiz, nombre)
            if carpeta is None:
                carpeta = self.raiz / nombre
                carpeta.mkdir(parents=True, exist_ok=True)
                self.ctx.log(f"creé la carpeta de curso {carpeta}")
            self._carpetas[nombre] = carpeta
        return self._carpetas[nombre]

    def _indice(self, carpeta, prohibidas):
        """Teoría y lab de un curso comparten carpeta: se indexa una vez por corrida."""
        clave = (str(carpeta).casefold(), tuple(sorted(normalizar(x) for x in prohibidas)))
        if clave not in self._indices:
            self._indices[clave] = IndiceCurso(carpeta, excluir=prohibidas)
        return self._indices[clave]

    def _ajena(self, regla, carpeta):
        """Reconoce lo que en disco es de la otra mitad del curso (None si no hay dos)."""
        hermanas = [r for r in self.reglas if r.get("carpeta") == regla.get("carpeta")]
        if len(hermanas) < 2:
            return None

        def ajena(ruta):
            duena = mitad_de(ruta, carpeta, hermanas)
            return duena is not None and duena is not regla

        return ajena

    def _decidir(self, desconocidos, metas, historial):
        descargas = []
        for c in desconocidos:
            regla = c.regla
            prohibidas = regla.get("nunca_escribir", [])
            carpeta = self._carpeta_curso(regla)
            indice = self._indice(carpeta, prohibidas)
            meta = metas.get(c.file_id) or {}
            nombre = nombre_destino(c.item.titulo, meta.get("nombre"))

            previo = indice.buscar(nombre, meta.get("tamano"), self.dedupe_por_tamano,
                                   self._ajena(regla, carpeta))
            if previo:
                motivo, ruta = previo
                self._res["ya"] += 1
                if ruta.exists():  # si no, es uno que esta misma corrida va a bajar
                    historial.anotar(c.file_id, ruta, meta.get("tamano"))
                    self._res["coincidencias"].append((c, nombre, motivo, ruta))
                continue

            destino = carpeta_destino(carpeta, regla, c.item, c.semana, self.secciones, self.formato)
            if destino is None:
                self._res["sin_seccion"].append((c, nombre))
                continue
            if ruta_vetada(destino, prohibidas):
                self.ctx.log(f"ruta protegida, no escribo: {destino}", "warning")
                continue

            # se reserva ya en el índice: si otro ítem de esta corrida trae el mismo
            # archivo (p. ej. teoría y lab), no se baja dos veces
            indice.agregar(destino / nombre, meta.get("tamano"))
            descargas.append(Descarga(c, nombre, destino, meta.get("tamano"), carpeta))
        return descargas

    # ------------------------------------------------------------------ fase 5

    def _descargar(self, canvas, descargas, historial):
        # lo que el docente programó para más adelante no se intenta: se reintenta solo
        # en la próxima sincronización (no queda en el historial)
        for d in descargas:
            if d.candidato.item.bloqueado:
                self._res["bloqueados"].append((d, d.candidato.item.abre))
        descargas = [d for d in descargas if not d.candidato.item.bloqueado]
        if not descargas:
            return
        self.ctx.decir(f"Encontré {len(descargas)} archivo(s) nuevo(s). Bajando…")

        def bajar(d):
            tmp = TEMPORAL / f"{d.candidato.file_id}.part"
            es_html = d.nombre.lower().endswith((".html", ".htm"))
            try:
                escritos = canvas.descargar(d.candidato.curso["id"], d.candidato.file_id,
                                            tmp, espera_html=es_html)
                if d.tamano and escritos != d.tamano:
                    raise CanvasError(f"llegó incompleto: {escritos} de {d.tamano} bytes")
                return tmp, escritos, None
            except (CanvasError, OSError) as exc:
                tmp.unlink(missing_ok=True)
                return tmp, 0, exc

        with ThreadPoolExecutor(min(HILOS_DESCARGA, len(descargas))) as ex:
            futuros = {ex.submit(bajar, d): d for d in descargas}
            for hechos, futuro in enumerate(as_completed(futuros), start=1):
                d = futuros[futuro]
                self.ctx.progreso(hechos, len(descargas))
                tmp, escritos, error = futuro.result()
                if error is not None:
                    if getattr(error, "estado", None) == 403:
                        # Canvas lo muestra pero no deja bajarlo todavía: no es una falla
                        self._res["bloqueados"].append((d, None))
                        self.ctx.log(f"«{d.nombre}» aún no está disponible (403)")
                        continue
                    if isinstance(error, SinConexion):
                        self._res["sin_conexion"] = True
                    self._res["fallidos"].append((d, str(error)))
                    self.ctx.log(f"falló la descarga de «{d.nombre}»: {error}", "error")
                    continue
                self._mover(d, tmp, escritos, historial)

    def _mover(self, d, tmp, escritos, historial):
        """Un solo hilo mueve a la carpeta final, y solo si el destino sigue libre."""
        final = d.destino / d.nombre
        try:
            d.destino.mkdir(parents=True, exist_ok=True)
            if final.exists():
                tmp.unlink(missing_ok=True)
                self._res["ya"] += 1
                self.ctx.log(f"«{d.nombre}» apareció mientras bajaba, no lo piso", "warning")
                return
            shutil.move(str(tmp), str(final))
        except OSError as exc:
            self._res["fallidos"].append((d, f"bajé el archivo pero no pude moverlo ({exc})"))
            self.ctx.log(f"no pude mover «{d.nombre}»: {exc}", "error")
            return
        historial.anotar(d.candidato.file_id, final, escritos)
        self._res["nuevos"].append((d, final))
        self.ctx.log(f"guardado {final} ({escritos} bytes)")

    # ------------------------------------------------------------------ resultado

    def _resultado(self, n_cursos, segundos):
        r = self._res
        # se reporta lo que de verdad quedó en disco
        nuevos = [(d, f) for d, f in r["nuevos"] if f.exists()]
        for d, f in r["nuevos"]:
            if not f.exists():
                r["fallidos"].append((d, "se guardó pero ya no aparece en disco"))
        dur = _duracion(segundos)
        revisados = r["ya"] + len(nuevos)
        ok = not (r["fallidos"] or r["sin_conexion"] or r["cursos_error"])
        marca = "✓ " if ok else ""  # si algo falló, Pandex ya antepone ⚠

        if r["sin_conexion"]:
            resumen = "Se cortó la conexión con Canvas"
            resumen += f" · alcancé a guardar {len(nuevos)}." if nuevos else "."
        elif r["cursos_error"] and not revisados:
            resumen = f"No pude leer Canvas: {r['cursos_error'][0][1]}"
        elif nuevos:
            por_curso = {}
            for d, _ in nuevos:
                por_curso[d.candidato.alias] = por_curso.get(d.candidato.alias, 0) + 1
            cursos = ", ".join(f"{a} {n}" for a, n in por_curso.items())
            resumen = f"{marca}{len(nuevos)} nuevo(s): {cursos} · {dur}"
        elif ok:
            resumen = f"✓ Todo al día · {n_cursos} cursos, {revisados} archivos · {dur}"
        else:
            resumen = f"Nada nuevo · {n_cursos} cursos, {revisados} archivos · {dur}"
        if r["fallidos"] and not r["sin_conexion"]:
            n = len(r["fallidos"])
            resumen += f" · {n} no se pudo bajar" if n == 1 else f" · {n} no se pudieron bajar"
        if r["bloqueados"] and not r["sin_conexion"]:
            resumen += f" · {len(r['bloqueados'])} aún sin abrir en Canvas"
        if r["cursos_error"] and revisados and not r["sin_conexion"]:
            resumen += f" · {len(r['cursos_error'])} curso(s) sin leer"

        hay_algo = nuevos or r["fallidos"] or r["sin_seccion"] or r["cursos_error"]
        carpetas = {f.parent for _, f in nuevos}
        return {
            "ok": ok,
            "resumen": resumen,
            "detalle": self._detalle(nuevos),
            # la ventana de resumen solo aparece si hay algo que contar
            "informe": self._informe(nuevos, n_cursos, dur) if hay_algo else None,
            "carpeta": str(carpetas.pop() if len(carpetas) == 1 else self.raiz),
        }

    def _informe(self, nuevos, n_cursos, dur):
        r = self._res
        l = [f"SINCRONIZAR CANVAS · {horas.fecha_hora(datetime.now())} · {dur}", ""]
        if nuevos:
            l.append(f"✓ {len(nuevos)} archivo(s) nuevo(s)")
            por_curso = {}
            for d, final in nuevos:
                por_curso.setdefault(d.candidato.alias, []).append((d, final))
            for alias, lista in por_curso.items():
                l.append(f"  {alias}")
                for d, final in sorted(lista, key=lambda x: str(x[1]).casefold()):
                    try:
                        donde = " · ".join(final.parent.relative_to(d.carpeta_curso).parts)
                    except ValueError:
                        donde = final.parent.name
                    l.append(f"    {donde:<32} {final.name}")
            l.append("")
        if r["fallidos"]:
            l.append(f"✗ {len(r['fallidos'])} no se pudo bajar (se reintenta la próxima vez)")
            l += [f"    {d.candidato.alias} · {d.nombre} — {m}" for d, m in r["fallidos"]]
            l.append("")
        if r["bloqueados"]:
            l.append(f"🔒 {len(r['bloqueados'])} aún sin abrir en Canvas (los bajo cuando se abran)")
            l += [f"    {d.candidato.alias} · {d.nombre}" + (f" — se abre el {_fecha(abre)}" if abre else "")
                  for d, abre in r["bloqueados"]]
            l.append("")
        if r["sin_seccion"]:
            l.append(f"? {len(r['sin_seccion'])} sin sección reconocida (no se bajaron)")
            l += [f"    {c.alias} · {n} — sección «{c.item.seccion or c.item.modulo}»"
                  for c, n in r["sin_seccion"]]
            l.append("")
        l += [f"✗ {alias}: {motivo}" for alias, motivo in r["cursos_error"]]
        pie = f"Ya tenías {r['ya']} · {n_cursos} cursos revisados"
        if r["omitidos"]:
            pie += f" · {r['omitidos']} omitidos por tu elección inicial"
        l.append(pie)
        return "\n".join(l)

    def _detalle(self, nuevos):
        """Para el registro: solo lo que cambió, no los cientos de archivos conocidos."""
        r = self._res
        l = ["fases: " + " · ".join(f"{k} {v:.1f}s" for k, v in self._fases.items()),
             f"ya estaban: {r['ya']} · nuevos: {len(nuevos)} · fallidos: {len(r['fallidos'])}"
             f" · omitidos: {r['omitidos']}"]
        l += [f"nuevo · {d.candidato.alias} · {f}" for d, f in nuevos]
        l += [f"falló · {d.candidato.alias} · {d.nombre} — {m}" for d, m in r["fallidos"]]
        l += [f"aún sin abrir · {d.candidato.alias} · {d.nombre}" + (f" (se abre {abre})" if abre else "")
              for d, abre in r["bloqueados"]]
        l += [f"sin sección · {c.alias} · {n} («{c.item.seccion or c.item.modulo}»)"
              for c, n in r["sin_seccion"]]
        l += [f"ya lo tenías ({m}) · {c.alias} · {n} → {ruta}" for c, n, m, ruta in r["coincidencias"]]
        l += [f"error · {a} · {m}" for a, m in r["cursos_error"]]
        return l


def _fecha(iso):
    """``2026-10-12T05:00:00Z`` → ``12/10 12:00 a. m.`` en tu hora local."""
    try:
        return horas.fecha_hora(datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone())
    except (ValueError, AttributeError):
        return iso


def _duracion(segundos):
    s = round(segundos)
    return f"{s} s" if s < 60 else f"{s // 60} min {s % 60:02d} s"


def _limpiar_temporales(horas=24):
    """Borra restos de descargas cortadas, solo en la carpeta temporal propia."""
    limite = time.time() - horas * 3600
    for f in TEMPORAL.glob("*"):
        try:
            if f.is_file() and f.stat().st_mtime < limite:
                f.unlink()
        except OSError:
            pass
