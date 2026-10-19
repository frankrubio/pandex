# Pandex: guía para agentes de código

Lo lee cualquier agente (Claude Code, Codex, Gemini CLI, Cursor, Copilot…). Detalle en
`docs/arquitectura.md`.

## Qué es
Mascota de escritorio (PyQt6, Python 3.12+) para Windows y Linux que automatiza tareas típicas
de estudiantes. Lo central: bajar el material de Canvas y ordenarlo; lo demás (Convertir a
Markdown, Comprimir carpeta…) son funciones de apoyo. Núcleo genérico en `pandex/`; funciones
enchufables en `tasks/`. Repositorio **público**.

## Cómo se trabaja (specs primero)
1. Lee `specs/principios.md` (reglas que nada puede romper) y `specs/tablero.md`.
2. Trabaja **una tarea** del tablero a la vez, siguiendo su `spec.md`, `plan.md` y `tareas.md`.
3. **Escribe primero la prueba** que indica la tarea y comprueba que falla por el motivo correcto.
4. Haz el cambio mínimo; corre toda la suite; marca la tarea en su `tareas.md` y en el tablero.
5. ¿Pedido sin tarea? Si toca rendimiento, peso, datos del usuario, archivos fuera de Pandex o
   el comportamiento en un sistema, escribe antes la spec (`specs/_plantilla/`). Si una
   pregunta abierta cambia el diseño, **pregunta**: no inventes la respuesta.
6. Si la spec y el código no coinciden, manda la spec. Si la spec parece mal, propón el cambio.

## Comandos
```
python -m venv .venv && .venv/bin/python -m pip install -r requirements.txt -r requirements-markdown.txt   # Windows: .venv\Scripts\python.exe
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -t . -v   # Windows: sin la variable
QT_QPA_PLATFORM=offscreen .venv/bin/python main.py --test
grep -rn "REN-04" tests/   # la prueba de un requisito
```
«Convertir a Markdown» es opcional (`requirements-markdown.txt`, ver `pandex/extras.py`). Las `winrt-*` solo en Windows; Playwright solo en Windows (en Linux, Selenium con el Firefox del sistema). La CI corre en Windows y Ubuntu (3.12 y 3.13).

## Presupuestos (no se pasan)
- Peso con todas las funciones opcionales ≤ 600 MB; base ≤ 350 MB.
- Sincronizar sin novedades ≤ 6 s; con descargas, tiempo propio (sin la transferencia) ≤ 10 s.
- Reposo: 0 % de CPU, ≤ 80 MB de memoria.

## Reglas
- Privacidad: nunca registres ni guardes contraseñas, cookies o tokens; nada personal entra al repo
  (`config.json`, `logs/` y la carpeta de datos están fuera de git).
- No toques el sistema: nada fuera de la carpeta del proyecto, la carpeta de datos (`rutas.DATOS`)
  y los lugares de `specs/principios.md#p3-sin-residuos`. Sin `sudo`, sin instalar nada global.
- Nada destructivo: sincronizar solo crea; mover o borrar necesita confirmación y deshacer.
- Textos de interfaz y documentos: español de Perú neutro, directos y breves.
- Nombres de archivo nuevos sin tildes, ñ ni espacios. Convenciones en `docs/convenciones.md`.
- Corrige solo errores reales y cumple specs; no refactorices por gusto ni hagas la app más pesada.
- Código que depende del sistema va detrás de `rutas.WINDOWS` (Windows) o de su equivalente en Linux.
- Toda hora que ve el usuario va en 12 horas (`pandex/horas.py`).
- Lo pesado se importa dentro de la función que lo usa, nunca al arrancar.
- Cada cambio de comportamiento lleva su prueba en `tests/` y una línea en `CHANGELOG.md`.
- Si el cambio llega al usuario, sube la versión en `pandex/__init__.py`.
- Personajes nuevos incluidos en la app: `.claude/skills/skin-pixel-art/SKILL.md` (sirve a cualquier agente).
- Rama propia y PR hacia `main` (plantilla en `.github/PULL_REQUEST_TEMPLATE.md`); no empujes directo a `main`.
