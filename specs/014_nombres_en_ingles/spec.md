# 014 · Adaptar Pandex a nombres en inglés

> Estado: terminada  ·  Prefijo de requisitos: `ING`
> Principios que toca: P4 (nada destructivo), P7 (Windows y Linux), P8 (simple)

## Por qué

Quien lleva cursos en inglés o nombra sus carpetas en inglés (`Semester_2`, `Course_Calculus`,
`Week_01`, `Wk 3`, `Lecture`, `Theory`, `Laboratory`, `Class Material`, `Assignments`,
`Syllabus`…) hoy choca con varios límites: Pandex no empareja `Lecture`/`Theory` con
`Laboratory`, duplica carpetas como `Week_03` o `Lecture`/`Laboratory`, confunde `Lecture` y
`Laboratory` con secciones al detectar el estilo, pierde puntaje al emparejar carpetas que llevan
`Course` o `Semester` y no clasifica bien archivos en inglés en «Material de estudio».

## Qué existe hoy

- `pandex/canvas/nombres.py`: `RE_SEMANA` ya acepta `Week 3`, pero no `Week_03`, `Week-3` ni
  `Wk 3`; `RE_LAB` solo acepta `lab` y `laboratorio`, no `laboratory`.
- `pandex/canvas/estructura.py`: `_MITAD` solo reconoce `Teoría`/`Teo`/`Laboratorio`/`Lab`.
- `pandex/canvas/destinos.py`: `alias_semana` solo trae `Week {n}` (sin `Week {n:02d}`, `Wk`,
  `W` ni `S`); `_EQUIVALENTES` solo cubre abreviaturas en español (`teo`, `labo`, `laboratorio`).
- `pandex/canvas/adoptar.py`: `_VACIAS` solo tiene palabras en español; `TEORIA` y `LAB` no
  incluyen `Lecture` ni `Laboratory`; `PREFIJOS_SEMANA` no incluye `Wk`.
- `pandex/canvas/reconectar.py`: actualiza `formato_semana` y `estilo_carpetas`, pero no las
  mitades ni secciones detectadas.
- `pandex/markdown/clasificador.py`: la mayoría de patrones están solo en español.

## Requisitos

| Id | Requisito | Se comprueba con |
|---|---|---|
| ING-01 | `nombres.numero_de_semana`, `destinos.alias_semana` y `adoptar.formato_de_carpeta_semana` reconocen semanas en inglés (`Week 3`, `Week 03`, `Week_03`, `Week-3`, `Wk 3`, `Wk03`, `W03`, `S03`) sin confundir `Semester 1`, `Semester 2026`, `Semestre 2026` ni `Course 1` con una semana. | `tests/test_nombres_ingles.py::SemanasEnIngles` |
| ING-02 | `nombres.es_laboratorio`, `estructura.agrupar`/`emparejar_cursos` y `destinos.clave_carpeta`/`buscar_subcarpeta`/`mitad_de` reconocen `Theory`, `Lecture`, `Lec`, `Laboratory` y `Labs` como mitades equivalentes a `Teoría` y `Lab`, sin duplicar carpetas existentes. | `tests/test_nombres_ingles.py::MitadesEnIngles` |
| ING-03 | `adoptar.parecido` y `emparejar_carpetas` ignoran palabras vacías en inglés (`of`, `the`, `and`, `to`, `in`, `for`, `with`…) y prefijos organizativos (`course`, `curso`, `semester`, `semestre`, `ciclo`, `term`, `fall`, `spring`…), emparejando carpetas como `Course_Calculus_I` o `Semester_2_Physics_I` sin falsos positivos entre cursos distintos. | `tests/test_nombres_ingles.py::EmparejarEnIngles` |
| ING-04 | `adoptar.detectar_convenciones` reconoce `Wk`, `Lecture`/`Theory` y `Laboratory` sin confundir mitades con secciones; `adoptar.mapa_secciones` y `destinos.clave_carpeta` emparejan plurales en inglés (`Activity`/`Activities`, `Summary`/`Summaries`) y equivalentes español ↔ inglés (`Material de clase` ↔ `Class Material`, `Actividades` ↔ `Activities`, `Tareas` ↔ `Assignments`/`Homework`, `Lecturas` ↔ `Readings`, `Recursos` ↔ `Resources`, `Evaluaciones` ↔ `Exams`, `Sílabo` ↔ `Syllabus`, `Información del curso` ↔ `Course Information`). | `tests/test_nombres_ingles.py::ConvencionesYSeccionesEnIngles` |
| ING-05 | El asistente de Canvas deduce `Week {n}` y `Lecture`/`Theory` cuando el curso en Canvas está en inglés (sin afectar cursos en español), y `reconectar.adaptar` actualiza también las mitades y secciones detectadas al reconectar una carpeta en inglés. | `tests/test_nombres_ingles.py::AsistenteYReconectarEnIngles` |
| ING-06 | `pandex/markdown/clasificador.py` clasifica archivos y carpetas en inglés (`Homework`, `Assignment`, `Quiz`, `Midterm`, `Lecture`, `Slides`, `Reading`, `Submissions/`, `Course Information/`…). | `tests/test_nombres_ingles.py::ClasificadorEnIngles` |

## Escenarios

**ING-01 · Semana en inglés y carpeta `Semester`**
- *Dado* un curso con carpetas `Week_01` y `Semester 1`
- *Cuando* se busca la semana 1 y se analiza `"Semester 1"`
- *Entonces* se reutiliza `Week_01` y `"Semester 1"` no se toma como semana.

**ING-02 · Pareja Lecture + Laboratory en Canvas**
- *Dado* `"Physics I (PH101) - Lecture 1 - Fall Semester 2026"` y `"Physics I (PH101) - Laboratory 2 - Fall Semester 2026"`
- *Cuando* el asistente agrupa los cursos y sincroniza sobre carpetas `Week_01/Lecture` y `Week_01/Laboratory`
- *Entonces* ambos comparten carpeta y reutilizan `Lecture` y `Laboratory` sin crear `Teoria` ni `Lab`.

**ING-03 · Carpeta con `Course` o `Semester` en el nombre**
- *Dado* el curso `"Calculus I (MA101) - Fall Semester 2026"` y las carpetas `Course_01_Calculus_I` y `Course_02_History`
- *Cuando* se emparejan las carpetas
- *Entonces* elige `Course_01_Calculus_I` y no confunde `Course_02_History` por compartir la palabra `Course`.

**ING-05 · Reconectar una carpeta renombrada al inglés**
- *Dado* una configuración previa con `Sem {n}`, `Teoría`, `Lab` y `Material de clase`
- *Cuando* el usuario reconecta a `Semester_2/Course_Programacion_I/Week_01/Lecture/Class_Material` y `Laboratory`
- *Entonces* el destino, `formato_semana`, `subcarpeta_fija` y `secciones` se adaptan sin tocar el disco.

## Fuera de alcance

- Traducir la interfaz de Pandex al inglés (P8: la interfaz sigue en español de Perú neutro).
- Renombrar carpetas existentes del usuario (P4).
- Traducir títulos arbitrarios de cursos entre idiomas (el usuario siempre puede elegir la carpeta en el desplegable).

## Preguntas abiertas

| # | Pregunta | Por defecto | Decide |
|---|---|---|---|

## Historial

| Fecha | Cambio | Por qué |
|---|---|---|
| 2026-11-27 | Primera versión. | Pedido de Frank: verificar y completar la adaptación de Pandex a nombres en inglés (`semester`, `week`, `course`, etc.). |
