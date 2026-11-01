# 009 · Reconectar la carpeta de cursos

> Estado: en curso  ·  Prefijo de requisitos: `REC`
> Principios que toca: P4 (nada destructivo), P8 (todo desde la interfaz)

## Por qué

Si renombras o mueves la carpeta donde Pandex guarda tus cursos, la sincronización dice
«No encuentro tu carpeta de cursos» y no hay forma de arreglarlo desde Pandex: hay que repetir
el asistente de Canvas (con inicio de sesión) o editar `config.json`. Pasó el 31/10/2026.

## Qué existe hoy

- `docs/sincronizar-canvas.md`: `destino` y la `carpeta` de cada curso en `config.json`.
- `pandex/canvas/adoptar.py`: `parecido`, `detectar_convenciones` (el asistente las usa al elegir una carpeta existente).

## Requisitos

| Id | Requisito | Se comprueba con |
|---|---|---|
| REC-01 | Elegir una carpeta cambia el `destino` y deja cada curso apuntando a la subcarpeta que más se le parece (aunque se llame distinto: `Programacion_I` ↔ `Programación I`). | `tests/test_reconectar.py::Adaptar` |
| REC-02 | Las reglas que comparten carpeta (teoría y lab) quedan en la misma. Un curso sin pareja conserva su nombre (se creará al sincronizar) y se avisa. | `…::Adaptar` |
| REC-03 | Si la carpeta ya tiene tu estilo (`Sem 3`, `Semana 03`…), se actualizan `formato_semana` y `estilo_carpetas`. | `…::Estilo` |
| REC-04 | No mueve, renombra ni borra nada del disco, ni modifica los datos que recibe; guarda una copia de la configuración anterior. | `…::Seguridad` |
| REC-05 | Si la carpeta no existe, no cambia nada y lo dice. | `…::Seguridad` |
| REC-06 | Configuración tiene el botón «Reconectar carpeta de cursos…» (con resumen y confirmación) y el aviso de carpeta no encontrada lo menciona. | `tests/test_ui.py` |

## Fuera de alcance

- Reordenar archivos (eso lo hace «Configurar Canvas…»). El historial no se toca: si una ruta
  anotada ya no existe, se revisa de nuevo y no se duplica nada.
- Buscar la carpeta sola en todo el disco.

## Historial

| Fecha | Cambio | Por qué |
|---|---|---|
| 2026-11-01 | Primera versión. | Frank renombró su carpeta de cursos y Pandex dejó de sincronizar. |
