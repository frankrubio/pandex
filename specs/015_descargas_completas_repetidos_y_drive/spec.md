# 015 · Descargas completas, archivos repetidos por semana, material adicional y Google Drive

> Estado: terminada  ·  Prefijo de requisitos: `DES`
> Principios que toca: P1 (privacidad), P4 (nada destructivo), P5 (liviano), P6 (rápido), P7, P8

## Por qué

En cursos como *Programación I* y *Fundamentos del Cálculo* se reportaron cuatro problemas al
sincronizar Canvas:

1. **No se descargaba todo el material:**
   - cuando un módulo tenía más de 10 ítems, Canvas devolvía la lista truncada en línea y Pandex no
     consultaba `items_url`;
   - dos archivos distintos de semanas distintas con el mismo nombre genérico (`Ejercicios.pdf`,
     `Guia.pdf`, `main.py`, `Laboratorio.pdf`) se confundían por «mismo nombre» y solo se bajaba el
     de la primera semana;
   - archivos y enlaces publicados dentro de páginas (`Page`), tareas (`Assignment`) o enlaces
     (`ExternalUrl`) de los módulos no se leían;
   - cursos cuya sección tenía decimales (`Laboratorio 1.01`) o venían combinados (`Teo. 1 - Lab. 11`)
     no se emparejaban bien.
2. **Archivos repetidos cada semana:** en cursos como *Fundamentos del Cálculo* se publica el mismo
   PDF de la AP todas las semanas; faltaba poder elegir en el asistente y en Configuración si
   descargarlo **solo una vez** o **siempre (en cada semana)**.
3. **Material adicional:** los subencabezados o módulos de «Material adicional» / «Material
   complementario» (o los archivos sin subencabezado dentro de una semana) se descartaban en
   configuraciones clásicas cuyo mapa `secciones` no los incluía.
4. **Enlaces a Google Drive:** varios docentes suben material como enlaces a Google Drive
   (`drive.google.com`, `docs.google.com`), que además a veces rechazan el acceso cuando la cuenta
   predeterminada del navegador es la personal y requieren cambiar a la cuenta institucional.

## Qué existe hoy

- `pandex/canvas/cliente.py`: `Canvas.modulos` solo pedía `items_url` si `"items" not in modulo`.
- `pandex/canvas/estructura.py`: `items_de_modulos` solo leía ítems `type == "File"` con `content_id`.
- `pandex/canvas/destinos.py`: `IndiceCurso.buscar` comparaba nombres en todo el curso sin distinguir
  archivos de distinto tamaño en carpetas/semanas diferentes; `carpeta_destino` descartaba secciones
  fuera del mapa en modo clásico.
- `pandex/canvas/sincronizar.py`: `candidatos_de` descartaba cualquier `file_id` repetido en otro
  módulo y omitía módulos sin semana cuando `otros_modulos` no estaba escrito.
- `pandex/canvas/sesion.py` y `navegador.py`: manejan el inicio de sesión en el navegador del
  usuario con un perfil propio de Pandex.

## Requisitos

| Id | Requisito | Se comprueba con |
|---|---|---|
| DES-01 | `Canvas.modulos` pide `items_url` cuando `len(items) < items_count`; `estructura._MITAD` y `emparejar_cursos` soportan secciones con decimales/letras (`Laboratorio 1.01`, `Lab 2A`) y cursos combinados (`Teo. 1 - Lab. 11`); `items_de_modulos` y `Sincronizacion` extraen archivos de Canvas enlazados como `ExternalUrl`, `Page` o `Assignment`. | `tests/test_descargas_canvas.py::DescargasCompletas` |
| DES-02 | Dos archivos con el mismo nombre que van a carpetas distintas (`Sem 1` vs `Sem 2`) y pesan distinto nunca se saltan como duplicados (tampoco en la primera corrida ni cuando el primero ya estaba en disco); si dos archivos distintos (otro id y otro tamaño) van a la misma carpeta en la misma corrida, el segundo se baja como `(v2)`. | `tests/test_descargas_canvas.py::NombresGenericosPorSemana` |
| DES-03 | En el asistente (`PaginaDescarga`) y en `Configuración → Tareas → Sincronizar Canvas` se puede elegir para «Archivos repetidos cada semana» entre «Descargar solo una vez» (`repetidos_cada_semana: false`, por defecto) y «Descargar siempre (en cada semana)» (`repetidos_cada_semana: true`). Con `true`, un mismo archivo publicado en varias semanas (mismo `file_id` o mismo nombre y tamaño) se baja en la carpeta de cada semana y no se vuelve a bajar donde ya está. | `tests/test_descargas_canvas.py::ArchivosRepetidosPorSemana` |
| DES-04 | Pandex descarga subencabezados y módulos de «Material adicional» (`Material adicional`, `Materiales adicionales`, `Material complementario`, `Material de apoyo`, `Material extra`, `Recursos adicionales`, `Additional Material`, `Supplementary Material`) en cualquier modo, descarga por defecto los módulos sin número de semana salvo `otros_modulos: false` y los archivos sin subencabezado dentro de una semana, y el clasificador de Markdown los reconoce como material de estudio. | `tests/test_descargas_canvas.py::MaterialAdicional` |
| DES-05 | Los enlaces a Google Drive (`drive.google.com/file/d/…`, `open?id=…`, `uc?id=…`, `docs.google.com/{document,presentation,spreadsheets}/d/…`) en `ExternalUrl`, `ExternalTool`, `Page` o `Assignment` de los módulos se descargan en su carpeta con su extensión real (`Content-Disposition` o exportación PDF/DOCX/PPTX/XLSX), pasando la confirmación de archivos grandes cuando Google la pide. | `tests/test_descargas_canvas.py::GoogleDriveDescarga` |
| DES-06 | Si Google Drive niega el acceso porque no hay sesión o la cuenta predeterminada del navegador no es la institucional, Pandex prueba las cuentas del perfil (`authuser=0, 1, 2…`) y, si hace falta, abre el navegador con el perfil de Pandex para que el usuario cambie a su cuenta institucional; guarda las cookies en `DATOS/sesion_drive.json` (`0600`, ocultas en el registro, borradas por «Olvidar mi sesión») y descarga el archivo. | `tests/test_descargas_canvas.py::GoogleDriveCuentaInstitucional` |

## Escenarios

**DES-01 / DES-02 · Curso con módulos largos, páginas y nombres genéricos (*Programación I*)**
- *Dado* un módulo con 15 ítems (Canvas solo incluye 10 en línea), una página con enlaces a archivos y semanas 1 y 2 con `Ejercicios.pdf` de distinto tamaño
- *Cuando* se sincroniza el curso
- *Entonces* se piden los 15 ítems a `items_url`, se bajan los archivos de la página y se guardan tanto `Sem 1/…/Ejercicios.pdf` como `Sem 2/…/Ejercicios.pdf`.

**DES-03 · PDF de la AP repetido todas las semanas (*Fundamentos del Cálculo*)**
- *Dado* `AP.pdf` (mismo id o mismo tamaño) publicado en `Semana 1`, `Semana 2` y `Semana 3`
- *Cuando* el usuario elige «Descargar siempre (en cada semana)»
- *Entonces* `AP.pdf` se descarga en `Sem 1`, `Sem 2` y `Sem 3`, y en la siguiente corrida no hace descargas nuevas.

**DES-04 · Material adicional**
- *Dado* un subencabezado o módulo «Material adicional» (o «Material complementario») en un curso con configuración clásica o del asistente
- *Cuando* se sincroniza
- *Entonces* se descarga dentro de `Material_adicional` (o `Material adicional` con estilo propio) en lugar de descartarse como «sin sección reconocida».

**DES-05 / DES-06 · Enlace a Google Drive con cuenta institucional**
- *Dado* un ítem de módulo que enlaza a `https://drive.google.com/file/d/ABC/view` restringido al correo de la universidad
- *Cuando* la cuenta predeterminada (`authuser=0`) da «Necesitas acceso» y el usuario cambia a la cuenta institucional (`authuser=1`) en el navegador de Pandex
- *Entonces* Pandex detecta el acceso con la cuenta institucional, guarda la sesión de Drive en `DATOS/sesion_drive.json` y descarga el archivo.

## Fuera de alcance

- Subir archivos a Google Drive o a Canvas (Pandex solo lee de Canvas/Drive y solo crea archivos en la carpeta de tus cursos, P4).
- Usar la API OAuth de Google Cloud con credenciales de desarrollador (Pandex usa la sesión del navegador del propio estudiante, sin servidores ni claves externas, P1).

## Preguntas abiertas

| # | Pregunta | Por defecto | Decide |
|---|---|---|---|

## Historial

| Fecha | Cambio | Por qué |
|---|---|---|
| 2026-11-28 | Primera versión. | Pedido de Frank: corregir material faltante en cursos como Programación I, opción de archivos repetidos cada semana (p. ej. AP en Fundamentos del Cálculo), material adicional y enlaces de Google Drive con cambio a cuenta institucional. |
