# 014 · IA y Google Calendar

> Estado: aprobada | Prefijo: `CON` | Principios: P1, P2, P3, P4, P5, P8

## Por qué

Pandex puede delegar trabajo a un cerebro de IA y consultar o crear eventos, pero no puede
guardar secretos ni ejecutar proveedores sin permisos explícitos.

## Requisitos

| Id | Requisito | Se comprueba con |
|---|---|---|
| CON-01 | Credenciales fuera de `config.json`, Git y el registro. | `tests/test_conexiones.py` |
| CON-02 | IA admite ejecutables locales configurables: OpenCode, Antigravity o otro. | `test_ia.py` |
| CON-03 | El integrador nunca usa shell: argumentos separados y sin expansión. | `test_ia.py::test_no_shell` |
| CON-04 | Cada tarea delegada debe mostrar su alcance y pedir confirmación si puede escribir o ejecutar. | prueba de UI y core |
| CON-05 | No puede borrar archivos, ejecutar comandos destructivos ni salir de la carpeta autorizada. | política de acciones |
| CON-06 | Google Calendar usa OAuth y PKCE; nunca pide contraseña ni guarda el refresh token en Git/config. | `test_calendar.py` |
| CON-07 | Consultar eventos no requiere confirmación destructiva; crear/actualizar requiere vista previa y confirmación. | `test_calendar.py` |
| CON-08 | Revocar desconecta y borra credenciales locales. | prueba de revocación |
| CON-09 | Los hosts remotos son exactos y visibles por permiso. | revisión de `pandex/red.py` |

## Fuera de alcance

- Responder de forma autónoma sin límites.
- Acceso a archivos fuera de permisos.
- Secretos, tokens o cookies dentro de código o ejemplos.
