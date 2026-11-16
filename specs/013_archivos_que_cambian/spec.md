# 013 · Archivos que el docente vuelve a subir

> Estado: en curso  ·  Prefijo de requisitos: `CAM`
> Principios que toca: P4 (nada destructivo), P2 (rendimiento)

## Por qué

Cuando el docente corrige una diapositiva y la vuelve a subir con el mismo nombre, Canvas le da
otro id. Pandex ve un archivo con ese nombre en tu carpeta, cree que ya lo tienes y **no baja la
versión corregida**, sin avisar. Te quedas estudiando la versión vieja (fallo F3 de la revisión
de 2026-11).

## Qué existe hoy

- `sincronizar._decidir()` pregunta a `destinos.Indice.buscar()` si ya tienes el archivo:
  basta el **mismo nombre** en la carpeta del curso (en la otra mitad del curso, teoría o
  laboratorio, también tiene que pesar igual).
- `historial.Historial` anota id de Canvas → ruta y tamaño de lo que Pandex bajó o reconoció.
- Sincronizar solo crea: nunca pisa, mueve ni borra (`docs/sincronizar-canvas.md`).

## Requisitos

| Id | Requisito | Se comprueba con |
|---|---|---|
| CAM-01 | Si Canvas trae un archivo **nuevo** (id que el historial no conoce) con el nombre de uno que el historial anotó con **otro id y otro tamaño**, se baja como versión nueva: `Clase 5 (v2).pdf` (o `v3`, `v4`… el primer nombre libre) en su carpeta. | `tests/test_canvas_sincronizar.py::ArchivosQueCambian::test_version_corregida_se_baja_aparte` |
| CAM-02 | La versión anterior queda **intacta** (mismo nombre, mismos bytes), aunque la hayas anotado o renombrado otras. | ídem |
| CAM-03 | Si el tamaño es el mismo, o Canvas o el historial no lo saben, sigue como antes: «ya lo tenías», sin bajar nada. | `::test_mismo_tamano_no_se_baja_otra_vez` |
| CAM-04 | Un archivo tuyo con ese nombre que Pandex nunca anotó (lo tenías de antes) cuenta como tuyo, como hoy: no aparecen copias `(v2)` al estrenar Pandex sobre una carpeta llena. | `::test_lo_que_tenias_de_antes_no_se_duplica` |
| CAM-05 | Sin pedidos extra a Canvas: solo se compara lo que la fase «consultas» ya trae. | `::test_version_corregida_se_baja_aparte` (cuenta `archivo`) |
| CAM-06 | El registro y el informe dicen que es una versión nueva. | `::test_version_corregida_se_baja_aparte` |

## Escenarios

**CAM-01 · Diapositiva corregida**
- *Dado* `Sem 5/Clase 5.pdf` que Pandex bajó (id 501, 9000 bytes)
- *Cuando* el docente la reemplaza en Canvas (id 502, 9500 bytes, mismo nombre)
- *Entonces* aparece `Sem 5/Clase 5 (v2).pdf`, `Clase 5.pdf` sigue igual y el resumen cuenta
  «1 nuevo(s)».

**CAM-03 · Misma versión con otro id**
- *Dado* el mismo `Clase 5.pdf`
- *Cuando* el docente la vuelve a publicar sin cambios (id 503, 9000 bytes)
- *Entonces* no se baja nada y el historial anota el id 503 en esa ruta.

## Fuera de alcance

- Detectar cambios de un archivo cuyo **id no cambia** (Canvas lo reemplaza conservando el id):
  pediría a Canvas los datos de todo lo conocido en cada corrida (va contra REN-05).
- Borrar, mover o renombrar la versión anterior.
- Archivos que no están en módulos (F7, postergado con las propuestas).

## Preguntas abiertas

| # | Pregunta | Por defecto | Decide |
|---|---|---|---|
| 1 | ¿Formato del nombre de la versión nueva? | `Nombre (v2).ext` | Frank |

## Historial

| Fecha | Cambio | Por qué |
|---|---|---|
| 2026-11-16 | Primera versión. | Fallo F3 de la revisión: la versión corregida no se bajaba. |
