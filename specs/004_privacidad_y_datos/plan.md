# 004 · Plan

## Enfoque

Defensa en capas, de la más barata a la más cara:

1. **Pruebas de repositorio** (ya hechas: `tests/test_principios.py`): `.gitignore` y archivos
   versionados.
2. **Filtro del registro:** un `logging.Filter` en `pandex/log.py` que reemplaza por `***`
   cualquier valor que coincida con cookies conocidas de la sesión actual, `Bearer …`,
   `Authorization:` y `token=`. Así un `log` descuidado en una tarea futura tampoco filtra.
3. **Hosts permitidos:** una lista en `pandex/red.py` (`HOSTS_PERMITIDOS`) que usan
   `canvas/cliente.py` y `actualizar.py`; la prueba reemplaza `requests.Session.request` y
   falla si sale a otro host.
4. **Anonimizar al copiar:** `pandex/ui/visor_registro.py` gana el botón; la lógica
   (`anonimizar(texto, casa, usuario, canvas_url)`) vive en `pandex/log.py` para probarla sin Qt.
5. **Permisos:** `rutas.privado(ruta)` aplica `0600`/`0700` en Linux (no hace nada en
   Windows, donde la carpeta de usuario ya es privada).
6. **Escáner de secretos en la CI:** `gitleaks` como acción, solo sobre el diff del PR.

## Principios

- P1 es el objetivo. P5: ninguna dependencia nueva en la app (gitleaks corre solo en la CI).

## Archivos que se tocan

| Archivo | Cambio |
|---|---|
| `pandex/log.py` | filtro de secretos; `anonimizar()` |
| `pandex/red.py` | nuevo: `HOSTS_PERMITIDOS`, `verificar(url)` |
| `pandex/canvas/cliente.py`, `pandex/actualizar.py` | usan `red.verificar` |
| `pandex/rutas.py` | `privado()` |
| `pandex/canvas/sesion.py`, `pandex/onedrive.py` | llaman a `privado()` |
| `pandex/ui/visor_registro.py` | botón «Copiar para un issue» |
| `pandex/ui/configuracion.py` / `canvas/asistente.py` | «Olvidar mi sesión» |
| `tests/test_privacidad.py` | nuevo |
| `.github/workflows/pruebas.yml` | job `secretos` |
| `docs/privacidad.md` | se mantiene al día |

## Riesgos

| Riesgo | Qué se hace |
|---|---|
| El filtro del registro esconde información útil para depurar | Solo reemplaza valores de secretos, no nombres de campos ni rutas. |
| Un host legítimo nuevo (p. ej. el SSO) dispara la prueba | El SSO ocurre dentro del navegador, no con `requests`; si cambia, se actualiza la spec. |
