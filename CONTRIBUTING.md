# Contribuir a Pandex

Gracias por querer ayudar. Pandex lo usan estudiantes que no programan, así que cada cambio
tiene que ser pequeño, probado y fácil de revisar. Esta guía sirve igual para personas y para
agentes de IA.

## Antes de empezar

1. Lee [specs/principios.md](specs/principios.md): son las reglas que ningún cambio puede romper
   (privacidad, nada fuera de sus carpetas, máximo 600 MB, rapidez, Windows y Linux).
2. Mira [specs/tablero.md](specs/tablero.md): ahí están las tareas libres, en orden.
3. ¿Tu idea no está? Abre un issue «Idea» primero. Si toca rendimiento, peso, datos del
   usuario, archivos fuera de Pandex o el comportamiento en un sistema, necesita una spec
   (copia [specs/_plantilla/](specs/_plantilla/)).

## Preparar el entorno

```bash
git clone https://github.com/frankrubio/pandex.git && cd pandex
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-markdown.txt   # Windows: .venv\Scripts\python.exe
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -t .
```

Todo debe pasar antes de tocar nada. Si algo falla en un clon limpio, eso ya es un issue.

## Cómo se trabaja

```
tarea del tablero → rama → prueba que falla → cambio mínimo → suite en verde → PR
```

1. **Rama propia** desde `main`: `tarea/T003.2-pip-sin-cache`. Nunca se empuja a `main`.
2. **La prueba va primero.** La tarea dice cuál. Córrela y comprueba que falla por el motivo
   correcto.
3. **El cambio mínimo** que la hace pasar. Nada de refactorizar «de paso».
4. **Toda la suite** en verde y `main.py --test` abre y cierra.
5. **Documentación:** si cambió algo que el usuario nota, una línea en `CHANGELOG.md` (y sube la
   versión en `pandex/__init__.py`); si cambió cómo funciona, actualiza `docs/`.
6. **Marca la tarea** en su `tareas.md` y en `specs/tablero.md`.
7. **Abre el PR** y completa el checklist.

Detalle de estilo, nombres, registro y versiones: [docs/convenciones.md](docs/convenciones.md).
Cómo escribir y correr pruebas: [docs/pruebas.md](docs/pruebas.md).

## Si usas un agente de IA

El agente lee `AGENTS.md` (Claude Code también, a través de `CLAUDE.md`). Para que trabaje sin
huecos:

- Dale **una tarea del tablero**, no una idea suelta: «Haz T003.2 siguiendo
  specs/003_sin_residuos_y_desinstalar/tareas.md».
- Pídele que te muestre la prueba fallando **antes** de cambiar el código.
- Revisa tú el diff completo: el agente puede registrar datos sensibles, añadir dependencias o
  escribir fuera de las carpetas permitidas sin notarlo. El checklist del PR te guía.
- Si el agente encuentra que la spec está mal o incompleta, que proponga el cambio de spec en
  el PR; no que «arregle» el código a su criterio.

## Qué no se acepta

- Datos personales en el repositorio (configuraciones, registros, capturas con datos reales).
- Dependencias nuevas sin su peso medido y sin spec.
- Código que escriba fuera de los lugares de `principios.md#p3-sin-residuos`.
- Cambios sin prueba que cambien el comportamiento.
- Personajes o imágenes sin licencia clara para un repositorio público.
- Telemetría, analítica o servicios en la nube.
