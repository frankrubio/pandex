# Pruebas

Cómo se prueba Pandex, qué cubre cada archivo de `tests/` y cómo convertir un escenario de
una spec en una prueba. Las pruebas son la forma de comprobar que un requisito se cumple:
si no hay prueba, el requisito no está terminado.

## Correrlas

```bash
# todas (Linux)
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -t .
# todas (Windows)
.venv\Scripts\python.exe -m unittest discover -s tests -t .

# un archivo, una clase o una sola prueba
.venv/bin/python -m unittest tests.test_principios
.venv/bin/python -m unittest tests.test_principios.Tareas
.venv/bin/python -m unittest tests.test_principios.Tareas.test_contrato

# ¿qué prueba cuida el requisito REN-04?
grep -rn "REN-04" tests/
```

Antes de abrir un PR: toda la suite en verde y `main.py --test` abre y se cierra solo.

## Reglas

1. **Sin internet.** Canvas, GitHub y PyPI se simulan (`tests/apoyo.CanvasFalso`,
   `unittest.mock`). Una prueba que necesita red no entra a la suite.
2. **Sin tocar los datos reales.** `tests/__init__.py` apunta `PANDEX_DATOS` a una carpeta
   temporal y Qt a una pantalla invisible **antes** de importar Pandex. Cada prueba que escribe
   archivos usa su propia carpeta temporal y la borra en `tearDown`.
3. **Sin esperas a ciegas.** Nada de `time.sleep` para «darle tiempo»: se espera una señal o
   una condición con tiempo límite.
4. **Nombres que se leen como una frase**, en español: `test_un_archivo_a_medias_nunca_llega_a_tu_carpeta`.
5. **El docstring cita el requisito:** `"""REN-04: siempre hay al menos 4 descargas en curso."""`.
6. **Una prueba, un comportamiento.** Si falla, el nombre ya dice qué se rompió.
7. **Se prueban reglas, no píxeles.** En la interfaz: colores del tema, nombres de botones,
   contraste, orden de tabulación; no posiciones exactas.
8. **Lo que depende del sistema** se prueba en los dos (la CI corre en Windows y Ubuntu). Si
   una prueba solo tiene sentido en uno, se salta en el otro con
   `@unittest.skipUnless(rutas.WINDOWS, "solo Windows")` y un motivo.
9. **Sin depender del idioma.** Qt adopta el idioma del sistema al crear la app, así que
   `strftime("%a")` da `lun` en una PC en español: compara números (`weekday()`, `day`), no
   textos. La CI de Ubuntu corre en español (`es_PE.UTF-8`) para notarlo.
10. **Lo opcional se salta si no está instalado.** Las pruebas de una función opcional llevan
    `@unittest.skipUnless(extras.instalado("markdown"), "…")`, para que la suite pase en un
    Pandex sin ella. La CI instala todo, así que ahí siempre corren.

## Qué cubre cada archivo

| Archivo | Qué cubre |
|---|---|
| `test_principios.py` | Principios verificables con el repositorio: privacidad (`.gitignore`, archivos personales), dependencias fijas y por sistema, contrato de tareas, mapa de módulos, nombres de archivo, specs completas. |
| `test_nucleo.py` | `config.json` (valores por defecto) y descubrimiento de tareas. |
| `test_canvas_piezas.py` | Piezas de Sincronizar Canvas por separado: nombres, destinos, índice de duplicados, estructura, sesión. |
| `test_canvas_sincronizar.py` | Sincronización de punta a punta con Canvas falso. |
| `test_canvas_adoptar.py` | Usar una carpeta existente: emparejar, estilo, reordenar y deshacer. |
| `test_asistente.py` | El asistente de Canvas manejado por código. |
| `test_markdown.py` | Convertir a Markdown: clasificador, nombres de los `.md` y una conversión real. |
| `test_comprimir.py` | Comprimir carpeta: el `.zip` trae todo, no pisa otro y aligera PDF con Ghostscript. |
| `test_actualizar.py` | Versiones y aplicar una actualización por ZIP sin internet ni tocar tus datos. |
| `test_a_la_hora.py` | Ponerse al día si la PC estuvo apagada y el despertador del sistema. |
| `test_linux.py` | Lo que cambia en Linux: accesos `.desktop`, Firefox para Canvas y OCR con Tesseract. |
| `test_onedrive.py` | OneDrive en Linux con rclone: cuentas, montar y no escribir si no está montado. |
| `test_ui.py` | La interfaz se construye y se pinta sin errores: mascota, personajes, logo y ventanas. |

Archivos que piden las specs y aún no existen: `test_rendimiento.py` (001), `test_extras.py`
(002), `test_residuos.py` (003), `test_privacidad.py` (004), `test_interfaz.py` (005),
`test_paridad.py` (006), `test_herramientas.py` (007). Ver [specs/tablero.md](../specs/tablero.md).

## Tipos de prueba

| Tipo | Ejemplo | Dónde corre |
|---|---|---|
| Unidad (función pura) | `nombres.semana_de("Week 07") == 7` | CI, siempre |
| Punta a punta con Canvas falso | sincronizar 3 cursos y revisar el árbol creado | CI, siempre |
| Interfaz (pantalla invisible) | Configuración tiene un solo botón principal | CI, siempre |
| Repositorio | `config.json` no está versionado | CI, siempre |
| Presupuesto con latencia simulada | tiempo propio ≤ 10 s con 150 ms por pedido | CI, siempre |
| Peso | instalación completa ≤ 600 MB | CI, job `peso` |
| Instaladores | `instalar.sh` sin preguntas + `main.py --test` | CI, job `instaladores` |
| Manual | 5 sincronizaciones reales con Canvas | PC de referencia, antes de publicar una versión |

## De escenario a prueba

Cada escenario de una spec (*Dado / Cuando / Entonces*) se vuelve una prueba con la misma
estructura. Ejemplo con el escenario REN-02 de `specs/001_rendimiento_sincronizar/spec.md`:

> **REN-02 · Sin novedades**
> - *Dado* que todo ya está en disco y el historial lo sabe
> - *Cuando* sincroniza
> - *Entonces* el globo dice `✓ Todo al día · … · N s` con N ≤ 6.

```python
class Presupuesto(apoyo.ConCarpetaTemporal):
    def test_sin_novedades_total(self):
        """REN-02: sin novedades, el total es ≤ 6 s (Canvas falso con 150 ms por pedido)."""
        # Dado: 10 cursos ya sincronizados una vez
        CanvasFalso.reiniciar(*canvas_de_ejemplo(cursos=10, archivos=300))
        CanvasFalso.latencia = 0.15
        self.sincronizar(PARAMS)

        # Cuando: se sincroniza otra vez
        inicio = time.monotonic()
        resultado, ctx = self.sincronizar(PARAMS)
        segundos = time.monotonic() - inicio

        # Entonces
        self.assertTrue(resultado["ok"])
        self.assertIn("Todo al día", resultado["resumen"])
        self.assertLessEqual(segundos, 6)
```

(`canvas_de_ejemplo`, `PARAMS` y `CanvasFalso.latencia` todavía no existen: los crean las
tareas T001.1 y T001.4.)

Pasos al escribirla:

1. Escríbela **antes** del cambio y córrela: tiene que **fallar**, y por el motivo que el
   requisito describe (no por un error de importación o una errata).
2. Haz el cambio mínimo hasta que pase.
3. Corre toda la suite.

## Pruebas que documentan un hueco

Si una prueba nueva falla por un problema real que **otra** tarea va a arreglar, se marca con
`@unittest.expectedFailure` y un comentario con esa tarea (`# T003.3`). Cuando la tarea se
cierra, se quita el decorador: si se olvida, `unittest` lo reporta como «unexpected success» y
la CI falla. Nunca se usa `skip` para esconder un error.

## Antes de publicar una versión (manual)

En Windows **y** en Linux, con una cuenta real de Canvas:

- [ ] Instalar desde cero con y sin «Convertir a Markdown».
- [ ] Primera vez: el asistente solo pide la URL e iniciar sesión.
- [ ] Sincronizar 5 veces sin novedades: anotar la mediana (≤ 6 s).
- [ ] Borrar `historial_canvas.json` y sincronizar: anotar el tiempo propio (≤ 10 s).
- [ ] Medir el peso con `herramientas/medir_peso.py` (≤ 600 MB).
- [ ] Buscar actualizaciones desde la versión anterior.
- [ ] Desinstalar y comprobar que no queda nada fuera de la carpeta del proyecto.
