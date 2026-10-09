"""El explorador de archivos de «Convertir a Markdown»: claro con el mouse, rápido con el teclado.

Una tabla como la del Explorador de Windows (nombre, estado, tipo, tamaño y fecha) que
además dice qué es material de estudio y qué ya está en ``.md``.
"""

from collections import Counter
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QFileInfo, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFileIconProvider,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import horas
from ..ui import iconos, tema
from .archivos import (
    AVISO_LOTE,
    SIN_IA,
    SOPORTADOS,
    listar,
    orden_natural,
    recorrer,
    ruta_md,
)
from .clasificador import Clasificador

ROL = Qt.ItemDataRole.UserRole
CLAVE = Qt.ItemDataRole.UserRole + 1  # para ordenar cada columna
SUBIR, INICIO, RAIZ, CARPETA, ARCHIVO, ULTIMA = range(6)
NOMBRE, ESTADO, TIPO, TAMANO, FECHA = range(5)
COLUMNAS = ("Nombre", "Estado", "Tipo", "Tamaño", "Modificado")


def _tamano(n):
    for unidad in ("B", "KB", "MB", "GB"):
        if n < 1024 or unidad == "GB":
            return f"{n:.0f} {unidad}" if unidad == "B" else f"{n:.1f} {unidad}".replace(".", ",")
        n /= 1024
    return ""


class _Fila(QTreeWidgetItem):
    """Ordena por la columna elegida, pero «..» y las carpetas siempre van arriba."""

    def __lt__(self, otra):
        arbol = self.treeWidget()
        columna = arbol.sortColumn() if arbol else NOMBRE
        descendente = arbol is not None and arbol.header().sortIndicatorOrder() == Qt.SortOrder.DescendingOrder
        grupo, grupo_otra = self.data(NOMBRE, CLAVE)[0], otra.data(NOMBRE, CLAVE)[0]
        if grupo != grupo_otra:
            return (grupo < grupo_otra) != descendente
        return self.data(columna, CLAVE) < otra.data(columna, CLAVE)


class Navegador(QDialog):
    """Elegir archivos o una carpeta sin escribir rutas.

    Mouse: doble clic abre una carpeta o marca un archivo; la casilla también marca.
    Teclado: ↑↓ moverse · Enter abrir/marcar · Espacio marcar · Retroceso subir
             Ctrl+F buscar · Ctrl+A marcar el material · Ctrl+Enter convertir marcados
             Ctrl+M material de estudio de esta carpeta · Ctrl+T todos · 1-9 raíz
             Esc cancelar · y escribir las primeras letras salta al nombre.
    """

    def __init__(self, raices_, ultima=None, clasificador=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Convertir a Markdown")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(860, 600)

        self.raices = raices_
        self.ultima = Path(ultima) if ultima and Path(ultima).is_dir() else None
        self.clasificador = clasificador or Clasificador()
        self.proveedor = QFileIconProvider()  # los mismos íconos del Explorador
        self._iconos = {}  # por extensión: pedirle el ícono a Windows por cada archivo es lento
        self.actual = None  # None = pantalla de inicio
        self.marcados = set()
        self.resultado = None
        self._repetidos = set()
        self._cuenta = (0, 0)  # (material de estudio, todos) en la carpeta actual

        # barra de arriba: subir · migas · buscar · abrir en el Explorador
        self.btn_subir = QPushButton(iconos.icono("subir"), "")
        self.btn_subir.setToolTip("Subir un nivel (Retroceso)")
        self.btn_subir.clicked.connect(self._subir)
        self.migas = QHBoxLayout()
        self.migas.setSpacing(0)
        self.migas.setContentsMargins(0, 0, 0, 0)
        contenedor_migas = QWidget()
        contenedor_migas.setLayout(self.migas)
        # que una ruta larga nunca empuje el ancho del diálogo
        contenedor_migas.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.buscar = QLineEdit()
        self.buscar.setPlaceholderText("Buscar aquí (Ctrl+F)")
        self.buscar.addAction(iconos.icono("buscar"), QLineEdit.ActionPosition.LeadingPosition)
        self.buscar.setClearButtonEnabled(True)
        self.buscar.setFixedWidth(240)
        self.buscar.textChanged.connect(self._filtrar)
        self.btn_explorador = QPushButton(iconos.icono("carpeta"), "")
        self.btn_explorador.setToolTip("Abrir esta carpeta en el Explorador de Windows")
        self.btn_explorador.clicked.connect(self._abrir_en_explorador)
        barra = QHBoxLayout()
        barra.setSpacing(8)
        barra.addWidget(self.btn_subir)
        barra.addWidget(contenedor_migas, 1)
        barra.addWidget(self.buscar)
        barra.addWidget(self.btn_explorador)

        self.lista = QTreeWidget()
        self.lista.setColumnCount(len(COLUMNAS))
        self.lista.setHeaderLabels(COLUMNAS)
        self.lista.setRootIsDecorated(False)
        self.lista.setUniformRowHeights(True)
        self.lista.setAllColumnsShowFocus(True)
        self.lista.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.lista.setFont(tema.fuente(10))
        cabecera = self.lista.header()
        cabecera.setStretchLastSection(False)
        cabecera.setSectionResizeMode(NOMBRE, QHeaderView.ResizeMode.Stretch)
        for col in (ESTADO, TIPO, TAMANO, FECHA):
            cabecera.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setSortIndicator(NOMBRE, Qt.SortOrder.AscendingOrder)
        self.lista.itemActivated.connect(self._activar)
        self.lista.itemChanged.connect(self._al_marcar)
        self.estado = QLabel()
        self.estado.setProperty("rol", "suave")

        self.recursivo = QCheckBox("Incluir subcarpetas")
        self.recursivo.toggled.connect(self._refrescar_botones)
        self.forzar = QCheckBox("Forzar reconversión")
        self.forzar.setToolTip(
            "Vuelve a convertir aunque ya exista el .md.\n"
            "Solo reescribe .md creados por Pandex: los tuyos no se tocan."
        )

        self.btn_estudio = QPushButton()
        self.btn_estudio.setToolTip(
            "Convierte solo material de estudio: clases, guías, resúmenes y lecturas (Ctrl+M).\n"
            "Deja fuera actividades previas, tareas, evaluaciones, preguías, HTML…"
        )
        self.btn_estudio.setProperty("rol", "primario")
        self.btn_estudio.clicked.connect(lambda: self._elegir_carpeta("estudio"))
        self.btn_todos = QPushButton()
        self.btn_todos.setToolTip("Convierte todo lo convertible de la carpeta, sin filtrar (Ctrl+T).")
        self.btn_todos.clicked.connect(lambda: self._elegir_carpeta("todos"))
        self.btn_convertir = QPushButton()
        self.btn_convertir.setToolTip("Convierte los archivos que marcaste (Ctrl+Enter).")
        self.btn_convertir.clicked.connect(self._elegir_marcados)
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self.reject)
        for b in (self.btn_subir, self.btn_explorador, self.btn_estudio, self.btn_todos,
                  self.btn_convertir, cancelar):
            b.setAutoDefault(False)
        for b in (self.btn_subir, self.btn_explorador):
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setFixedWidth(38)
            b.setStyleSheet("QPushButton { padding: 4px; min-width: 0; }")

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

        ayuda = QLabel("Doble clic o Enter: abrir o marcar · Espacio: marcar · Retroceso: subir · "
                       "Ctrl+F: buscar · en gris: lo que no es material de estudio")
        ayuda.setProperty("rol", "suave")
        ayuda.setStyleSheet("font-size: 8pt;")

        cuerpo = QVBoxLayout(self)
        cuerpo.addLayout(barra)
        cuerpo.addWidget(self.lista, 1)
        cuerpo.addWidget(self.estado)
        cuerpo.addLayout(opciones)
        cuerpo.addLayout(botones)
        cuerpo.addWidget(ayuda)

        QShortcut(QKeySequence("Backspace"), self.lista, activated=self._subir)
        QShortcut(QKeySequence("Alt+Left"), self, activated=self._subir)
        QShortcut(QKeySequence("Alt+Up"), self, activated=self._subir)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._enfocar_busqueda)
        QShortcut(QKeySequence("Ctrl+A"), self, activated=self._marcar_todo)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._elegir_marcados)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self._elegir_marcados)
        QShortcut(QKeySequence("Ctrl+M"), self, activated=lambda: self._elegir_carpeta("estudio"))
        QShortcut(QKeySequence("Ctrl+T"), self, activated=lambda: self._elegir_carpeta("todos"))
        QShortcut(QKeySequence("Space"), self.lista, activated=self._alternar_actual)
        # buscar → ↓ baja a la lista; Enter abre el primero que coincide
        self.buscar.returnPressed.connect(self._abrir_primero)
        # solo en la pantalla de inicio: dentro de una carpeta los dígitos sirven
        # para saltar escribiendo (p. ej. «05_Analisis»)
        self._atajos_raiz = [
            QShortcut(QKeySequence(str(n)), self.lista, activated=lambda n=n: self._atajo_raiz(n))
            for n in range(1, 10)
        ]

        self._mostrar(None)

    # ---------- pintar ----------

    def _icono(self, rol, ruta):
        if rol == ARCHIVO:
            ext = Path(ruta).suffix.lower()
            if ext not in self._iconos:
                self._iconos[ext] = self.proveedor.icon(QFileInfo(str(ruta)))
            return self._iconos[ext]
        if rol in (RAIZ, ULTIMA) and ruta:
            return self.proveedor.icon(QFileInfo(str(ruta)))
        if rol == SUBIR:
            return iconos.icono("subir")
        if "carpeta" not in self._iconos:
            self._iconos["carpeta"] = self.proveedor.icon(QFileIconProvider.IconType.Folder)
        return self._iconos["carpeta"]

    def _fila(self, textos, rol, ruta=None, claves=None, marcable=False, gris=False, ayuda=None):
        """Una fila de la tabla. ``textos``: nombre, estado, tipo, tamaño, fecha."""
        fila = _Fila([str(t) for t in textos])
        fila.setIcon(NOMBRE, self._icono(rol, ruta))
        fila.setData(NOMBRE, ROL, (rol, str(ruta) if ruta else None))
        grupo = {SUBIR: 0, RAIZ: 1, ULTIMA: 2, CARPETA: 1}.get(rol, 3)
        claves = claves or {}
        fila.setData(NOMBRE, CLAVE, (grupo, orden_natural(textos[0])))
        for col in (ESTADO, TIPO, TAMANO, FECHA):
            fila.setData(col, CLAVE, claves.get(col, textos[col].casefold() if isinstance(textos[col], str) else 0))
        for col in (TAMANO,):
            fila.setTextAlignment(col, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if marcable:
            flags |= Qt.ItemFlag.ItemIsUserCheckable
            fila.setCheckState(NOMBRE, Qt.CheckState.Checked if str(ruta) in self.marcados
                               else Qt.CheckState.Unchecked)
        fila.setFlags(flags)
        suave = tema.color("texto_suave")
        for col in range(len(COLUMNAS)):
            if gris or col != NOMBRE:
                fila.setForeground(col, suave)
        if ayuda:
            for col in range(len(COLUMNAS)):
                fila.setToolTip(col, ayuda)
        return fila

    def _fecha(self, momento):
        dt = datetime.fromtimestamp(momento)
        return f"{dt:%d/%m/%Y} {horas.de(dt)}"

    def _mostrar(self, carpeta):
        self.actual = Path(carpeta) if carpeta else None
        for atajo in self._atajos_raiz:
            atajo.setEnabled(self.actual is None)
        self.buscar.blockSignals(True)
        self.buscar.clear()
        self.buscar.blockSignals(False)
        self.lista.blockSignals(True)
        self.lista.setSortingEnabled(False)
        self.lista.clear()
        self._pintar_migas()
        filas = []

        if self.actual is None:
            for i, (etiqueta, ruta) in enumerate(self.raices, start=1):
                filas.append(self._fila((f"{i}   {etiqueta}", "", "Carpeta", "", ""), RAIZ, ruta,
                                        claves={ESTADO: i}, ayuda=str(ruta)))
            if self.ultima:
                filas.append(self._fila((f"Última carpeta: {self._corta(self.ultima)}", "", "Carpeta", "", ""),
                                        ULTIMA, self.ultima, ayuda=str(self.ultima)))
            if not self.raices:
                self.estado.setText("No encontré OneDrive, Escritorio, Descargas ni Documentos.")
            else:
                self.estado.setText("Elige dónde empezar: doble clic, o pulsa su número.")
            self._cuenta = (0, 0)
        else:
            subcarpetas, archivos, sin_ia = listar(self.actual)
            self._repetidos = {
                s for s, n in Counter(p.stem.casefold() for p in archivos).items() if n > 1
            }
            filas.append(self._fila(("..", "", "", "", ""), SUBIR, ayuda="Subir un nivel"))
            for sub in subcarpetas:
                fecha = self._mtime(sub)
                filas.append(self._fila((sub.name, "", "Carpeta", "", self._fecha(fecha) if fecha else ""),
                                        CARPETA, sub, claves={FECHA: fecha, TAMANO: -1}))
            estudio = ya = 0
            for archivo in archivos:
                es, motivo = self.clasificador.clasificar(archivo)
                convertido = ruta_md(archivo, self._repetidos).exists()
                estudio += es
                ya += convertido
                if convertido:
                    estado = "✓ Ya en .md"
                elif es:
                    estado = "Material de estudio"
                else:
                    estado = f"No: {motivo}"
                try:
                    info = archivo.stat()
                    tam, fecha = info.st_size, info.st_mtime
                except OSError:
                    tam, fecha = 0, 0
                tipo = SOPORTADOS.get(archivo.suffix.lower(), archivo.suffix.lstrip(".").upper())
                ayuda = (f"Material de estudio ({motivo})" if es else
                         f"No es material de estudio: {motivo}.\n"
                         "Márcalo a mano o usa «Todos» si igual lo quieres.")
                fila = self._fila((archivo.name, estado, tipo, _tamano(tam), self._fecha(fecha) if fecha else ""),
                                  ARCHIVO, archivo, claves={TAMANO: tam, FECHA: fecha},
                                  marcable=True, gris=not es, ayuda=ayuda)
                if convertido:
                    fila.setForeground(ESTADO, tema.color("exito"))
                filas.append(fila)
            self._cuenta = (estudio, len(archivos))
            partes = [f"{len(subcarpetas)} carpeta(s)",
                      f"{len(archivos)} archivo(s): {estudio} material de estudio"]
            if ya:
                partes.append(f"{ya} ya en .md")
            if sin_ia:
                partes.append(f"{sin_ia} de audio/video (no soportado sin IA)")
            self.estado.setText(" · ".join(partes))

        self.lista.addTopLevelItems(filas)
        for col in (ESTADO, TAMANO, FECHA):  # en el inicio solo importa el nombre
            self.lista.setColumnHidden(col, self.actual is None)
        self.lista.setSortingEnabled(self.actual is not None)
        self.lista.blockSignals(False)
        primera = 1 if self.actual is not None and self.lista.topLevelItemCount() > 1 else 0
        if self.lista.topLevelItemCount():
            self.lista.setCurrentItem(self.lista.topLevelItem(primera))
        self.btn_subir.setEnabled(self.actual is not None)
        self.btn_explorador.setEnabled(self.actual is not None)
        self.buscar.setEnabled(self.actual is not None)
        self.lista.setFocus()
        self._refrescar_botones()

    @staticmethod
    def _mtime(ruta):
        try:
            return ruta.stat().st_mtime
        except OSError:
            return 0

    def _filas(self):
        return [self.lista.topLevelItem(i) for i in range(self.lista.topLevelItemCount())]

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
                sep.setProperty("rol", "suave")
                self.migas.addWidget(sep)
                boton(texto, destino)
        self.migas.addStretch()

    def _raiz_de(self, carpeta):
        # la más específica primero: «Mis cursos» suele estar dentro del OneDrive
        for etiqueta, ruta in sorted(self.raices, key=lambda r: len(r[1].parts), reverse=True):
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

    def _activar(self, item, _columna=0):
        rol, ruta = item.data(NOMBRE, ROL)
        if rol in (RAIZ, CARPETA, ULTIMA):
            self._mostrar(ruta)
        elif rol == SUBIR:
            self._subir()
        elif rol == ARCHIVO:
            self._alternar(item)

    def _alternar(self, item):
        nuevo = (Qt.CheckState.Unchecked if item.checkState(NOMBRE) == Qt.CheckState.Checked
                 else Qt.CheckState.Checked)
        item.setCheckState(NOMBRE, nuevo)

    def _alternar_actual(self):
        item = self.lista.currentItem()
        if item and item.data(NOMBRE, ROL)[0] == ARCHIVO:
            self._alternar(item)
            debajo = self.lista.itemBelow(item)
            if debajo is not None:
                self.lista.setCurrentItem(debajo)
        elif item:
            self._activar(item)

    def _al_marcar(self, item, columna=NOMBRE):
        rol, ruta = item.data(NOMBRE, ROL)
        if rol != ARCHIVO or columna != NOMBRE:
            return
        if item.checkState(NOMBRE) == Qt.CheckState.Checked:
            self.marcados.add(ruta)
        else:
            self.marcados.discard(ruta)
        self._refrescar_botones()

    def _marcar_todo(self):
        """Marca el material de estudio de la carpeta; otra vez, desmarca todo."""
        archivos = [f for f in self._filas() if f.data(NOMBRE, ROL)[0] == ARCHIVO and not f.isHidden()]
        de_estudio = [f for f in archivos if self.clasificador.clasificar(f.data(NOMBRE, ROL)[1])[0]]
        if de_estudio and all(f.checkState(NOMBRE) == Qt.CheckState.Checked for f in de_estudio):
            for fila in archivos:
                fila.setCheckState(NOMBRE, Qt.CheckState.Unchecked)
        else:
            for fila in de_estudio:
                fila.setCheckState(NOMBRE, Qt.CheckState.Checked)

    def _subir(self):
        if self.actual is None:
            return
        raiz = self._raiz_de(self.actual)
        if raiz is not None and self.actual == raiz[1]:
            self._mostrar(None)
            return
        anterior = self.actual
        self._mostrar(self.actual.parent)
        for fila in self._filas():
            if fila.data(NOMBRE, ROL)[1] == str(anterior):
                self.lista.setCurrentItem(fila)
                break

    def _atajo_raiz(self, n):
        if self.actual is None and n <= len(self.raices):
            self._mostrar(self.raices[n - 1][1])

    def _enfocar_busqueda(self):
        if self.buscar.isEnabled():
            self.buscar.setFocus()
            self.buscar.selectAll()

    def _filtrar(self, texto):
        buscado = texto.strip().casefold()
        primera = None
        for fila in self._filas():
            rol = fila.data(NOMBRE, ROL)[0]
            visible = rol == SUBIR or not buscado or buscado in fila.text(NOMBRE).casefold()
            fila.setHidden(not visible)
            if visible and rol != SUBIR and primera is None:
                primera = fila
        if primera is not None:
            self.lista.setCurrentItem(primera)

    def _abrir_primero(self):
        item = self.lista.currentItem()
        if item is not None and not item.isHidden():
            self._activar(item)
            self.lista.setFocus()

    def _abrir_en_explorador(self):
        if self.actual is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.actual)))

    def keyPressEvent(self, evento):
        # Esc con una búsqueda escrita la borra; sin búsqueda, cierra
        if evento.key() == Qt.Key.Key_Escape and self.buscar.text():
            self.buscar.clear()
            self.lista.setFocus()
            return
        if evento.key() == Qt.Key.Key_Down and self.buscar.hasFocus():
            self.lista.setFocus()
            return
        super().keyPressEvent(evento)

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
