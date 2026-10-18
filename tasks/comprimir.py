"""Comprimir carpeta: un .zip listo para subir a un drive, con PDFs más livianos si quieres.

La lógica vive en ``pandex/comprimir.py``; este archivo solo la conecta con Pandex.
"""

from pathlib import Path

from pandex import comprimir


class Task:
    id = "comprimir"
    nombre = "Comprimir carpeta"
    icono = "carpeta"
    descripcion = "Crea un .zip de una carpeta para subirla a un drive; puede aligerar los PDF"
    schedule = None
    programable = False  # cada vez eliges qué carpeta

    def preparar(self, ctx):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        inicio = ctx.params.get("ultima_carpeta") or ctx.config.get("tareas", {}).get(
            "sync_canvas", {}).get("destino") or str(Path.home())
        carpeta = QFileDialog.getExistingDirectory(None, "¿Qué carpeta comprimo?", inicio)
        if not carpeta:
            return None
        pdfs = False
        if comprimir.ghostscript():
            pdfs = QMessageBox.question(
                None, "Comprimir carpeta",
                "¿Aligero también los PDF?\n\nEs lo que más reduce el peso (sobre todo los escaneados). "
                "Las imágenes quedan a calidad de pantalla; tus archivos originales no se tocan.",
            ) == QMessageBox.StandardButton.Yes
        ctx.params["ultima_carpeta"] = str(Path(carpeta).parent)
        ctx.guardar()
        return {"carpeta": carpeta, "pdfs": pdfs}

    def run(self, ctx):
        entrada = ctx.entrada or {}
        if not entrada.get("carpeta"):
            return {"ok": False, "resumen": "Elige una carpeta desde el menú."}
        r = comprimir.comprimir(entrada["carpeta"], pdfs=entrada.get("pdfs", False), progreso=ctx.progreso)
        ahorro = 100 - (r["despues"] * 100 // r["antes"]) if r["antes"] else 0
        resumen = (f"✓ {r['zip'].name}: {comprimir.tamano(r['antes'])} → {comprimir.tamano(r['despues'])} "
                   f"({ahorro} % menos)")
        if r["pdfs"]:
            resumen += f" · {r['pdfs']} PDF aligerado(s)"
        elif not comprimir.ghostscript():
            resumen += " · instala Ghostscript para aligerar los PDF"
        return {"ok": True, "resumen": resumen, "carpeta": str(r["zip"].parent)}
