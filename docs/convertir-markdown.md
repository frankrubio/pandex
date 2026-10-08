# Convertir a Markdown

Convierte PDF, Word, PowerPoint, Excel y más a `.md`, 100 % en tu computadora y sin IA.
El código vive en `pandex/markdown/`; `tasks/convertir_md.py` solo lo conecta.

| Módulo | Qué hace |
|---|---|
| `clasificador.py` | ¿Es material de estudio? Reglas fijas y legibles. |
| `archivos.py` | Qué se puede convertir, dónde va cada `.md`, recorrer carpetas, escribir sin dejar archivos a medias. |
| `conversion.py` | El motor: MarkItDown local y el OCR de Windows. |
| `lote.py` | Una conversión completa: revisar, convertir, verificar e informar. |
| `navegador.py` | La ventana para elegir archivos o carpetas con el teclado. |

## Uso

**Clic derecho → Convertir a Markdown.** Se abre un navegador con los mismos íconos de tu
Explorador. Eliges una carpeta o marcas archivos y Pandex trabaja en segundo plano; al
terminar abre un resumen.

| Botón | Qué convierte |
|---|---|
| **Material de estudio** *(`Ctrl+M`, el predeterminado)* | Solo clases, guías, resúmenes y lecturas. Deja fuera actividades previas, tareas, evaluaciones, preguías, HTML… |
| **Todos** *(`Ctrl+T`)* | Todo lo convertible de la carpeta, sin filtrar. |

Los dos respetan *Incluir subcarpetas* y *Forzar reconversión*, y muestran cuántos archivos
entran. En la lista, lo que no es material de estudio sale **en gris con su motivo**
(`AP4-Sem5.pdf · no: actividad previa`). Si **marcas un archivo a mano**, se convierte siempre.

### Teclado

| Tecla | Qué hace |
|---|---|
| `1` `2` `3` | En el inicio: OneDrive institucional, Descargas, Documentos |
| **Enter** | Entrar a una carpeta · marcar/desmarcar un archivo |
| **Espacio** | Marcar y bajar al siguiente |
| **Retroceso** | Subir un nivel |
| Escribir letras | Salta al nombre que empieza así |
| **Ctrl+A** | Marcar el material de estudio de la carpeta (otra vez: desmarcar) |
| **Ctrl+Enter** | Convertir los marcados |
| **Ctrl+M** / **Ctrl+T** | Convertir el material de estudio / todo de esta carpeta |
| **Esc** | Cancelar |

Las migas de arriba (`Inicio › OneDrive › … › Sem 6`) son clicables, la primera opción del
inicio es la última carpeta que usaste, y lo marcado se conserva al cambiar de carpeta.

## Cómo decide qué es material de estudio

Reglas fijas, en este orden; **gana la primera que aplica**:

| # | Mira… | Si encuentra… | Entonces |
|---|---|---|---|
| 1 | el formato | HTML, CSV, JSON, XML, imágenes | **no** (solo PDF, Word, PowerPoint, Excel, EPUB) |
| 2 | las carpetas | `Trabajos…`, `Entregas…` | **no**: es trabajo tuyo |
| — | tus palabras | `excluir_palabras` / `incluir_palabras` de la configuración | **no** / **sí** |
| 3 | el nombre | `AP`, `TA`, `ED`, `EA`, `PC`, `EP`, `EF`, actividad previa, tarea, enunciado, evaluación, examen, preguía, *ejercicios*, plantilla, formato, sílabo, horario, cronograma, consentimiento, rúbrica | **no** |
| 4 | el nombre | clase, sesión, teoría, semana, capítulo, presentación, guía, resumen, toolkit, infografía, apuntes, lectura, fuente, libro, glosario, o un título en inglés con guiones bajos como los de NotebookLM (`Trigonometry_Toolkit`) | **sí** |
| 5 | las carpetas | `Actividades`, `Tareas`, `Evaluaciones`, `Información del curso`, `Syllabus` | **no** |
| 6 | — | nada de lo anterior | **sí** |

El nombre se lee normalizado (sin tildes, en minúsculas, los signos como espacios) y las siglas
se buscan **como palabra suelta**: `AP4` es actividad previa, `apuntes` no. Ejemplos:

- `Sem6_Guía de estudio` está en *Actividades*, pero dice **guía** (la regla 4 va antes que la 5) → **sí**.
- `PreGuía de ejercicios 6` dice «guía», pero antes dice **preguía** (regla 3) → **no**.
- `Teoría y ejercicios de límites` tiene ejercicios **y** teoría → **sí**; `Ejercicios_Conjuntos_3` → **no**.

## Qué convierte y cómo nombra los .md

`.pdf` `.docx` `.pptx` `.xlsx` `.xls` `.html` `.htm` `.csv` `.json` `.xml` `.epub` `.png` `.jpg` `.jpeg`

- Cada `.md` queda **junto al original, con el mismo nombre**. Si en la carpeta está la misma
  clase en `.pptx` y en `.pdf`, salen `Clase 3 (pptx).md` y `Clase 3 (pdf).md`.
- **Audio y video no se tocan:** MarkItDown solo los entiende transcribiéndolos por internet.
  El resumen los lista como *tipo no soportado sin IA*.
- Si el `.md` ya existe, **se salta**. *Forzar reconversión* los rehace, pero **solo los que
  hizo Pandex**: llevan en la primera línea una marca
  (`<!-- Pandex: convertido desde «Clase 6.pdf» con MarkItDown -->`). Un `.md` escrito por ti
  nunca se pisa.
- El `.md` se escribe primero fuera de tu carpeta y se mueve al final: OneDrive nunca
  sincroniza uno a medias.

## PDFs y diapositivas que son solo imagen

Si MarkItDown saca menos de 200 caracteres de un PDF o una imagen, Pandex prueba con el
**OCR que trae Windows** (`Windows.Media.Ocr`): viene con el sistema, corre en tu PC, sin
internet ni costo. Es solo un respaldo: los PDFs con texto normal no pasan por ahí. Rescata,
por ejemplo, los PowerPoint exportados a PDF como imágenes.

Lo que siga saliendo corto se lista como **posible contenido-imagen, revisar**. Los `.md`
hechos con OCR lo dicen en su primera línea: revísalos, el OCR a veces confunde letras.

## Cómo garantiza «cero IA»

- **MarkItDown sin plugins** (`enable_plugins=False`), sin cliente de LLM y sin Azure.
- **El tipo se decide por la extensión.** Por defecto MarkItDown pasa cada archivo por
  *Magika* (una red neuronal) para adivinar qué es; Pandex reemplaza ese paso y nunca se ejecuta.
- **La codificación** de CSV/HTML/JSON/XML sale de reglas fijas: marca BOM → UTF-8 →
  `cp1252` (la de Excel en Windows en español). La detección estadística rompía la Ñ.

## Configuración

En `config.json → tareas → convertir_md`:

```jsonc
"convertir_md": {
  "umbral_contenido_imagen": 200,  // por debajo: probar OCR y marcar para revisar
  "ocr_local": true,               // false = nunca usar el OCR de Windows
  "ocr_max_paginas": 60,           // tope por PDF
  "ultima_carpeta": "…",           // se guarda sola
  "clasificacion": {
    "formatos_estudio": [".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".epub"],
    "excluir_palabras": ["borrador"],     // si el nombre lo tiene: NO es material
    "incluir_palabras": ["ejercicios"],   // si el nombre lo tiene: SÍ (manda sobre las reglas 3-6)
    "excluir_carpetas": ["Borradores"]    // carpetas enteras fuera
  }
}
```

El recorrido nunca entra en carpetas ocultas (`.git`, `.venv`…), `node_modules`,
`__pycache__`, `site-packages`, `venv` ni `env`, ni toca los `~$archivo` que deja Office abiertos.
