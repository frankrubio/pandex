"""Convertir a Markdown: PDF, Word, PowerPoint, Excel y más a .md, 100 % local y sin IA.

La lógica vive en ``pandex/markdown/``; este archivo solo la conecta con Pandex.
"""

from pandex.markdown.archivos import raices
from pandex.markdown.clasificador import Clasificador
from pandex.markdown.lote import convertir


class Task:
    id = "convertir_md"
    nombre = "Convertir a Markdown"
    icono = "documento"
    descripcion = "Convierte PDF, Word, PowerPoint, Excel y más a .md, sin IA"
    schedule = None

    def preparar(self, ctx):
        from pandex.markdown.navegador import Navegador  # Qt: solo al abrirlo

        dialogo = Navegador(raices(), ctx.params.get("ultima_carpeta"),
                            Clasificador(ctx.params.get("clasificacion")))
        dialogo.raise_()
        dialogo.activateWindow()
        if not dialogo.exec() or not dialogo.resultado:
            return None
        ctx.params["ultima_carpeta"] = dialogo.resultado["carpeta"]
        ctx.guardar()
        return dialogo.resultado

    def run(self, ctx):
        return convertir(ctx)
