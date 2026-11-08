# Tablero de tareas

Todas las tareas de las specs, en el orden sugerido. **Toma la primera `libre` cuyas
dependencias estén `hecha`.** Al empezar, cámbiala a `en curso (tu-rama)` en tu rama; al
fusionar el PR, a `hecha`. Una tarea `bloqueada` espera una respuesta de Frank (pregunta
abierta de su spec).

Estados: `libre` · `en curso (rama)` · `hecha` · `bloqueada (motivo)`

## Prioridad 1 · Redes de seguridad (baratas, evitan regresiones)

| Tarea | Qué | Spec | Depende de | Estado |
|---|---|---|---|---|
| T004.1 | Pruebas de repositorio: `.gitignore` y archivos personales | 004 | — | hecha |
| T006.0 | Dependencias con versión fija y cada una en su sistema | 006 | — | hecha |
| T007.1 | Contrato de tareas y mapa de módulos en la CI | 007 | — | hecha |
| T003.1 | Prueba que vigila residuos fuera de los lugares permitidos | 003 | — | libre |
| T002.1 | Medir el peso y vigilarlo en la CI | 002 | — | hecha |
| T001.1 | Contar pedidos por fase; separar inicio de sesión manual | 001 | — | libre |
| T006.1 | Matriz completa en la CI (Ubuntu 22.04/24.04, Windows; Python 3.12–3.14) | 006 | — | libre |
| T005.1 | Reglas de aspecto como pruebas | 005 | — | libre |

## Prioridad 2 · Residuos y privacidad (riesgo bajo, valor alto)

| Tarea | Qué | Spec | Depende de | Estado |
|---|---|---|---|---|
| T003.2 | pip sin caché, en un solo lugar | 003 | — | hecha |
| T003.3 | Drivers y navegadores en la carpeta de datos | 003 | — | hecha |
| T003.4 | Límites para respaldos y copias de configuración | 003 | — | hecha |
| T004.2 | Filtro de secretos en el registro | 004 | — | libre |
| T004.3 | Solo hosts permitidos | 004 | — | libre |
| T004.5 | Permisos privados en Linux | 004 | — | libre |
| T004.6 | Olvidar mi sesión | 004 | — | libre |
| T004.7 | Claves de config documentadas | 004 | — | libre |
| T004.8 | Escáner de secretos en la CI | 004 | — | libre |
| T004.9 | MarkItDown sin Magika ni onnxruntime: sin telemetría | 004 | — | en curso (claude/vibrant-volta-t1vhh9) |

## Prioridad 3 · Rendimiento y peso (los requisitos de números)

| Tarea | Qué | Spec | Depende de | Estado |
|---|---|---|---|---|
| T001.2 | Spike: ¿cuánto dura la sesión de Canvas? | 001 | — | libre |
| T001.3 | Atajo de sesión con cookies guardadas | 001 | T001.1, T001.2 | en curso (claude/vibrant-volta-t1vhh9) |
| T001.4 | Leer todos los cursos en una sola tanda | 001 | T001.1 | libre |
| T001.5 | Concurrencia adaptativa para la primera vez | 001 | T001.1 | libre |
| T001.6 | Descargas sin esperas en serie | 001 | — | libre |
| T001.7 | Documentar las cifras reales | 001 | T001.3, T001.4, T001.5 | libre |
| T002.2 | Extras en un solo lugar (`PANDEX_EXTRAS`) | 002 | — | libre |
| T002.3 | Quitar un extra desde Configuración | 002 | T002.2 | libre |
| T002.4 | Bajar del límite de 600 MB | 002 | T002.1 | hecha |
| T002.5 | Navegador a elección (Firefox, Chrome o Edge) sin descargas, con Selenium | 002 | — | hecha |
| T002.6 | Pesos reales en la documentación | 002 | T002.4 | libre |
| T002.7 | Memoria en reposo ≤ 80 MB de RSS siempre (hoy 74–88 MB) | 002 | — | libre |

## Prioridad 4 · Desinstalar, paridad e interfaz

| Tarea | Qué | Spec | Depende de | Estado |
|---|---|---|---|---|
| T003.5 | Quitar paquetes huérfanos al actualizar | 003 | T003.2 | hecha |
| T003.6 | Inventario de lo creado fuera | 003 | — | hecha |
| T003.7 | Desinstalar Pandex (`desinstalar.sh`, `desinstalar.bat`, botón) | 003 | T003.6 | hecha |
| T006.2 | La CI ejecuta los instaladores | 006 | T002.2 | libre |
| T006.3 | Python portátil en Linux viejo | 006 | T006.2 | bloqueada (pregunta 1 de 006) |
| T006.4 | Mismo árbol en los dos sistemas | 006 | — | libre |
| T006.5 | Rutas con espacios, tildes y ñ | 006 | — | libre |
| T006.6 | Plantilla de issue y sistemas no soportados | 006 | — | libre |
| T005.2 | Globo conciso y errores con acción | 005 | — | libre |
| T005.3 | Una acción principal por ventana | 005 | T005.1 | libre |
| T005.4 | Primera vez solo con la URL | 005 | — | libre |
| T005.5 | Configuración sin JSON (Restablecer, Cancelar) | 005 | — | libre |
| T005.6 | Leer las preferencias del sistema en un solo lugar | 005 | — | libre |
| T005.7 | Configuración abre rápido | 005 | — | libre |
| T004.4 | Copiar el registro anonimizado | 004 | — | libre |

## Prioridad 5 · Comodidad para quien programa

| Tarea | Qué | Spec | Depende de | Estado |
|---|---|---|---|---|
| T007.2 | Generador de tareas (`herramientas/nueva_tarea.py`) | 007 | — | libre |
| T007.3 | Tareas documentadas (falta la prueba; el README ya menciona «Comprimir carpeta») | 007 | — | libre |
| T007.4 | Sin `print` y con estilo (`ruff`) | 007 | — | libre |
| T007.5 | Errores en los ganchos no tumban la app | 007 | — | libre |
| T008.1 | Estilo de carpetas (`_` por defecto, o el tuyo) | 008 | — | hecha |
| T008.2 | Aplicar una configuración de Canvas ya escrita | 008 | — | hecha |
| T009.1 | Reconectar la carpeta de cursos desde Configuración | 009 | — | en curso (claude/vibrant-volta-t1vhh9) |
| T010.1 | Iniciar sesión sin trabas en Chrome y Edge | 010 | — | en curso (claude/vibrant-volta-t1vhh9) |

## Preguntas abiertas para Frank

Resumen de lo que bloquea o cambia el diseño. El detalle está en cada spec.

| Spec | # | Pregunta | Por defecto si no hay respuesta |
|---|---|---|---|
| 001 | 1 | «10 s descargando todo»: ¿tiempo propio o total? | Tiempo propio |
| 001 | 2 | ¿Guardar las cookies de sesión en la carpeta de datos para no abrir el navegador? | Sí, con P1 |
| 001 | 3 | ¿Token de Canvas opcional («Modo rápido»)? | No por ahora |
| 002 | 1 | ¿600 MB con todas las funciones opcionales? | Sí |
| 002 | 2 | ¿Podar librerías de Qt no usadas? | Sí, con prueba de humo |
| 002 | 3 | ¿Selenium también en Windows (sin Playwright)? | **Respondida (31/10):** sí; Frank pidió elegir el navegador (ADR-0001, D1) |
| 002 | 4 | ¿Dejar MarkItDown por conversores directos? | No por ahora |
| 003 | 1 | ¿El desinstalador borra la carpeta del proyecto? | No; explica cómo |
| 003 | 3 | ¿Al actualizar se limpian las cachés que dejaron versiones anteriores (pip, Selenium, Playwright)? | **Respondida (31/10):** sí, con la lista y confirmación (ADR-0001, D4) |
| 002 | 5 | ¿El presupuesto de memoria pasa a «memoria propia (USS) ≤ 40 MB»? Hoy: 74–88 MB de RSS, de los que ~80 % es Qt compartido | **Respondida (31/10):** no; sigue ≤ 80 MB de RSS. Bajarla es T002.7 |
| 006 | 1 | ¿`uv` para Python portátil en Linux viejo? | Sí, todo dentro de la carpeta |
| 007 | 1 | ¿Tareas propias del usuario en `DATOS/tareas/`? | Sí, en una versión futura |
| 008 | 1 | ¿La carpeta de curso siempre en `_` aunque el usuario las tenga con espacios? | Sí (ver spec 008) |
