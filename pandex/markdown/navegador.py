"""El navegador de archivos de «Convertir a Markdown», pensado para el teclado."""

from collections import Counter
from pathlib import Path

from PyQt6.QtCore import QFileInfo, Qt
from PyQt6.QtGui import QColor, QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileIconProvider,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from .archivos import AVISO_LOTE, SIN_IA, SOPORTADOS, listar, orden_natural, recorrer, ruta_md
from .clasificador import Clasificador

ROL = Qt.ItemDataRole.UserRole
SUBIR, INICIO, RAIZ, CARPETA, ARCHIVO, ULTIMA = range(6)
GRIS = QColor("#9ca3af")


class Navegador(QDialog):
    """Elegir archivos o una carpeta sin escribir rutas.

    Teclado: ↑↓ moverse · Enter entrar/marcar · Espacio marcar · Retroceso subir
             Ctrl+A marcar el material · Ctrl+Enter convertir marcados
             Ctrl+M material de estudio de esta carpeta · Ctrl+T todos · 1-9 raíz
             Esc cancelar · y escribir las primeras letras salta al nombre.
    """

    def __init__(self, raices_, ultima=None, clasificador=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Convertir a Markdown")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(700, 580)

        self.raices = raices_
        self.ultima = Path(ultima) if ultima and Path(ultima).is_dir() else None
        self.clasificador = clasificador or Clasificador()
        self.iconos = QFileIconProvider()  # los mismos íconos del Explorador
        self.actual = None  # None = pantalla de inicio
        self.marcados = set()
        self.resultado = None
        self._repetidos = set()
        self._cuenta = (0, 0)  # (material de estudio, todos) en la carpeta actual

        self.migas = QHBoxLayout()
        self.migas.setSpacing(0)
        self.migas.setContentsMargins(0, 0, 0, 0)
        self.lista = QListWidget()
        self.lista.setFont(QFont("Segoe UI", 10))
        self.lista.setUniformItemSizes(True)
        self.lista.itemActivated.connect(self._activar)
        self.lista.itemChanged.connect(self._al_marcar)
        self.estado = QLabel()
        self.estado.setStyleSheet("color: #6b7280;")

        self.recursivo = QCheckBox("Incluir subcarpetas")
        self.recursivo.toggled.connect(self._refrescar_botones)
        self.forzar = QCheckBox("Forzar reconversión")
        self.forzar.setToolTip(
            "Vuelve a convertir aunque ya exista el .md.\n"
            "Solo reescribe .md creados por Pandex: los tuyos no se tocan."
        )

        self.btn_estudio = QPushButton()
        self.btn_estudio.setToolTip(
            "Convierte solo material de estudio: clases, guías, resúmenes y lecturas.\n"
            "Deja fuera actividades previas, tareas, evaluaciones, preguías, HTML…"
        )
        self.btn_estudio.setStyleSheet("QPushButton { font-weight: 600; }")
        self.btn_estudio.clicked.connect(lambda: self._elegir_carpeta("estudio"))
        self.btn_todos = QPushButton()
        self.btn_todos.setToolTip("Convierte todo lo convertible de la carpeta, sin filtrar.")
        self.btn_todos.clicked.connect(lambda: self._elegir_carpeta("todos"))
        self.btn_convertir = QPushButton()
        self.btn_convertir.clicked.connect(self._elegir_marcados)
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self.reject)
        for b in (self.btn_estudio, self.btn_todos, self.btn_convertir, cancelar):
            b.setAutoDefault(False)

        opciones = QHBoxLayout()
        opciones.addWidget(self.recursivo)
        opciones.addWidget(self.forzar)
        opciones.addStretch()
        botones = QHBoxLayout()
        self.etiqueta_carpeta = QLabel("Esta carpeta:")
        botones.addWidget(self.etiqueta_carpeta)
        botones.addWidget(self.btn_estudio)
        botones.addWidget(self.btn_todos)
        botones.addStretch()
        botones.addWidget(cancelar)
        botones.addWidget(self.btn_convertir)

        ayuda = QLabel(
            "Enter entrar/marcar · Espacio marcar · Retroceso subir · Ctrl+A marcar material · "
            "Ctrl+Enter convertir marcados\nCtrl+M material de estudio de la carpeta · "
            "Ctrl+T todos · Esc cancelar · en gris: lo que no es material de estudio"
        )
        ayuda.setStyleSheet("color: #9ca3af; font-size: 8pt;")

        cuerpo = QVBoxLayout(self)
        contenedor_migas = QWidget()
        contenedor_migas.setLayout(self.migas)
        # que una ruta larga nunca empuje el ancho del diálogo
        contenedor_migas.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        cuerpo.addWidget(contenedor_migas)
        cuerpo.addWidget(self.lista, 1)
        cuerpo.addWidget(self.estado)
        cuerpo.addLayout(opciones)
        cuerpo.addLayout(botones)
        cuerpo.addWidget(ayuda)

        QShortcut(QKeySequence("Backspace"), self, activated=self._subir)
        QShortcut(QKeySequence("Alt+Left"), self, activated=self._subir)
        QShortcut(QKeySequence("Ctrl+A"), self, activated=self._marcar_todo)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._elegir_marcados)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self._elegir_marcados)
        QShortcut(QKeySequence("Ctrl+M"), self, activated=lambda: self._elegir_carpeta("estudio"))
        QShortcut(QKeySequence("Ctrl+T"), self, activated=lambda: self._elegir_carpeta("todos"))
        QShortcut(QKeySequence("Space"), self.lista, activated=self._alternar_actual)
        # solo en la pantalla de inicio: dentro de una carpeta los dígitos sirven
        # para saltar escribiendo (p. ej. «05_Analisis»)
        self._atajos_raiz = [
            QShortcut(QKeySequence(str(n)), self, activated=lambda n=n: self._atajo_raiz(n))
            for n in range(1, 10)
        ]

        self._mostrar(None)

    # ---------- pintar ----------

    def _icono(self, rol, ruta):
        if rol in (RAIZ, CARPETA, ARCHIVO) and ruta:
            return self.iconos.icon(QFileInfo(str(ruta)))
        estandar = {
            SUBIR: QStyle.StandardPixmap.SP_FileDialogToParent,
            ULTIMA: QStyle.StandardPixmap.SP_BrowserReload,
        }[rol]
        return self.style().standardIcon(estandar)

    def _item(self, texto, rol, ruta=None, marcable=False, gris=False, ayuda=None):
        # el ícono va aparte y el texto empieza por el nombre: así funciona
        # escribir las primeras letras para saltar
        item = QListWidgetItem(self._icono(rol, ruta), texto)
        item.setData(ROL, (rol, str(ruta) if ruta else None))
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if marcable:
            flags |= Qt.ItemFlag.ItemIsUserCheckable
            item.setCheckState(
                Qt.CheckState.Checked if str(ruta) in self.marcados else Qt.CheckState.Unchecked
            )
        item.setFlags(flags)
        if gris:
            item.setForeground(GRIS)
        if ayuda:
            item.setToolTip(ayuda)
        return item

    def _mostrar(self, carpeta):
        self.actual = Path(carpeta) if carpeta else None
        for atajo in self._atajos_raiz:
            atajo.setEnabled(self.actual is None)
        self.lista.blockSignals(True)
        self.lista.clear()
        self._pintar_migas()

        if self.actual is None:
            for i, (etiqueta, ruta) in enumerate(self.raices, start=1):
                self.lista.addItem(self._item(f"{i}   {etiqueta}", RAIZ, ruta, ayuda=str(ruta)))
            if self.ultima:
                self.lista.addItem(
                    self._item(f"Última carpeta: {self._corta(self.ultima)}", ULTIMA, self.ultima)
                )
            if not self.raices:
                self.estado.setText("No encontré OneDrive, Descargas ni Documentos.")
            else:
                self.estado.setText("Elige dónde empezar (o pulsa su número).")
            self._cuenta = (0, 0)
        else:
            subcarpetas, archivos, sin_ia = listar(self.actual)
            self._repetidos = {
                s for s, n in Counter(p.stem.casefold() for p in archivos).items() if n > 1
            }
            self.lista.addItem(self._item("..", SUBIR))
            for sub in subcarpetas:
                self.lista.addItem(self._item(sub.name, CARPETA, sub))
            estudio = ya = 0
            for archivo in archivos:
                es, motivo = self.clasificador.clasificar(archivo)
                convertido = ruta_md(archivo, self._repetidos).exists()
                estudio += es
                ya += convertido
                texto = archivo.name
                if convertido:
                    texto += "      ✓ ya en .md"
                if not es:
                    texto += f"      · no: {motivo}"
                ayuda = (f"Material de estudio ({motivo})" if es else
                         f"No es material de estudio: {motivo}.\n"
                         "Márcalo a mano o usa «Todos» si igual lo quieres.")
                self.lista.addItem(self._item(texto, ARCHIVO, archivo, True, not es, ayuda))
            self._cuenta = (estudio, len(archivos))
            partes = [f"{len(subcarpetas)} carpeta(s)",
                      f"{len(archivos)} archivo(s): {estudio} material de estudio"]
            if ya:
                partes.append(f"{ya} ya en .md")
            if sin_ia:
                partes.append(f"{sin_ia} de audio/video (no soportado sin IA)")
            self.estado.setText(" · ".join(partes))

        self.lista.blockSignals(False)
        self.lista.setCurrentRow(1 if self.actual is not None and self.lista.count() > 1 else 0)
        self.lista.setFocus()
        self._refrescar_botones()

    def _pintar_migas(self):
        while self.migas.count():
            w = self.migas.takeAt(0).widget()
            if w:
                # desengancharlo ya; con solo deleteLater el botón viejo sigue
                # un instante en pantalla encima de los nuevos
                w.setParent(None)
                w.deleteLater()

        def boton(texto, destino):
            b = QPushButton(texto)
            b.setFlat(True)
            b.setAutoDefault(False)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet("QPushButton { padding: 2px 5px; }")
            b.setToolTip(str(destino) if destino else "Elegir otra raíz")
            b.clicked.connect(lambda: self._mostrar(destino))
            self.migas.addWidget(b)

        boton("Inicio", None)
        if self.actual is not None:
            raiz = self._raiz_de(self.actual)
            if raiz is not None:
                etiqueta, ruta_raiz = raiz
                cadena = [(etiqueta.split(" · ")[0], ruta_raiz)]
                for parte in self.actual.relative_to(ruta_raiz).parts:
                    cadena.append((parte, cadena[-1][1] / parte))
            else:
                cadena = [(p.name or str(p), p) for p in reversed([self.actual, *self.actual.parents])]
            # en rutas hondas: raíz › … › penúltima › actual, para no ensanchar el diálogo
            if len(cadena) > 4:
                cadena = [cadena[0], ("…", cadena[-3][1]), cadena[-2], cadena[-1]]
            for texto, destino in cadena:
                sep = QLabel("›")
                sep.setStyleSheet("color: #9ca3af;")
                self.migas.addWidget(sep)
                boton(texto, destino)
        self.migas.addStretch()

    def _raiz_de(self, carpeta):
        for etiqueta, ruta in self.raices:
            if carpeta == ruta or ruta in carpeta.parents:
                return etiqueta, ruta
        return None

    def _corta(self, ruta):
        raiz = self._raiz_de(ruta)
        if raiz is None:
            return str(ruta)
        rel = ruta.relative_to(raiz[1])
        return raiz[0].split(" · ")[0] + ("\\" + str(rel) if str(rel) != "." else "")

    def _refrescar_botones(self):
        n = len(self.marcados)
        self.btn_convertir.setText(f"Convertir {n} marcado(s)" if n else "Convertir marcados")
        self.btn_convertir.setEnabled(n > 0)
        en_carpeta = self.actual is not None
        for w in (self.btn_estudio, self.btn_todos, self.recursivo, self.etiqueta_carpeta):
            w.setEnabled(en_carpeta)
        estudio, todos = self._cuenta
        if en_carpeta and not self.recursivo.isChecked():
            self.btn_estudio.setText(f"Material de estudio ({estudio})")
            self.btn_todos.setText(f"Todos ({todos})")
        else:
            self.btn_estudio.setText("Material de estudio")
            self.btn_todos.setText("Todos")

    # ---------- acciones ----------

    def _activar(self, item):
        rol, ruta = item.data(ROL)
        if rol in (RAIZ, CARPETA, ULTIMA):
            self._mostrar(ruta)
        elif rol == SUBIR:
            self._subir()
        elif rol == ARCHIVO:
            self._alternar(item)

    def _alternar(self, item):
        nuevo = (
            Qt.CheckState.Unchecked
            if item.checkState() == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        item.setCheckState(nuevo)

    def _alternar_actual(self):
        item = self.lista.currentItem()
        if item and item.data(ROL)[0] == ARCHIVO:
            self._alternar(item)
            fila = self.lista.currentRow()
            if fila < self.lista.count() - 1:
                self.lista.setCurrentRow(fila + 1)
        elif item:
            self._activar(item)

    def _al_marcar(self, item):
        rol, ruta = item.data(ROL)
        if rol != ARCHIVO:
            return
        if item.checkState() == Qt.CheckState.Checked:
            self.marcados.add(ruta)
        else:
            self.marcados.discard(ruta)
        self._refrescar_botones()

    def _marcar_todo(self):
        """Marca el material de estudio de la carpeta; otra vez, desmarca todo."""
        archivos = [
            self.lista.item(i) for i in range(self.lista.count())
            if self.lista.item(i).data(ROL)[0] == ARCHIVO
        ]
        de_estudio = [i for i in archivos if self.clasificador.clasificar(i.data(ROL)[1])[0]]
        if de_estudio and all(i.checkState() == Qt.CheckState.Checked for i in de_estudio):
            for item in archivos:
                item.setCheckState(Qt.CheckState.Unchecked)
        else:
            for item in de_estudio:
                item.setCheckState(Qt.CheckState.Checked)

    def _subir(self):
        if self.actual is None:
            return
        raiz = self._raiz_de(self.actual)
        if raiz is not None and self.actual == raiz[1]:
            self._mostrar(None)
            return
        anterior = self.actual
        self._mostrar(self.actual.parent)
        for i in range(self.lista.count()):
            if self.lista.item(i).data(ROL)[1] == str(anterior):
                self.lista.setCurrentRow(i)
                break

    def _atajo_raiz(self, n):
        if self.actual is None and n <= len(self.raices):
            self._mostrar(self.raices[n - 1][1])

    def _elegir_marcados(self):
        if not self.marcados:
            return
        archivos = sorted(self.marcados, key=lambda s: orden_natural(s))
        self.resultado = {
            "archivos": archivos,
            "forzar": self.forzar.isChecked(),
            "carpeta": str(self.actual or Path(archivos[0]).parent),
        }
        self.accept()

    def _elegir_carpeta(self, filtro):
        if self.actual is None:
            return
        recursivo = self.recursivo.isChecked()
        total, limite = 0, 5000
        for ruta in recorrer(self.actual, recursivo):
            ext = ruta.suffix.lower()
            if ext in SIN_IA or (ext in SOPORTADOS and (
                    filtro == "todos" or self.clasificador.clasificar(ruta)[0])):
                total += 1
                if total >= limite:
                    break
        if total == 0:
            donde = "aquí ni en sus subcarpetas" if recursivo else "en esta carpeta"
            que = "material de estudio" if filtro == "estudio" else "archivos convertibles"
            extra = ("\n\nSi igual quieres los demás, usa «Todos»." if filtro == "estudio"
                     and self._cuenta[1] else "")
            QMessageBox.information(self, "Nada que convertir", f"No hay {que} {donde}.{extra}")
            return
        if total >= AVISO_LOTE:
            cuantos = f"más de {limite}" if total >= limite else str(total)
            r = QMessageBox.question(
                self, "Carpeta grande",
                f"Son {cuantos} archivos a revisar en\n{self.actual}\n\n"
                "Se creará un .md junto a cada uno que no lo tenga. ¿Seguir?",
            )
            if r != QMessageBox.StandardButton.Yes:
                return
        self.resultado = {
            "carpeta": str(self.actual),
            "recursivo": recursivo,
            "forzar": self.forzar.isChecked(),
            "filtro": filtro,
        }
        self.accept()
