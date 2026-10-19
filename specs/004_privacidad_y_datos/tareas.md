# 004 · Tareas

## T004.1 · Pruebas de repositorio ✅

- **Requisitos:** PRI-01, PRI-02
- **Hecho:** `tests/test_principios.py` (clase `Privacidad`). Si alguna vez falla, **no** se
  relaja la prueba: se saca el archivo del repositorio y se revisa el historial de git.

## T004.2 · Filtro de secretos en el registro

- **Requisitos:** PRI-03
- **Depende de:** —
- **Prueba primero:** `tests/test_privacidad.py::Registro`
  - `test_registro_sin_secretos`: sincronizar con `CanvasFalso` y cookies
    `[{"name": "canvas_session", "value": "SECRETO123"}]`; además, una tarea falsa que hace
    `ctx.log("Authorization: Bearer abc")`. Ningún registro contiene `SECRETO123` ni `abc`.
  - `test_users_self_no_se_registra`.
- **Cambio:** `logging.Filter` en `pandex/log.py`; `sesion.py` registra los valores de las
  cookies obtenidas en el filtro.
- **Terminado cuando:** pruebas en verde.

## T004.3 · Solo hosts permitidos

- **Requisitos:** PRI-04
- **Depende de:** —
- **Prueba primero:** `test_solo_hosts_permitidos`: con `requests.Session.request` simulado,
  sincronizar y buscar actualizaciones solo tocan `canvas.ejemplo.edu` y los de GitHub; un
  pedido a `ejemplo.com` lanza `ErrorRed`.
- **Cambio:** `pandex/red.py`; `cliente.py` y `actualizar.py` lo usan.
- **Terminado cuando:** prueba en verde.

## T004.4 · Copiar el registro anonimizado

- **Requisitos:** PRI-05
- **Depende de:** —
- **Prueba primero:** `test_registro_anonimizado` (función pura) y
  `tests/test_ui.py::test_visor_tiene_copiar_para_issue`.
- **Cambio:** `log.anonimizar()`; botón en `ui/visor_registro.py`; la plantilla
  `.github/ISSUE_TEMPLATE/error.yml` menciona el botón.
- **Terminado cuando:** pruebas en verde.

## T004.5 · Permisos privados en Linux

- **Requisitos:** PRI-06
- **Depende de:** —
- **Prueba primero:** `test_permisos_de_archivos_sensibles` (se salta en Windows).
- **Cambio:** `rutas.privado()`; llamadas en `sesion.py`, `onedrive.py`.
- **Terminado cuando:** prueba en verde en Ubuntu.

## T004.6 · Olvidar mi sesión

- **Requisitos:** PRI-07
- **Depende de:** —
- **Prueba primero:** `test_olvidar_sesion`: borra `browser-profile*` y `sesion_canvas.json`;
  `historial_canvas.json` y `config.json` siguen iguales.
- **Cambio:** `sesion.olvidar()` + entrada en Configuración → Canvas.
- **Terminado cuando:** prueba en verde.

## T004.7 · Claves de config documentadas

- **Requisitos:** PRI-08
- **Depende de:** —
- **Prueba primero:** `test_claves_de_config_documentadas`: cada clave de `config.DEFAULTS` y
  de los parámetros de `sync_canvas` aparece en `docs/privacidad.md` o en
  `docs/sincronizar-canvas.md#configuración`.
- **Cambio:** completar la documentación si falta algo.
- **Terminado cuando:** prueba en verde.

## T004.8 · Escáner de secretos en la CI

- **Requisitos:** PRI-09
- **Depende de:** —
- **Prueba primero:** abrir un PR de prueba con un token falso con formato real y ver que el
  job falla (luego se cierra sin fusionar).
- **Cambio:** job `secretos` en `.github/workflows/pruebas.yml`.
- **Terminado cuando:** el job corre en cada PR.
