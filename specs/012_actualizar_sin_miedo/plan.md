# 012 · Plan

## Enfoque

- **ACT-01:** `PandexApp.actualizar_ya` abre `DialogoActualizacion` sin `aplicar_ya`; tras
  «Actualizar ahora» y terminar, reinicia solo (ya lo confirmaste).
- **ACT-02:** `buscar()` pregunta primero por `releases/latest` (API de GitHub). Si hay versión
  publicada, `info` lleva la etiqueta y las direcciones del ZIP y de su `.sha256`; `aplicar(info=…)`
  descarga, compara la huella y recién entonces copia. Con git: `git fetch origin tag vX.Y.Z` y
  `git merge --ff-only`. Sin versiones publicadas (404), todo sigue como antes con `main`.
- **ACT-03/04:** `pandex/vuelta.py` (solo biblioteca estándar y `rutas`) guarda y aplica el punto
  de vuelta. `aplicar()` lo escribe antes de copiar; la ventana ofrece «Volver a la versión
  anterior» si existe.
- **ACT-05:** `actualizacion.json` queda en `"probando"` tras actualizar. `main.py` marca `"ok"`
  cuando `app.iniciar()` termina; si el arranque falla con un punto en `"probando"`, vuelve, deja
  `"devuelta"` y abre Pandex otra vez, que lo dice una vez.
- **ACT-06:** `.github/workflows/publicar.yml` con `contents: write` solo en ese job.

## Principios

- **P4:** volver atrás aparta lo agregado, no lo borra; `git reset --keep` se niega a pisar
  cambios tuyos.
- **P3:** `deshecho-*` va a `respaldos/` y entra en su límite de 3.
- **P8:** cada fallo dice qué pasó y qué hacer.

## Archivos que se tocan

| Archivo | Cambio |
|---|---|
| `pandex/actualizar.py` | versiones publicadas, SHA-256, punto de vuelta |
| `pandex/vuelta.py` | nuevo: guardar, volver y vuelta automática |
| `pandex/ui/actualizacion.py` | sin «un clic»; botón «Volver a la versión anterior» |
| `pandex/app.py` | el clic abre la ventana; aviso tras volver |
| `main.py` | marca el arranque y vuelve si la versión nueva no abre |
| `.github/workflows/publicar.yml` | nuevo |
