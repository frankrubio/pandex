"""Sincronizar Canvas: baja el material nuevo de tus cursos y lo ordena en carpetas.

La lógica vive en ``pandex/canvas/``; este archivo solo la conecta con Pandex.
La primera vez abre el asistente de configuración (``pandex/canvas/asistente.py``).
"""

from pandex.canvas.sincronizar import Sincronizacion, esta_configurado


class Task:
    id = "sync_canvas"
    nombre = "Sincronizar Canvas"
    descripcion = "Baja el material nuevo de Canvas y lo ordena en tu carpeta"
    schedule = None  # el asistente puede poner uno (p. ej. todos los días a las 19:00)
    configurar_texto = "Configurar Canvas…"

    def necesita_configurar(self, params):
        return not esta_configurado(params)

    def configurar(self, ctx):
        from pandex.canvas.asistente import AsistenteCanvas  # Qt: solo al abrirlo

        asistente = AsistenteCanvas(ctx.params, ctx.guardar)
        asistente.raise_()
        asistente.activateWindow()
        return asistente.entrada if asistente.exec() else None

    def preparar(self, ctx):
        # sin configurar, «Sincronizar Canvas» abre el asistente
        return {} if esta_configurado(ctx.params) else self.configurar(ctx)

    def run(self, ctx):
        return Sincronizacion(ctx).ejecutar()
