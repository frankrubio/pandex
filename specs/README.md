# Especificaciones de Pandex

Aquí se decide **qué** tiene que hacer Pandex antes de escribir el **cómo**. Cualquier
persona o agente (Claude Code, Codex, Gemini CLI, Cursor, Copilot…) trabaja igual: lee la
spec, sigue su plan, toma una tarea, escribe primero la prueba y después el código.

Es *Spec-Driven Development* (SDD) con Markdown simple: no depende de Spec Kit, Kiro ni
OpenSpec, aunque sigue la misma idea.

## Por qué

Un pedido de una línea («haz que sincronice más rápido») deja al agente decidiendo solo lo
que no se dijo: qué se mide, en qué PC, qué pasa si falla, qué no se debe tocar. Los huecos
se notan después, como errores. Una spec cierra esos huecos antes:

- cada requisito se responde con **sí o no**;
- lo que **queda fuera** está escrito;
- lo que **no sabemos** está escrito como pregunta, no inventado.

## Qué hay en esta carpeta

| Archivo | Para qué |
|---|---|
| [principios.md](principios.md) | Las reglas que ninguna spec, plan ni tarea puede romper. Léelo primero. |
| [tablero.md](tablero.md) | Todas las tareas, su estado y cuál sigue. Empieza por aquí si vienes a trabajar. |
| `NNN_nombre/spec.md` | **Qué** y **por qué**: requisitos verificables, escenarios, fuera de alcance, preguntas abiertas. |
| `NNN_nombre/plan.md` | **Cómo**: módulos que se tocan, decisiones, riesgos y cómo se mide. |
| `NNN_nombre/tareas.md` | Pasos pequeños, cada uno con su prueba primero y su criterio de «terminado». |
| [_plantilla/](_plantilla/) | Copia esta carpeta para una spec nueva. |

| Spec | Tema |
|---|---|
| [001_rendimiento_sincronizar](001_rendimiento_sincronizar/spec.md) | 10 s con descargas, 6 s sin novedades |
| [002_peso_y_funciones_opcionales](002_peso_y_funciones_opcionales/spec.md) | Máximo 600 MB; lo opcional no se descarga si no lo quieres |
| [003_sin_residuos_y_desinstalar](003_sin_residuos_y_desinstalar/spec.md) | Nada fuera de sus carpetas, nada que se acumule, desinstalar limpio |
| [004_privacidad_y_datos](004_privacidad_y_datos/spec.md) | Solo los datos necesarios; nada personal llega a GitHub |
| [005_interfaz_y_configuracion](005_interfaz_y_configuracion/spec.md) | Interfaz bonita, simple y funcional; configuración fácil; se adapta a tu PC |
| [006_paridad_windows_linux](006_paridad_windows_linux/spec.md) | Mismo comportamiento en Windows y Linux, sin conflictos de versión |
| [007_tareas_y_cambios_faciles](007_tareas_y_cambios_faciles/spec.md) | Agregar tareas y modificar Pandex sin romper nada |

Las páginas de `docs/` describen **cómo funciona hoy** Pandex. Las specs describen **lo que
cambia**. Cuando una spec se termina, su comportamiento pasa a `docs/` y la spec queda
como registro de la decisión.

## El flujo

```
 idea / issue
     │
     ▼
 spec.md ──── ¿hay preguntas abiertas que cambian el diseño? ── sí ──► se le pregunta a Frank
     │ no                                                               (no se inventa)
     ▼
 plan.md ──── respeta principios.md
     │
     ▼
 tareas.md ── una tarea = una prueba que hoy falla + el cambio mínimo que la hace pasar
     │
     ▼
 PR pequeño ─ checklist de .github/PULL_REQUEST_TEMPLATE.md
```

1. **Lee** `principios.md`, `tablero.md` y la spec completa de tu tarea.
2. **Toma una sola tarea** (la primera libre, sin dependencias pendientes). Márcala
   «en curso» en `tablero.md` en tu rama.
3. **Escribe primero la prueba** que la tarea indica. Córrela y comprueba que **falla por el
   motivo correcto**.
4. **Haz el cambio mínimo** para que pase. Corre toda la suite.
5. **Cierra la tarea:** marca la casilla en `tareas.md`, actualiza `tablero.md`, añade una
   línea en `CHANGELOG.md` si el usuario lo nota, y abre el PR.

## Cuando un requisito cambia

1. Primero cambia la **spec**: edita el requisito y anota en su sección *Historial* qué
   cambió, cuándo y por qué. No borres el requisito viejo: márcalo ~~tachado~~.
2. Después cambia o añade la **prueba** que lo verifica.
3. Recién ahí cambia el **código**.

Si el código y la spec no coinciden, la spec manda. Si crees que la spec está mal, no
«corrijas» el código a tu criterio: propón el cambio de spec en el PR o en un issue.

## Tres niveles de especificación

| Nivel | Qué significa | ¿Lo usamos? |
|---|---|---|
| *Spec-first* | La spec se escribe antes y luego se olvida. | No: se desactualiza. |
| *Spec-anchored* | La spec vive junto al código y se actualiza con él. | **Sí.** |
| *Spec-as-source* | El código se genera desde la spec y nadie lo edita a mano. | No: Pandex se revisa y se depura a mano. |

## Cuándo NO hace falta una spec

- Un error de una línea, un texto mal escrito, un enlace roto: basta con su prueba (si cambia
  el comportamiento) y su línea en `CHANGELOG.md`.
- Una exploración (*spike*) para ver si algo es posible: hazla en una rama aparte, anota lo
  que aprendiste en la spec correspondiente y **descarta el código**.
- Un personaje nuevo: sigue `.claude/skills/skin-pixel-art/SKILL.md`.

Todo lo demás, en especial lo que toca rendimiento, peso, datos del usuario, archivos fuera
de la carpeta de Pandex o el comportamiento en Windows/Linux, **necesita spec**.

## Identificadores

- Requisito: `PREFIJO-NN` (p. ej. `REN-04`). El prefijo es de la spec y no se reutiliza.
- Tarea: `T<spec>.<n>` (p. ej. `T001.3`).
- Prueba: el nombre de la prueba cita el requisito en su docstring: `"""REN-04: …"""`.
  Así `grep -rn "REN-04" tests/` encuentra la prueba de cada requisito.
