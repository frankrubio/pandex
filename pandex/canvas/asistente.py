"""Asistente de configuración inicial de «Sincronizar Canvas».

Se abre solo la primera vez que arrancas Pandex, o desde el menú
«Configurar Canvas…». Pasos:

1. **Bienvenida**        la dirección de tu Canvas
2. **Conectar**          inicias sesión en un navegador; Pandex lee tus cursos
3. **Cursos**            cuáles sincronizar y el nombre de la carpeta de cada uno
4. **Carpeta**           una carpeta nueva, o una donde ya tenías tus cursos
5. **Tu carpeta**        (si ya tenías) qué carpeta es de qué curso
6. **Reordenar**         (opcional) vista previa de lo que se moverá
7. **Descarga inicial**  todo, desde una semana, o nada
8. **Listo**             resumen

Nada se escribe en disco ni en config.json hasta pulsar «Terminar».
"""

import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from PyQt6.QtCore import Qt, QThread, QTime, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QProgressDialog,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from ..log import get_logger
from ..rutas import DATOS
from ..ui import dibujo, tema
from . import adoptar, sesion
from .cliente import Canvas, CanvasError
from .destinos import alias_semana, nombre_semana, resolver_subcarpeta
from .estructura import agrupar, emparejar_cursos, nombre_corto, resumir
from .historial import Historial
from .nombres import limpiar_nombre
from .sincronizar import candidatos_de, metadatos

log = get_logger("pandex.canvas.asistente")

URL_POR_DEFECTO = "https://utec.instructure.com"
(BIENVENIDA, CONECTAR, CURSOS, CARPETA, ADOPTAR, REORDENAR, DESCARGA, LISTO) = range(8)


# --------------------------------------------------------------------------
# lo que se va decidiendo
# --------------------------------------------------------------------------


@dataclass
class Grupo:
    """Un curso a sincronizar: uno de Canvas, o la pareja teoría + laboratorio."""

    resumenes: list
    carpeta: str
    elegido: bool = True

    @property
    def nombre(self):
        return nombre_corto(self.resumenes[0].nombre)

    @property
    def pareja(self):
        return len(self.resumenes) > 1

    def alias_de(self, resumen):
        return self.nombre + (" (lab)" if self.pareja and resumen.es_lab else "")


class Estado:
    def __init__(self, params):
        self.params = params
        self.url = params.get("canvas_url") or URL_POR_DEFECTO
        self.canvas = None
        self.cursos = []
        self.modulos = {}       # id de curso -> módulos
        self.resumenes = []
        self.grupos = []
        self.modo = "nueva"     # "nueva" o "existente"
        self.raiz = None
        self.convenciones = adoptar.Convenciones()
        self.plan = None
        self.mover = False
        self.inicial = "todo"
        self.desde = 1
        self.horario = None

    @property
    def elegidos(self):
        return [g for g in self.grupos if g.elegido]

    def reglas(self):
        """Los cursos tal como quedan en config.json."""
        conv = self.convenciones
        salida = []
        for g in self.elegidos:
            for r in g.resumenes:
                regla = {"canvas_id": r.curso["id"], "nombre_canvas": r.nombre,
                         "carpeta": g.carpeta, "alias": g.alias_de(r),
                         "crear_secciones": True, "otros_modulos": True}
                if g.pareja and r.es_lab:
                    regla.update(tipo="laboratorio", subcarpeta_fija=conv.lab,
                                 alias_subcarpeta=list(conv.alias_lab))
                elif g.pareja:
                    regla.update(tipo="teoria", subcarpeta_fija=conv.teoria,
                                 alias_subcarpeta=list(conv.alias_teoria))
                salida.append(regla)
        return salida

    def secciones(self):
        subencabezados = Counter()
        for g in self.elegidos:
            for r in g.resumenes:
                subencabezados.update(r.secciones)
        existentes = self.convenciones.secciones if self.modo == "existente" else ()
        return adoptar.mapa_secciones(subencabezados, existentes)

    def archivos_elegidos(self):
        return sum(r.archivos for g in self.elegidos for r in g.resumenes)

    def ultima_semana(self):
        semanas = [n for g in self.elegidos for r in g.resumenes for n in r.semanas]
        return max(semanas) if semanas else 1


# --------------------------------------------------------------------------
# trabajo en segundo plano (la ventana nunca se congela)
# --------------------------------------------------------------------------


_EN_CURSO = set()  # hilos vivos: si cierras el asistente a mitad, terminan solos sin tumbar la app


class _Trabajo(QThread):
    aviso = pyqtSignal(str)
    listo = pyqtSignal(object)
    fallo = pyqtSignal(str)

    def __init__(self, funcion):
        super().__init__()
        self._funcion = funcion
        # Qt aborta la app si se destruye un QThread que sigue corriendo (p. ej. el
        # navegador esperando tu login cuando cancelas): se guarda hasta que termine
        _EN_CURSO.add(self)
        self.finished.connect(lambda: _EN_CURSO.discard(self))

    def run(self):
        try:
            self.listo.emit(self._funcion(self.aviso.emit))
        except CanvasError as exc:
            self.fallo.emit(str(exc))
        except PlaywrightError as exc:
            log.warning("navegador: %s", exc)
            self.fallo.emit(sesion.mensaje_de_error(exc))
        except Exception as exc:
            log.exception("el asistente falló en segundo plano")
            self.fallo.emit(f"{exc.__class__.__name__}: {exc}")


class _AvisosDeSesion:
    """Lo que ``sesion.iniciar_sesion`` espera de un ctx: log() y decir()."""

    def __init__(self, avisar):
        self._avisar = avisar

    def log(self, mensaje, nivel="info"):
        getattr(log, nivel, log.info)(mensaje)

    def decir(self, texto):
        self._avisar(texto)


def _conectar(estado, avisar):
    cookies, ua = sesion.iniciar_sesion(
        _AvisosDeSesion(avisar), estado.url, estado.params.get("usar_chrome_instalado", True),
        estado.params.get("espera_login_segundos", 300), True,
    )
    canvas = Canvas(estado.url, cookies, ua)
    avisar("Leyendo tus cursos…")
    cursos = canvas.cursos()

    def modulos(curso):
        try:
            return canvas.modulos(curso["id"])
        except CanvasError:
            return []

    avisar(f"Revisando cómo están organizados tus {len(cursos)} cursos…")
    with ThreadPoolExecutor(6) as ex:
        todos = list(ex.map(modulos, cursos))
    return canvas, cursos, {c["id"]: m for c, m in zip(cursos, todos)}


def _carpeta_sugerida():
    """El OneDrive institucional si lo hay (se respalda solo); si no, Documentos."""
    casa = Path(os.environ.get("USERPROFILE") or Path.home())
    try:
        onedrive = sorted(d for d in casa.iterdir() if d.name.startswith("OneDrive - ") and d.is_dir())
    except OSError:
        onedrive = []
    return onedrive[0] if onedrive else casa / "Documents"


def _texto(html):
    etiqueta = QLabel(html)
    etiqueta.setWordWrap(True)
    etiqueta.setTextFormat(Qt.TextFormat.RichText)
    return etiqueta


def _selector_de_carpeta(pagina, campo, titulo):
    """Un campo de ruta con su botón «Elegir…». Devuelve ``(fila, botón)``."""
    boton = QPushButton("Elegir…")
    boton.clicked.connect(lambda: campo.setText(
        QFileDialog.getExistingDirectory(pagina, titulo, campo.text()) or campo.text()))
    fila = QHBoxLayout()
    fila.addWidget(campo, 1)
    fila.addWidget(boton)
    return fila, boton


# --------------------------------------------------------------------------
# páginas
# --------------------------------------------------------------------------


class PaginaBienvenida(QWizardPage):
    def __init__(self, estado):
        super().__init__()
        self.estado = estado
        self.setTitle("Conectemos tu Canvas")
        self.url = QLineEdit(estado.url)
        self.url.setPlaceholderText("https://tu-universidad.instructure.com")

        caja = QVBoxLayout(self)
        caja.addWidget(_texto(
            "Voy a revisar cómo están organizados tus cursos en Canvas, armar una carpeta "
            "para ellos y bajar el material: después, cada vez que me lo pidas, solo lo nuevo."
            "<br><br><b>Tu contraseña nunca se guarda.</b> Inicias sesión tú, en una ventana "
            "del navegador; yo solo uso esa sesión. Nada se escribe hasta el último paso."))
        caja.addSpacing(8)
        caja.addWidget(QLabel("Dirección de tu Canvas:"))
        caja.addWidget(self.url)

        if estado.params.get("cursos"):
            caja.addSpacing(8)
            caja.addWidget(_texto(
                f"<span style='color:{tema.hex_('aviso')}'>Ya tienes Canvas configurado. Si sigues, tu lista "
                "de cursos se reemplaza (la actual queda guardada en una copia).</span>"))
        if adoptar.ultimo_diario():
            deshacer = QPushButton("Deshacer el último reordenamiento de carpetas")
            deshacer.clicked.connect(self._deshacer)
            caja.addSpacing(8)
            caja.addWidget(deshacer)
        caja.addStretch()

    def _deshacer(self):
        r = QMessageBox.question(self, "Deshacer", "¿Devuelvo a su lugar los archivos que moví "
                                 "la última vez que reordené tu carpeta?")
        if r == QMessageBox.StandardButton.Yes:
            devueltos, saltados = adoptar.deshacer()
            QMessageBox.information(self, "Deshacer", f"Devolví {devueltos} archivo(s)."
                                    + (f" {saltados} ya no estaban donde los dejé." if saltados else ""))

    def validatePage(self):
        url = self.url.text().strip().rstrip("/")
        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url
        if "." not in url:
            QMessageBox.warning(self, "Dirección", "Escribe la dirección de tu Canvas, por ejemplo "
                                "https://tu-universidad.instructure.com")
            return False
        if url != self.estado.url:
            self.estado.canvas = None  # otra institución: hay que volver a conectar
        self.estado.url = url
        return True


class PaginaConectar(QWizardPage):
    def __init__(self, estado):
        super().__init__()
        self.estado = estado
        self._trabajo = None
        self.setTitle("Iniciar sesión")
        self.setSubTitle("Si es la primera vez, se abre tu navegador: entra con tu cuenta de "
                         "la universidad y la ventana se cerrará sola.")
        self.mensaje = _texto("")
        self.barra = QProgressBar()
        self.barra.setRange(0, 0)
        self.reintentar = QPushButton("Reintentar")
        self.reintentar.clicked.connect(self._empezar)
        caja = QVBoxLayout(self)
        caja.addWidget(self.mensaje)
        caja.addWidget(self.barra)
        caja.addWidget(self.reintentar, 0, Qt.AlignmentFlag.AlignLeft)
        caja.addStretch()

    def initializePage(self):
        if self.estado.canvas is None:
            self._empezar()

    def isComplete(self):
        return self.estado.canvas is not None

    def _empezar(self):
        if self._trabajo is not None and self._trabajo.isRunning():
            return
        self.reintentar.hide()
        self.barra.show()
        self.mensaje.setText("Abriendo el navegador…")
        self._trabajo = _Trabajo(lambda avisar: _conectar(self.estado, avisar))
        self._trabajo.aviso.connect(self.mensaje.setText)
        self._trabajo.listo.connect(self._listo)
        self._trabajo.fallo.connect(self._fallo)
        self._trabajo.start()

    def _listo(self, resultado):
        canvas, cursos, modulos = resultado
        self.estado.canvas, self.estado.cursos, self.estado.modulos = canvas, cursos, modulos
        self.estado.resumenes = [resumir(c, modulos.get(c["id"], [])) for c in cursos]
        self.estado.grupos = []
        self.barra.hide()
        self.mensaje.setText(f"Listo: encontré {len(cursos)} curso(s) activos.")
        self.completeChanged.emit()
        self.wizard().next()

    def _fallo(self, mensaje):
        self.barra.hide()
        self.reintentar.show()
        self.mensaje.setText(f"<span style='color:{tema.hex_('error')}'>{mensaje}</span>")


class PaginaCursos(QWizardPage):
    def __init__(self, estado):
        super().__init__()
        self.estado = estado
        self.setTitle("Tus cursos")
        self.setSubTitle("Marca los que quieres sincronizar. Puedes cambiar el nombre de su carpeta.")
        self.tabla = QTableWidget(0, 2)
        self.tabla.setHorizontalHeaderLabels(["Carpeta", "En Canvas"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla.verticalHeader().hide()
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        caja = QVBoxLayout(self)
        caja.addWidget(self.tabla)
        caja.addWidget(_texto("<small>Los cursos que tienen teoría y laboratorio en Canvas "
                              "comparten una carpeta, con «Teoría» y «Lab» dentro de cada semana.</small>"))

    def initializePage(self):
        if not self.estado.grupos:
            usados = set()
            for grupo in agrupar(self.estado.resumenes):
                carpeta = nombre = nombre_corto(grupo[0].nombre)
                n = 2
                while carpeta.casefold() in usados:
                    carpeta, n = f"{nombre} ({n})", n + 1
                usados.add(carpeta.casefold())
                # se proponen los que se organizan por semanas: suelen ser las clases
                elegido = any(r.semanas for r in grupo)
                self.estado.grupos.append(Grupo(grupo, carpeta, elegido))
        self.tabla.setRowCount(len(self.estado.grupos))
        for fila, g in enumerate(self.estado.grupos):
            nombres = "\n".join(r.nombre for r in g.resumenes)  # el nombre completo, al pasar el mouse
            carpeta = QTableWidgetItem(g.carpeta)
            carpeta.setFlags(carpeta.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEditable)
            carpeta.setCheckState(Qt.CheckState.Checked if g.elegido else Qt.CheckState.Unchecked)
            carpeta.setToolTip(nombres)
            if g.pareja:
                detalle = " · ".join(f"{'laboratorio' if r.es_lab else 'teoría'}: {r.describir()}"
                                     for r in g.resumenes)
            else:
                detalle = g.resumenes[0].describir()
            canvas = QTableWidgetItem(detalle)
            canvas.setFlags(Qt.ItemFlag.ItemIsEnabled)
            canvas.setToolTip(nombres)
            self.tabla.setItem(fila, 0, carpeta)
            self.tabla.setItem(fila, 1, canvas)
        self.tabla.resizeColumnToContents(0)
        self.tabla.setColumnWidth(0, min(self.tabla.columnWidth(0) + 24, 320))

    def validatePage(self):
        usados = set()
        for fila, g in enumerate(self.estado.grupos):
            item = self.tabla.item(fila, 0)
            g.elegido = item.checkState() == Qt.CheckState.Checked
            g.carpeta = limpiar_nombre(item.text().strip() or g.nombre)
            if g.elegido and g.carpeta.casefold() in usados:
                QMessageBox.warning(self, "Carpetas", f"Dos cursos usan la carpeta «{g.carpeta}».")
                return False
            usados.add(g.carpeta.casefold())
        if not self.estado.elegidos:
            QMessageBox.warning(self, "Cursos", "Marca al menos un curso.")
            return False
        return True


class PaginaCarpeta(QWizardPage):
    def __init__(self, estado):
        super().__init__()
        self.estado = estado
        self.setTitle("¿Dónde guardo tus cursos?")
        self.nueva = QRadioButton("En una carpeta nueva")
        self.existente = QRadioButton("En una carpeta donde ya tengo mis cursos (la ordeno sin borrar nada)")
        self.nueva.setChecked(True)
        grupo = QButtonGroup(self)
        grupo.addButton(self.nueva)
        grupo.addButton(self.existente)

        self.padre = QLineEdit(str(_carpeta_sugerida()))
        self.nombre = QLineEdit("Cursos Canvas")
        self.ruta_existente = QLineEdit()

        fila_padre, elegir_padre = _selector_de_carpeta(self, self.padre, "Dónde crear la carpeta")
        fila_existente, elegir_existente = _selector_de_carpeta(self, self.ruta_existente,
                                                                "Tu carpeta de cursos")
        caja = QVBoxLayout(self)
        caja.addWidget(self.nueva)
        caja.addWidget(QLabel("    Dentro de:"))
        caja.addLayout(fila_padre)
        caja.addWidget(QLabel("    Con el nombre:"))
        caja.addWidget(self.nombre)
        caja.addSpacing(10)
        caja.addWidget(self.existente)
        caja.addLayout(fila_existente)
        caja.addWidget(_texto("<small>Consejo: si tu universidad te da OneDrive, ponla ahí y "
                              "tendrás tus cursos respaldados y en el celular.</small>"))
        caja.addStretch()
        # cada opción habilita solo sus propios campos
        for w in (self.padre, elegir_padre, self.nombre):
            self.nueva.toggled.connect(w.setEnabled)
        for w in (self.ruta_existente, elegir_existente):
            self.existente.toggled.connect(w.setEnabled)
            w.setEnabled(False)

    def validatePage(self):
        if self.nueva.isChecked():
            padre = Path(self.padre.text().strip())
            if not padre.is_dir():
                QMessageBox.warning(self, "Carpeta", "No encuentro la carpeta donde crearla.")
                return False
            self.estado.modo = "nueva"
            self.estado.raiz = padre / limpiar_nombre(self.nombre.text().strip() or "Cursos Canvas")
        else:
            raiz = Path(self.ruta_existente.text().strip())
            if not str(raiz) or not raiz.is_dir():
                QMessageBox.warning(self, "Carpeta", "Elige la carpeta donde ya tienes tus cursos.")
                return False
            self.estado.modo = "existente"
            self.estado.raiz = raiz
        self.estado.convenciones = adoptar.Convenciones()
        self.estado.plan = None
        return True

    def nextId(self):
        return ADOPTAR if self.existente.isChecked() else DESCARGA


class PaginaAdoptar(QWizardPage):
    CREAR = "(crear una carpeta nueva)"

    def __init__(self, estado):
        super().__init__()
        self.estado = estado
        self.setTitle("Tu carpeta")
        self.setSubTitle("Revisa qué carpeta tuya es de cada curso.")
        self.convenciones = _texto("")
        self.tabla = QTableWidget(0, 2)
        self.tabla.setHorizontalHeaderLabels(["Curso", "Tu carpeta"])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabla.verticalHeader().hide()
        self.reordenar = QCheckBox("Ordenar los archivos de Canvas que estén en otro lugar "
                                   "(antes te muestro la lista)")
        self.reordenar.setChecked(True)
        caja = QVBoxLayout(self)
        caja.addWidget(self.tabla)
        caja.addWidget(self.convenciones)
        caja.addWidget(self.reordenar)
        caja.addWidget(_texto("<small>Lo que no viene de Canvas (tus trabajos, tus notas) no se "
                              "toca. Nunca se borra ni se reemplaza nada.</small>"))

    def initializePage(self):
        raiz = self.estado.raiz
        self.subcarpetas = sorted((h for h in raiz.iterdir() if h.is_dir()), key=lambda p: p.name.casefold())
        grupos = self.estado.elegidos
        pares = adoptar.emparejar_carpetas({i: g.resumenes[0].nombre for i, g in enumerate(grupos)},
                                           self.subcarpetas)
        self.tabla.setRowCount(len(grupos))
        self.combos = []
        for fila, g in enumerate(grupos):
            curso = QTableWidgetItem(g.nombre + ("  (teoría + lab)" if g.pareja else ""))
            curso.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.tabla.setItem(fila, 0, curso)
            combo = QComboBox()
            combo.addItem(self.CREAR, None)
            for sub in self.subcarpetas:
                combo.addItem(sub.name, sub)
            if pares[fila] is not None:
                combo.setCurrentIndex(self.subcarpetas.index(pares[fila]) + 1)
            combo.currentIndexChanged.connect(self._mostrar_convenciones)
            self.tabla.setCellWidget(fila, 1, combo)
            self.combos.append(combo)
        self.tabla.resizeColumnToContents(1)
        self._mostrar_convenciones()

    def _elegidas(self):
        return [c.currentData() for c in self.combos]

    def _mostrar_convenciones(self):
        carpetas = [c for c in self._elegidas() if c is not None]
        self.estado.convenciones = adoptar.detectar_convenciones(carpetas)
        self.convenciones.setText(f"Así organizas tus carpetas: {self.estado.convenciones.describir()}. "
                                  "Lo nuevo seguirá ese estilo.")

    def validatePage(self):
        vistas = set()
        for g, carpeta in zip(self.estado.elegidos, self._elegidas()):
            if carpeta is None:
                continue
            if carpeta in vistas:
                QMessageBox.warning(self, "Carpetas", f"La carpeta «{carpeta.name}» está elegida dos veces.")
                return False
            vistas.add(carpeta)
            g.carpeta = carpeta.name
        self.estado.plan = None
        return True

    def nextId(self):
        return REORDENAR if self.reordenar.isChecked() else DESCARGA


class PaginaReordenar(QWizardPage):
    def __init__(self, estado):
        super().__init__()
        self.estado = estado
        self._trabajo = None
        self.setTitle("Ordenar tu carpeta")
        self.setSubTitle("Estos archivos vienen de Canvas pero están en otro lugar. "
                         "Se moverán (no se copian ni se borran) al hacer clic en «Terminar».")
        self.mensaje = _texto("Comparando tu carpeta con Canvas…")
        self.barra = QProgressBar()
        self.barra.setRange(0, 0)
        self.lista = QPlainTextEdit(readOnly=True)
        self.lista.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.confirmar = QCheckBox()
        caja = QVBoxLayout(self)
        caja.addWidget(self.mensaje)
        caja.addWidget(self.barra)
        caja.addWidget(self.lista, 1)
        caja.addWidget(self.confirmar)

    def initializePage(self):
        if self.estado.plan is not None:
            return
        self.barra.show()
        self.lista.clear()
        self.confirmar.hide()
        self._trabajo = _Trabajo(self._planificar)
        self._trabajo.aviso.connect(self.mensaje.setText)
        self._trabajo.listo.connect(self._listo)
        self._trabajo.fallo.connect(lambda m: self.mensaje.setText(f"<span style='color:{tema.hex_('error')}'>{m}</span>"))
        self._trabajo.start()

    def _planificar(self, avisar):
        estado = self.estado
        reglas = estado.reglas()
        parejas = emparejar_cursos(estado.cursos, reglas)
        candidatos = candidatos_de(parejas, [estado.modulos.get(c["id"], []) for _, c in parejas])
        avisar(f"Pidiendo a Canvas el tamaño de {len(candidatos)} archivo(s)…")
        metas = metadatos(estado.canvas, candidatos)
        avisar("Buscando cada uno en tu carpeta…")
        carpetas = {r["carpeta"]: resolver_subcarpeta(estado.raiz, r["carpeta"], crear=False) for r in reglas}
        return adoptar.planificar(candidatos, metas, carpetas, estado.secciones(),
                                  estado.convenciones.formato_semana)

    def isComplete(self):
        return self.estado.plan is not None

    def _listo(self, plan):
        self.estado.plan = plan
        self.barra.hide()
        raiz = self.estado.raiz

        def corta(ruta):
            try:
                return str(ruta.relative_to(raiz))
            except ValueError:
                return str(ruta)

        lineas = [f"{corta(m.origen)}\n    → {corta(m.destino.parent)}" for m in plan.movimientos]
        if plan.dudosos:
            lineas += ["", "SE QUEDAN DONDE ESTÁN (no es seguro moverlos):"]
            lineas += [f"  {alias} · {nombre} — {motivo}" for alias, nombre, motivo in plan.dudosos]
        self.lista.setPlainText("\n".join(lineas) or "Todo está en su lugar.")
        self.mensaje.setText(f"{len(plan.movimientos)} para mover · {len(plan.en_su_lugar)} ya en su "
                             f"lugar · {len(plan.dudosos)} se quedan como están")
        self.confirmar.setText(f"Sí, mover estos {len(plan.movimientos)} archivo(s)")
        self.confirmar.setChecked(False)
        self.confirmar.setVisible(bool(plan.movimientos))
        self.completeChanged.emit()

    def validatePage(self):
        self.estado.mover = self.confirmar.isVisible() and self.confirmar.isChecked()
        return True

    def nextId(self):
        return DESCARGA


class PaginaDescarga(QWizardPage):
    def __init__(self, estado):
        super().__init__()
        self.estado = estado
        self.setTitle("Descarga inicial")
        self.setSubTitle("Lo que ya tengas en la carpeta no se vuelve a bajar.")
        self.todo = QRadioButton()
        self.desde = QRadioButton("Solo desde la semana")
        self.nada = QRadioButton("Nada por ahora: solo lo que se publique de hoy en adelante")
        self.todo.setChecked(True)
        self.semana = QSpinBox()
        self.semana.setRange(1, 99)
        grupo = QButtonGroup(self)
        for b in (self.todo, self.desde, self.nada):
            grupo.addButton(b)
        self.programar = QCheckBox("Revisar Canvas automáticamente todos los días a las")
        self.hora = QTimeEdit(QTime(19, 0))
        self.hora.setDisplayFormat("HH:mm")

        fila_desde = QHBoxLayout()
        fila_desde.addWidget(self.desde)
        fila_desde.addWidget(self.semana)
        fila_desde.addWidget(QLabel("en adelante"))
        fila_desde.addStretch()
        fila_hora = QHBoxLayout()
        fila_hora.addWidget(self.programar)
        fila_hora.addWidget(self.hora)
        fila_hora.addStretch()
        caja = QVBoxLayout(self)
        caja.addWidget(self.todo)
        caja.addLayout(fila_desde)
        caja.addWidget(self.nada)
        caja.addSpacing(14)
        caja.addLayout(fila_hora)
        caja.addWidget(_texto("<small>También puedes sincronizar cuando quieras desde el menú "
                              "de Pandex (clic derecho → Sincronizar Canvas).</small>"))
        caja.addStretch()

    def initializePage(self):
        self.todo.setText(f"Todo lo publicado hasta hoy ({self.estado.archivos_elegidos()} archivos)")
        self.semana.setValue(self.estado.ultima_semana())

    def validatePage(self):
        self.estado.inicial = "todo" if self.todo.isChecked() else "desde" if self.desde.isChecked() else "nada"
        self.estado.desde = self.semana.value()
        h = self.hora.time()
        self.estado.horario = f"{h.minute()} {h.hour()} * * *" if self.programar.isChecked() else None
        return True


class PaginaListo(QWizardPage):
    def __init__(self, estado):
        super().__init__()
        self.estado = estado
        self.setTitle("Todo listo")
        self.resumen = _texto("")
        caja = QVBoxLayout(self)
        caja.addWidget(self.resumen)
        caja.addStretch()

    def initializePage(self):
        e = self.estado
        cursos = "".join(f"<li>{g.carpeta}" + (" (teoría + lab)" if g.pareja else "") + "</li>"
                         for g in e.elegidos)
        descarga = {"todo": "todo lo publicado hasta hoy",
                    "desde": f"desde la semana {e.desde} en adelante",
                    "nada": "nada por ahora; solo lo nuevo"}[e.inicial]
        lineas = [f"<b>Carpeta:</b> {e.raiz}", f"<b>Cursos:</b><ul>{cursos}</ul>"]
        if e.modo == "existente":
            lineas.append(f"<b>Estilo de tus carpetas:</b> {e.convenciones.describir()}")
        if e.mover and e.plan:
            lineas.append(f"<b>Reordenar:</b> se mueven {len(e.plan.movimientos)} archivo(s) "
                          "(se puede deshacer)")
        lineas.append(f"<b>Descarga inicial:</b> {descarga}")
        if e.horario:
            h, m = e.horario.split()[1], e.horario.split()[0]
            lineas.append(f"<b>Revisión automática:</b> todos los días a las {int(h):02d}:{int(m):02d}")
        lineas.append("<br>Al terminar empiezo la primera sincronización. Puedes volver a este "
                      "asistente cuando quieras: clic derecho → Configurar Canvas.")
        self.resumen.setText("<br>".join(lineas))


# --------------------------------------------------------------------------
# el asistente
# --------------------------------------------------------------------------


class AsistenteCanvas(QWizard):
    """Devuelve en ``self.entrada`` lo que la primera sincronización debe hacer."""

    def __init__(self, params, guardar, parent=None):
        super().__init__(parent)
        self.params = params
        self._guardar_config = guardar
        self.estado = Estado(params)
        self.entrada = None
        self.setWindowTitle("Configurar Canvas · Pandex")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setPixmap(QWizard.WizardPixmap.LogoPixmap, dibujo.pixmap_logo(48))
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        self.setButtonText(QWizard.WizardButton.FinishButton, "Terminar")
        self.setButtonText(QWizard.WizardButton.NextButton, "Siguiente >")
        self.setButtonText(QWizard.WizardButton.BackButton, "< Atrás")
        self.resize(760, 560)
        paginas = (PaginaBienvenida, PaginaConectar, PaginaCursos, PaginaCarpeta,
                   PaginaAdoptar, PaginaReordenar, PaginaDescarga, PaginaListo)
        for i, Pagina in enumerate(paginas):
            self.setPage(i, Pagina(self.estado))

    def accept(self):
        try:
            self._aplicar()
        except Exception as exc:
            log.exception("no pude terminar la configuración")
            QMessageBox.critical(self, "Configurar Canvas", f"No pude terminar:\n{exc}")
            return
        super().accept()

    def _aplicar(self):
        e = self.estado
        if self.params.get("cursos"):
            copia = DATOS / f"config-canvas-anterior-{datetime.now():%Y%m%d-%H%M%S}.json"
            copia.parent.mkdir(parents=True, exist_ok=True)
            copia.write_text(json.dumps(self.params, ensure_ascii=False, indent=2), encoding="utf-8")
            log.info("configuración anterior guardada en %s", copia)

        reglas = e.reglas()
        e.raiz.mkdir(parents=True, exist_ok=True)
        self._crear_esqueleto(reglas)
        if e.mover and e.plan and e.plan.movimientos:
            self._reordenar()

        for clave in ("calendario", "asistente_visto"):
            self.params.pop(clave, None)
        self.params.update({
            "activa": True,
            "canvas_url": e.url,
            "destino": str(e.raiz),
            "formato_semana": e.convenciones.formato_semana,
            "secciones": e.secciones(),
            "cursos": reglas,
            "schedule": e.horario,
        })
        for clave, valor in (("headless", True), ("usar_chrome_instalado", True),
                             ("dedupe_por_tamano", True), ("espera_login_segundos", 300)):
            self.params.setdefault(clave, valor)
        self._guardar_config()
        self.entrada = {"inicial": e.inicial, "desde_semana": e.desde}
        log.info("Canvas configurado: %d curso(s) en %s", len(reglas), e.raiz)

    def _crear_esqueleto(self, reglas):
        """Carpeta de cada curso y de cada semana que ya existe en Canvas."""
        formato = self.estado.convenciones.formato_semana
        por_id = {r.curso["id"]: r for r in self.estado.resumenes}
        for regla in reglas:
            curso = resolver_subcarpeta(self.estado.raiz, regla["carpeta"])
            for n in por_id[regla["canvas_id"]].semanas:
                semana = resolver_subcarpeta(curso, nombre_semana(n, formato), alias_semana(n))
                if regla.get("subcarpeta_fija"):
                    resolver_subcarpeta(semana, regla["subcarpeta_fija"], regla.get("alias_subcarpeta", []))

    def _reordenar(self):
        plan = self.estado.plan
        progreso = QProgressDialog("Ordenando tu carpeta…", None, 0, len(plan.movimientos), self)
        progreso.setWindowModality(Qt.WindowModality.WindowModal)
        progreso.setMinimumDuration(300)

        def avance(i, total):
            progreso.setValue(i)

        historial = Historial()
        hechos, saltados, _diario = adoptar.aplicar(plan, historial, avance)
        historial.guardar()
        progreso.close()
        texto = f"Moví {len(hechos)} archivo(s) a su lugar."
        if saltados:
            texto += f"\n{len(saltados)} se quedaron donde estaban (el destino se ocupó)."
        texto += "\n\nSi algo no te gusta: clic derecho → Configurar Canvas → Deshacer."
        QMessageBox.information(self, "Carpeta ordenada", texto)
