# 015 · Plan

## Enfoque

1. **Módulos completos y enlaces dentro de páginas/tareas (`cliente.py`, `estructura.py`, `sincronizar.py`):**
   - En `Canvas.modulos`, consultar `items_url` también cuando `len(items) < items_count`.
   - En `Sincronizacion._candidatos`, completar el cuerpo (`body`) de los ítems `Page` y `Assignment` publicados en los módulos (cacheando en `Historial` para no repetir llamadas en corridas sin cambios) y extraer de su HTML los enlaces a archivos de Canvas y a Google Drive.
   - En `estructura._MITAD` y `emparejar_cursos`, aceptar números de sección con decimales/letras (`1.01`, `2A`) y cursos combinados (`Teo. 1 - Lab. 11`).
2. **Desambiguación de duplicados y opción de repetidos por semana (`destinos.py`, `historial.py`, `sincronizar.py`, `asistente.py`, `ui/configuracion.py`):**
   - En `IndiceCurso.buscar`, no considerar duplicado por «mismo nombre» un archivo que está en otra carpeta (`previo.parent != destino`) cuando ambos tamaños se conocen y son distintos.
   - Guardar en `IndiceCurso` el `file_id` de lo reservado en la misma corrida para que dos archivos distintos con igual nombre en la misma carpeta se bajen como `(v2)`.
   - Añadir la opción `repetidos_cada_semana` (`False` por defecto: «Descargar solo una vez»; `True`: «Descargar siempre (en cada semana)») en el asistente (`PaginaDescarga`) y en `Configuración → Tareas → Sincronizar Canvas`. Con `True`, `candidatos_de`, `Historial` e `IndiceCurso` acotan la deduplicación a la carpeta destino / semana actual.
3. **Material adicional (`destinos.py`, `sincronizar.py`, `markdown/clasificador.py`):**
   - Reconocer todas las variantes de «Material adicional» / «Material complementario» / «Additional Material» en `destinos.py` aunque no figuren en el mapa `secciones` escrito a mano.
   - Descargar por defecto los módulos sin número de semana salvo `otros_modulos: false` explícito, y permitir archivos sin subencabezado dentro de una semana en modo clásico.
4. **Google Drive con soporte de cuenta institucional (`canvas/drive.py`, `red.py`, `sesion.py`):**
   - Crear `pandex/canvas/drive.py` para identificar enlaces de `drive.google.com` y `docs.google.com`, construir la URL de descarga o exportación (PDF/DOCX/PPTX/XLSX), resolver la confirmación de archivos grandes y extraer el nombre real de `Content-Disposition` / `Content-Type`.
   - Si Google Drive devuelve acceso denegado o login (porque la cuenta predeterminada del navegador no es la institucional), probar primero `authuser=0, 1, 2, 3` con las cookies de Google del perfil/atajo; si sigue sin permiso, abrir el navegador de Pandex en el enlace de Drive para que el usuario cambie a su cuenta institucional, guardar las cookies y el `authuser` en `DATOS/sesion_drive.json` (`0600`) y completar la descarga.

## Principios

- **P1 (Privacidad):** `sesion_drive.json` vive en `DATOS` con permisos `0600`, sus cookies pasan por `log.ocultar`, «Olvidar mi sesión» lo borra y `red.GOOGLE_DRIVE` se declara en `pandex/red.py`, `specs/004_privacidad_y_datos/spec.md` y `docs/privacidad.md`.
- **P4 (Nada destructivo):** solo crea archivos nuevos; respeta `(v2)` cuando dos archivos distintos coinciden en la misma carpeta.
- **P5 (Liviano):** cero dependencias nuevas (usa `requests` y el navegador de `navegador.py`).
- **P6 (Rápido):** `Historial` recuerda las rutas por semana y las páginas ya leídas para mantener 0 consultas en corridas sin novedades.

## Archivos que se tocan

| Archivo | Cambio |
|---|---|
| `pandex/canvas/drive.py` | Nuevo módulo: detección, descarga, confirmación y sesión institucional de Google Drive. |
| `pandex/red.py` | Añadir `GOOGLE_DRIVE` a los hosts permitidos. |
| `pandex/canvas/cliente.py` | Pedir `items_url` cuando `len(items) < items_count`; métodos `pagina()` y `tarea_canvas()`. |
| `pandex/canvas/estructura.py` | Ampliar `Item`, `items_de_modulos` (`ExternalUrl`, `Page`, `Assignment`), `_MITAD` y `emparejar_cursos`. |
| `pandex/canvas/destinos.py` | Reconocer «Material adicional», archivos sin subencabezado y alcance de `IndiceCurso.buscar` por carpeta/semana. |
| `pandex/canvas/historial.py` | Soportar múltiples rutas por `file_id` (para repetidos cada semana) y caché de páginas/metadatos. |
| `pandex/canvas/sincronizar.py` | Integrar `repetidos_cada_semana`, páginas/tareas, módulos sin semana por defecto y descargas de Google Drive. |
| `pandex/canvas/sesion.py` | Borrar también `sesion_drive.json` en `olvidar()`. |
| `pandex/canvas/asistente.py` | Selector de «Archivos repetidos cada semana» en `PaginaDescarga`. |
| `pandex/ui/configuracion.py` | Selector de «Archivos repetidos cada semana» en `Sincronizar Canvas`. |
| `pandex/markdown/clasificador.py` | Reconocer material adicional/complementario como material de estudio. |
| `tests/test_descargas_canvas.py` | Pruebas de `DES-01` a `DES-06`. |
| `docs/arquitectura.md`, `docs/sincronizar-canvas.md`, `docs/privacidad.md`, `specs/004_privacidad_y_datos/spec.md` | Documentación actualizada. |

## Medición

Toda la suite de pruebas (`QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -t . -v`) y `main.py --test`.

## Riesgos

| Riesgo | Qué se hace |
|---|---|
| Varios hilos intentando abrir el navegador para Google Drive a la vez | Proteger el inicio de sesión de Drive con un `threading.Lock()` para que solo el primer hilo abra la ventana y los demás reutilicen la sesión. |
| Consultas repetidas a páginas en cada sincronización | Guardar en `Historial` los enlaces extraídos de cada página/tarea para no volver a pedirla si sus archivos ya están en disco. |
