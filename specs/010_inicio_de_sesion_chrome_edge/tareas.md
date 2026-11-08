# 010 · Tareas

## T010.1 · Inicio de sesión fiable en Chrome y Edge

- **Requisitos:** SES-01 a SES-07
- **Prueba primero:** `tests/test_navegador.py` (`HaySesion`, `EnUso`, `EsperarSesion`,
  `ErroresPasajeros`, `IniciarSesionConVentanaNormal`)
- **Terminado cuando:**
  - [x] las pruebas nuevas pasan y antes fallaban;
  - [ ] toda la suite pasa en Windows y Linux (CI);
  - [x] `CHANGELOG.md` y `docs/` al día;
  - [ ] probado en Windows real con Chrome y Edge.

## T010.2 · Correcciones de la revisión de código (2.6.7)

- **Requisitos:** SES-01, SES-03, SES-05, SES-06, SES-08
- **Prueba primero:** `tests/test_navegador.py` (`RegistroSinDatos`, `ProcesosDelPerfil`, casos nuevos en
  `Abrir`, `EnUso`, `ErroresPasajeros`, `EsperarSesion` e `IniciarSesionConVentanaNormal`)
- **Cambio:** `navegador.py` (`SinRed`, `SinInstalar`, `limpiar`, `para_registro`, candado con la línea
  de comandos, `procesos_del_perfil`, `cerrar_procesos`, `abierto_aqui`); `sesion.py`
  (`_intento_sin_ventana`, `_perfil_ocupado`); registro limpio en `asistente.py` y `sincronizar.py`.
- **Terminado cuando:**
  - [x] las pruebas nuevas pasan y antes fallaban;
  - [x] probado con un Chromium real sin ventana en Linux: candado, procesos y cierre;
  - [ ] toda la suite pasa en Windows y Linux (CI);
  - [ ] probado en Windows real (PowerShell y `taskkill`);
  - [x] `CHANGELOG.md` y `docs/` al día.
