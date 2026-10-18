# Pandex: guía para agentes de código

Lo lee cualquier agente (Claude Code, Codex, Gemini CLI, Cursor, Copilot…). Detalle en
`docs/arquitectura.md`.

## Qué es
Mascota de escritorio (PyQt6, Python 3.12+) para Windows y Linux. Sincroniza archivos de Canvas
y convierte documentos a Markdown. Núcleo genérico en `pandex/`; funciones enchufables en `tasks/`.

## Comandos
```
python -m venv .venv && .venv/bin/python -m pip install -r requirements.txt -r requirements-markdown.txt   # Windows: .venv\Scripts\python.exe
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -t . -v   # Windows: sin la variable
QT_QPA_PLATFORM=offscreen .venv/bin/python main.py --test
```
«Convertir a Markdown» es opcional (`requirements-markdown.txt`, ver `pandex/extras.py`). Las `winrt-*` solo en Windows; Playwright solo en Windows (en Linux, Selenium con el Firefox del sistema). La CI corre en Windows y Ubuntu (3.12 y 3.13).

## Reglas
- Textos de interfaz y documentos: español de Perú neutro, directos y breves.
- Corrige solo errores reales; no refactorices por gusto ni hagas la app más pesada.
- Código que depende del sistema va detrás de `rutas.WINDOWS` (Windows) o de su equivalente en Linux.
- Toda hora que ve el usuario va en 12 horas (`pandex/horas.py`).
- Cada cambio de comportamiento lleva su prueba en `tests/` y una línea en `CHANGELOG.md`.
- Si el cambio llega al usuario, sube la versión en `pandex/__init__.py`.
- Personajes nuevos incluidos en la app: `.claude/skills/skin-pixel-art/SKILL.md` (sirve a cualquier agente).
- Rama propia y PR hacia `main`; no empujes directo a `main`.
