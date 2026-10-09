"""Genera las capturas del README (``docs/img/``) sin abrir ninguna ventana real.

    .venv\\Scripts\\python.exe herramientas/capturas.py

Usa la plataforma «offscreen» de Qt: dibuja la mascota, el globo, el menú y las
ventanas tal como se ven en la app, en tema claro y oscuro. No toca tu config.json
(usa una configuración temporal) ni se conecta a internet.
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PANDEX_DATOS", tempfile.mkdtemp(prefix="pandex-capturas-"))

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from PyQt6.QtCore import QPoint  # noqa: E402
from PyQt6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

DESTINO = RAIZ / "docs" / "img"


def _config():
    from pandex.config import Config

    return Config(Path(tempfile.mkdtemp()) / "config.json")


def _lienzo(ancho, alto, oscuro):
    img = QImage(ancho * 2, alto * 2, QImage.Format.Format_ARGB32_Premultiplied)
    img.setDevicePixelRatio(2)
    img.fill(QColor("#1F1E1D" if oscuro else "#F0EEE6"))
    return img


def _pegar(painter, widget, x, y):
    widget.ensurePolished()
    painter.drawPixmap(QPoint(x, y), widget.grab())


def mascota(oscuro):
    """Los cuatro estados de Rusty, cada uno con su globo."""
    from pandex.ui import personajes
    from pandex.ui.globo import Globo

    frases = (("idle", "¿Qué tal? Clic derecho para el menú.", "info", None),
              ("trabajando", "Voy 12 de 30…", "progreso", (12, 30)),
              ("feliz", "✓ 3 nuevo(s): Cálculo 2, Física 1 · 8 s", "exito", None),
              ("error", "No pude conectarme con Canvas.", "error", None))
    ancho, alto = 4 * 250 + 40, 330
    img = _lienzo(ancho, alto, oscuro)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    for i, (estado, texto, tipo, avance) in enumerate(frases):
        x = 20 + i * 250
        globo = Globo()
        if avance:
            globo.progreso(texto, *avance)
        else:
            globo.decir(texto, 5, tipo)
        globo.colocar(0, 0, globo.width() // 2)
        _pegar(p, globo, x + (250 - globo.width()) // 2, 150 - globo.height())
        pix = personajes.imagen("rusty", estado, 147, 2)
        p.drawPixmap(x + (250 - round(pix.width() / 2)) // 2, 152, pix)
        globo.ocultar_ya()
        globo.deleteLater()
    p.end()
    return img


def menu(app_cfg, oscuro):
    from types import SimpleNamespace

    from pandex import tareas
    from pandex.app import PandexApp

    nada = lambda *a: None  # noqa: E731
    # lo justo para dibujar el menú, sin bandeja, reloj ni ventanas
    falsa = SimpleNamespace(
        tareas=tareas.descubrir(), _nueva=None, ejecutor=None,
        mascota=SimpleNamespace(isVisible=lambda: True, hide=nada),
        _configurar=nada, _abrir_configuracion=nada, _abrir_registro=nada, _recargar_tareas=nada,
        buscar_actualizaciones=nada, actualizar_ya=nada, _mostrar_mascota=nada, salir=nada,
    )
    m = PandexApp._construir_menu(falsa, None)
    m.adjustSize()
    img = _lienzo(m.width() + 40, m.height() + 40, oscuro)
    p = QPainter(img)
    _pegar(p, m, 20, 20)
    p.end()
    return img


def configuracion(cfg, oscuro):
    from pandex import tareas
    from pandex.ui.configuracion import DialogoConfiguracion

    dlg = DialogoConfiguracion(cfg, tareas.descubrir(), al_buscar_actualizaciones=lambda: None)
    dlg.resize(720, 540)
    return dlg.grab().toImage()


def actualizacion(oscuro):
    from pandex import actualizar
    from pandex.ui import actualizacion as ui

    actualizar.buscar = lambda: {
        "local": "2.0.0", "remota": "2.1.0", "hay_nueva": True,
        "novedades": "## 2.1.0\n\n- Panda nuevo, nítido a cualquier tamaño\n"
                     "- Interfaz renovada con modo oscuro\n- Buscar actualizaciones desde el menú",
    }
    dlg = ui.DialogoActualizacion(lambda: None)
    dlg._hilo.wait()
    QApplication.processEvents()
    dlg.resize(500, 380)
    return dlg.grab().toImage()


def social():
    """Vista previa para redes (1280×640): súbela en GitHub → Settings → Social preview."""
    from PyQt6.QtCore import QRectF, Qt
    from PyQt6.QtGui import QFont

    from pandex.ui import logo, personajes, tema

    img = QImage(1280, 640, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor(tema.CLARO["fondo"]))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.drawPixmap(96, 120, logo.pixmap(88))
    p.setPen(QColor(tema.CLARO["texto"]))
    p.setFont(tema.fuente_titulo(54))
    p.drawText(QRectF(96, 230, 700, 100), int(Qt.AlignmentFlag.AlignLeft), "Pandex")
    p.setPen(QColor(tema.CLARO["texto_suave"]))
    f = tema.fuente(20)
    f.setWeight(QFont.Weight.Normal)
    p.setFont(f)
    p.drawText(QRectF(96, 340, 640, 160), int(Qt.TextFlag.TextWordWrap),
               "Un panda rojo en tu escritorio que sincroniza Canvas y convierte tu material "
               "a Markdown. Local, gratis y sin IA.")
    pix = personajes.imagen("rusty", "feliz", 420)
    p.drawPixmap(1280 - pix.width() - 90, (640 - pix.height()) // 2, pix)
    p.end()
    return img


def main():
    from pandex.ui import tema

    app = QApplication(sys.argv)
    DESTINO.mkdir(parents=True, exist_ok=True)
    cfg = _config()
    for oscuro in (False, True):
        tema.aplicar(app, oscuro=oscuro)
        sufijo = "-oscuro" if oscuro else ""
        for nombre, img in (("mascota", mascota(oscuro)), ("menu", menu(cfg, oscuro)),
                            ("configuracion", configuracion(cfg, oscuro)),
                            ("actualizar", actualizacion(oscuro))):
            ruta = DESTINO / f"{nombre}{sufijo}.png"
            img.save(str(ruta))
            print(ruta.relative_to(RAIZ))
    tema.aplicar(app, oscuro=False)
    social().save(str(RAIZ / "assets" / "social.png"))
    print("assets/social.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
