# 001 · Tareas

Una tarea = un PR. La prueba va primero y debe fallar por el motivo correcto.

## T001.1 · Contar pedidos por fase y separar el inicio de sesión manual

- **Requisitos:** REN-07, REN-08
- **Depende de:** —
- **Prueba primero:** `tests/test_rendimiento.py`
  - `Registro.test_registro_con_pedidos`: tras sincronizar con `CanvasFalso`, el detalle
    contiene `fases:` y `pedidos:` con un número por fase.
  - `Registro.test_fase_login_manual_aparte`: si `iniciar_sesion` informa que hubo ventana,
    aparece la fase `inicio de sesión manual` y no se suma a `sesión`.
- **Cambio:** `cliente.Canvas` cuenta pedidos (contador con candado); `sincronizar._detalle`
  los escribe. `sesion.iniciar_sesion` devuelve también cuánto se esperó a la persona.
- **Terminado cuando:** pruebas nuevas en verde; toda la suite en verde en la CI.

## T001.2 · Spike: ¿cuánto dura la sesión de Canvas?

- **Requisitos:** decide la pregunta abierta 2/3
- **Depende de:** —
- **Prueba primero:** no aplica (exploración). El código se descarta.
- **Cambio:** script local fuera del repo que guarda las cookies tras iniciar sesión y prueba
  `/api/v1/users/self` con `requests` a los 5 min, 1 h, 8 h y 24 h.
- **Terminado cuando:** la tabla de resultados está en `plan.md` → *Medición* y la decisión
  (atajo sí/no) en el *Historial* de `spec.md`.

## T001.3 · Atajo de sesión con cookies guardadas

- **Requisitos:** REN-02, REN-09
- **Depende de:** T001.1, T001.2 (solo si el spike dice que sirve)
- **Prueba primero:** `tests/test_rendimiento.py::Atajo`
  - `test_atajo_valido_no_abre_navegador`: con `sesion_canvas.json` presente y un servidor
    falso que responde 200, no se llama a `_abridor`.
  - `test_atajo_vencido_cae_al_navegador_y_se_borra`: con 401, se abre el navegador y el
    archivo desaparece.
  - `test_atajo_no_aparece_en_el_registro`: ninguna línea del registro contiene el valor de
    una cookie.
  - `test_atajo_permisos` (solo Linux): el archivo queda con modo `0o600`.
- **Cambio:** `sesion.py` (`intentar_atajo`, `guardar_atajo`, `olvidar_atajo`);
  «Configurar Canvas…» y «Cerrar sesión» llaman a `olvidar_atajo`.
- **Terminado cuando:** pruebas en verde; 5 corridas reales sin novedades con mediana ≤ 6 s
  copiadas al PR; `docs/privacidad.md` menciona el archivo.

## T001.4 · Leer todos los cursos en una sola tanda

- **Requisitos:** REN-02, REN-03, REN-05
- **Depende de:** T001.1
- **Prueba primero:** `tests/test_rendimiento.py::Presupuesto::test_sin_novedades_total`
  (Canvas falso, `latencia=0.15`, 10 cursos: la fase `módulos` dura ≤ 2 tandas de latencia),
  `test_con_historial_tiempo_propio` y `test_sin_consultas_repetidas` (la segunda corrida no
  pide a Canvas ningún archivo que el historial ya conoce).
- **Cambio:** `HILOS_API = min(10, max(6, cursos))` en `sincronizar.py`; pedir módulos en
  cuanto hay cookies.
- **Terminado cuando:** prueba en verde; medición real anotada.

## T001.5 · Concurrencia adaptativa para la primera vez

- **Requisitos:** REN-01, REN-06
- **Depende de:** T001.1
- **Prueba primero:**
  - `Presupuesto.test_primera_vez_tiempo_propio`: 10 cursos, 300 archivos nuevos,
    `latencia=0.15` → tiempo propio ≤ 10 s.
  - `Limites.test_limite_de_peticiones`: `CanvasFalso.limite=3` (3 respuestas 429) → termina
    bien y el registro dice «esperé 3 veces».
- **Cambio:** `cliente.py` lee `X-Rate-Limit-Remaining`; `metadatos()` ajusta hilos entre 4 y
  12; el historial recuerda qué cursos permiten `/files`.
- **Terminado cuando:** pruebas en verde; primera vez real ≤ 10 s de tiempo propio.

## T001.6 · Descargas sin esperas en serie

- **Requisitos:** REN-04
- **Depende de:** —
- **Prueba primero:** `Descargas.test_descargas_en_paralelo`: `CanvasFalso` registra cuántas
  descargas hay a la vez; el máximo es ≥ 4 cuando hay ≥ 4 archivos.
- **Cambio:** solo si la prueba falla.
- **Terminado cuando:** prueba en verde.

## T001.7 · Documentar las cifras reales

- **Requisitos:** REN-10
- **Depende de:** T001.3, T001.4, T001.5
- **Prueba primero:** no aplica (documentación).
- **Cambio:** `docs/sincronizar-canvas.md` → tabla de fases con fecha, sistema y mediana.
  `CHANGELOG.md`: «Sincronizar es más rápido: … s sin novedades».
- **Terminado cuando:** las cifras del doc coinciden con las del PR.
