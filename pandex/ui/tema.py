"""El aspecto de Pandex: colores, tipografía y una sola hoja de estilos para toda la app.

Base neutra y cálida (marfil de día, grafito de noche) con el azul del panda como
acento. Sigue el modo claro/oscuro de Windows. Todo se calcula una vez: no hay
nada animándose en segundo plano.
"""

import sys

from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QPalette

CLARO = {
    "fondo": "#FAF9F5",
    "superficie": "#FFFFFF",
    "superficie_2": "#F0EEE6",
    "borde": "#E3DFD3",
    "borde_fuerte": "#CFC9B8",
    "texto": "#1F1E1D",
    "texto_suave": "#6B675E",
    "acento": "#3B6EA8",
    "acento_hover": "#2F5C8F",
    "acento_suave": "#E3ECF6",
    "sobre_acento": "#FFFFFF",
    "terracota": "#D97757",
    "exito": "#2F8F5B",
    "aviso": "#B45309",
    "error": "#B91C1C",
    "sombra": "#000000",
}

OSCURO = {
    "fondo": "#1F1E1D",
    "superficie": "#2A2927",
    "superficie_2": "#343330",
    "borde": "#3D3B37",
    "borde_fuerte": "#55524C",
    "texto": "#F2F0E9",
    "texto_suave": "#A8A398",
    "acento": "#7FA7D6",
    "acento_hover": "#9BBCE2",
    "acento_suave": "#2C3A4A",
    "sobre_acento": "#14202E",
    "terracota": "#E08B6D",
    "exito": "#5FBF8A",
    "aviso": "#F0A35E",
    "error": "#F07A7A",
    "sombra": "#000000",
}

FUENTE = "Segoe UI Variable Text"
FUENTE_RESPALDO = "Segoe UI"
FUENTE_TITULO = "Georgia"  # serif editorial para los títulos
FUENTE_MONO = "Cascadia Mono"

_oscuro = None


def es_oscuro():
    """True si Windows (o el sistema) está en modo oscuro."""
    if _oscuro is not None:
        return _oscuro
    app = QGuiApplication.instance()
    if app is None:
        return False
    return app.styleHints().colorScheme() == Qt.ColorScheme.Dark


def colores():
    return OSCURO if es_oscuro() else CLARO


def color(nombre):
    return QColor(colores()[nombre])


def hex_(nombre):
    """Para HTML dentro de etiquetas: ``<span style='color:{hex_("error")}'>``."""
    return colores()[nombre]


def fuente(puntos=10, peso=QFont.Weight.Normal):
    f = QFont(FUENTE)
    f.setFamilies([FUENTE, FUENTE_RESPALDO, "Noto Sans", "DejaVu Sans"])
    f.setPointSizeF(puntos)
    f.setWeight(peso)
    return f


def fuente_titulo(puntos=15):
    f = QFont(FUENTE_TITULO)
    f.setFamilies([FUENTE_TITULO, "Cambria", "Noto Serif", "DejaVu Serif"])
    f.setPointSizeF(puntos)
    return f


def fuente_mono(puntos=9.5):
    f = QFont(FUENTE_MONO)
    f.setFamilies([FUENTE_MONO, "Consolas", "DejaVu Sans Mono"])
    f.setStyleHint(QFont.StyleHint.Monospace)
    f.setPointSizeF(puntos)
    return f


def hoja_de_estilos(c=None):
    c = c or colores()
    return f"""
* {{ outline: none; }}
QWidget {{ color: {c['texto']}; font-size: 10pt; }}
QDialog, QWizard, QWizardPage, QMainWindow {{ background: {c['fondo']}; }}
QLabel {{ background: transparent; }}
QLabel[rol="titulo"] {{ font-family: "{FUENTE_TITULO}", "Cambria", serif; font-size: 17pt; }}
QLabel[rol="subtitulo"], QLabel[rol="suave"] {{ color: {c['texto_suave']}; }}
QLabel[rol="seccion"] {{ color: {c['texto_suave']}; font-size: 8.5pt; font-weight: 600; }}

QFrame[rol="tarjeta"], QGroupBox {{
    background: {c['superficie']}; border: 1px solid {c['borde']}; border-radius: 12px;
}}
QGroupBox {{ margin-top: 22px; padding: 14px 12px 10px 12px; font-weight: 600; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 4px; top: 0px; padding: 0 4px;
    color: {c['texto_suave']}; }}

QPushButton {{
    background: {c['superficie']}; color: {c['texto']};
    border: 1px solid {c['borde_fuerte']}; border-radius: 8px; padding: 6px 16px; min-height: 20px;
}}
QPushButton:hover {{ background: {c['superficie_2']}; }}
QPushButton:pressed {{ background: {c['borde']}; }}
QPushButton:disabled {{ color: {c['texto_suave']}; border-color: {c['borde']}; }}
QPushButton:default, QPushButton[rol="primario"] {{
    background: {c['acento']}; color: {c['sobre_acento']}; border-color: {c['acento']}; font-weight: 600;
}}
QPushButton:default:hover, QPushButton[rol="primario"]:hover {{
    background: {c['acento_hover']}; border-color: {c['acento_hover']};
}}
QPushButton:focus {{ border-color: {c['acento']}; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTimeEdit, QPlainTextEdit, QTextEdit {{
    background: {c['superficie']}; border: 1px solid {c['borde_fuerte']}; border-radius: 8px;
    padding: 5px 8px; selection-background-color: {c['acento']}; selection-color: {c['sobre_acento']};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTimeEdit:focus,
QPlainTextEdit:focus, QTextEdit:focus {{ border: 1px solid {c['acento']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {c['superficie']}; border: 1px solid {c['borde']};
    border-radius: 8px; selection-background-color: {c['acento_suave']}; selection-color: {c['texto']}; }}

QCheckBox, QRadioButton {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px; border: 1px solid {c['borde_fuerte']}; background: {c['superficie']};
}}
QCheckBox::indicator {{ border-radius: 5px; }}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {c['acento']}; border-color: {c['acento']};
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {c['acento']}; }}

QSlider::groove:horizontal {{ height: 4px; background: {c['borde']}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {c['acento']}; border-radius: 2px; }}
QSlider::handle:horizontal {{ width: 16px; height: 16px; margin: -6px 0; border-radius: 8px;
    background: {c['superficie']}; border: 2px solid {c['acento']}; }}

QListWidget, QTreeWidget, QTableWidget {{
    background: {c['superficie']}; border: 1px solid {c['borde']}; border-radius: 10px;
    alternate-background-color: {c['superficie_2']}; gridline-color: {c['borde']};
}}
QListWidget::item, QTreeWidget::item {{ padding: 4px 6px; border-radius: 6px; }}
QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected {{
    background: {c['acento_suave']}; color: {c['texto']};
}}
QListWidget#navegacion {{ background: transparent; border: none; }}
QListWidget#navegacion::item {{ padding: 8px 12px; margin: 1px 0; border-radius: 8px; }}
QListWidget#navegacion::item:hover {{ background: {c['superficie_2']}; }}
QListWidget#navegacion::item:selected {{ background: {c['superficie']}; color: {c['acento']};
    font-weight: 600; border: 1px solid {c['borde']}; }}
QHeaderView::section {{ background: {c['superficie_2']}; border: none;
    border-bottom: 1px solid {c['borde']}; padding: 5px 8px; font-weight: 600; }}

QProgressBar {{ background: {c['superficie_2']}; border: none; border-radius: 4px; height: 8px;
    text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {c['acento']}; border-radius: 4px; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle {{ background: {c['borde_fuerte']}; border-radius: 3px; min-height: 24px; min-width: 24px; }}
QScrollBar::handle:hover {{ background: {c['texto_suave']}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
    background: none; border: none; width: 0; height: 0; }}

QMenu {{ background: {c['superficie']}; border: 1px solid {c['borde']}; border-radius: 10px;
    padding: 6px; }}
QMenu::item {{ padding: 7px 28px 7px 12px; border-radius: 6px; background: transparent; }}
QMenu::item:selected {{ background: {c['acento_suave']}; color: {c['texto']}; }}
QMenu::item:disabled {{ color: {c['texto_suave']}; }}
QMenu::icon {{ padding-left: 10px; }}
QMenu::separator {{ height: 1px; background: {c['borde']}; margin: 5px 8px; }}
QMenu::section {{ color: {c['texto_suave']}; font-size: 8.5pt; font-weight: 600;
    padding: 6px 12px 3px 12px; background: transparent; }}

QToolTip {{ background: {c['texto']}; color: {c['fondo']}; border: none; border-radius: 6px;
    padding: 5px 8px; }}
QTabWidget::pane {{ border: 1px solid {c['borde']}; border-radius: 10px; background: {c['superficie']}; }}
QTabBar::tab {{ padding: 6px 14px; border: none; color: {c['texto_suave']}; }}
QTabBar::tab:selected {{ color: {c['acento']}; border-bottom: 2px solid {c['acento']}; }}
"""


def _paleta(c):
    p = QPalette()
    rol = QPalette.ColorRole
    for r, nombre in ((rol.Window, "fondo"), (rol.Base, "superficie"), (rol.AlternateBase, "superficie_2"),
                      (rol.Text, "texto"), (rol.WindowText, "texto"), (rol.Button, "superficie"),
                      (rol.ButtonText, "texto"), (rol.Highlight, "acento"),
                      (rol.HighlightedText, "sobre_acento"), (rol.ToolTipBase, "texto"),
                      (rol.ToolTipText, "fondo"), (rol.PlaceholderText, "texto_suave"),
                      (rol.Link, "acento")):
        p.setColor(r, QColor(c[nombre]))
    p.setColor(QPalette.ColorGroup.Disabled, rol.Text, QColor(c["texto_suave"]))
    p.setColor(QPalette.ColorGroup.Disabled, rol.ButtonText, QColor(c["texto_suave"]))
    return p


def aplicar(app, oscuro=None):
    """Estilo Fusion + paleta + hoja de estilos. ``oscuro`` fuerza el tema (capturas, pruebas)."""
    global _oscuro
    _oscuro = oscuro
    app.setStyle("Fusion")
    app.setFont(fuente(10))
    c = colores()
    app.setPalette(_paleta(c))
    app.setStyleSheet(hoja_de_estilos(c))


def seguir_al_sistema(app, al_cambiar=None):
    """Vuelve a aplicar el tema cuando Windows cambia entre claro y oscuro."""

    def cambio(_esquema):
        aplicar(app)
        if al_cambiar:
            al_cambiar()

    app.styleHints().colorSchemeChanged.connect(cambio)


# ---------- ventanas ----------

_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWA_SYSTEMBACKDROP_TYPE = 38


def aplicar_ventana(ventana):
    """Windows 11: esquinas redondeadas y barra de título en el tema actual.

    En otros sistemas (o Windows 10, que ignora estos atributos) no hace nada.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = int(ventana.winId())
        dwm = ctypes.windll.dwmapi

        def poner(atributo, valor):
            v = ctypes.c_int(valor)
            dwm.DwmSetWindowAttribute(hwnd, atributo, ctypes.byref(v), ctypes.sizeof(v))

        poner(_DWMWA_USE_IMMERSIVE_DARK_MODE, 1 if es_oscuro() else 0)
        poner(_DWMWA_WINDOW_CORNER_PREFERENCE, 2)  # redondeadas
    except Exception:
        pass


def animar_entrada(ventana, desplazamiento=10, ms=170):
    """Aparece con un fundido y un leve ascenso. Una sola vez, al abrir: no cuesta nada después."""
    final = ventana.pos()
    ventana.setWindowOpacity(0.0)
    opacidad = QPropertyAnimation(ventana, b"windowOpacity", ventana)
    opacidad.setDuration(ms)
    opacidad.setStartValue(0.0)
    opacidad.setEndValue(1.0)
    opacidad.setEasingCurve(QEasingCurve.Type.OutCubic)
    opacidad.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    if desplazamiento:
        mover = QPropertyAnimation(ventana, b"pos", ventana)
        mover.setDuration(ms + 40)
        mover.setStartValue(final + QPoint(0, desplazamiento))
        mover.setEndValue(final)
        mover.setEasingCurve(QEasingCurve.Type.OutCubic)
        mover.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


def preparar_dialogo(dialogo):
    """Lo que todo diálogo de Pandex hace al mostrarse: barra de Windows 11 y entrada suave."""
    aplicar_ventana(dialogo)
    animar_entrada(dialogo, desplazamiento=0, ms=140)
