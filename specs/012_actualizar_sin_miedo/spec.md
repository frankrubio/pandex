# 012 · Actualizar sin miedo

> Estado: en curso  ·  Prefijo de requisitos: `ACT`
> Principios que toca: P3 (sin residuos), P4 (nada destructivo), P8 (mensajes claros)

## Por qué

Hasta la 2.6.7, un clic en la mascota con el aviso «Hay una versión nueva» descargaba, copiaba y
reiniciaba sin preguntar. Se instalaba el último commit de `main`, sin una versión publicada ni
una huella que comprobar. Si la versión nueva no abría, no había forma de volver atrás desde
Pandex: había que copiar a mano lo que estaba en `respaldos/`.

## Qué existe hoy

- `pandex/actualizar.py`: `buscar()` lee la versión de `main` en GitHub; `aplicar()` actualiza con
  `git pull --ff-only` o copiando el ZIP de `main`, con respaldo de lo reemplazado en
  `DATOS/respaldos/` (máximo 3). Nunca toca `config.json`, `logs/`, `.venv/` ni tus tareas.
- `pandex/ui/actualizacion.py`: la ventana «Buscar actualizaciones…».
- `limpiar_obsoletos()`: la versión nueva aparta (no borra) los archivos que ya no usa.

## Requisitos

| Id | Requisito | Se comprueba con |
|---|---|---|
| ACT-01 | Nada se descarga ni se instala sin que pulses **Actualizar ahora**. El clic en la mascota, el aviso de la bandeja y el menú abren la ventana con las novedades. | `tests/test_actualizar.py::Confirmar` |
| ACT-02 | Pandex se actualiza a la última **versión publicada** en GitHub (etiqueta `vX.Y.Z`), no al último commit de `main`. El ZIP publicado trae su SHA-256 (`pandex-X.Y.Z.zip.sha256`); si no coincide o falta, no se toca nada. Mientras el repositorio no tenga ninguna versión publicada, se usa `main` como hasta la 2.6.7. | `tests/test_actualizar.py::Publicadas` |
| ACT-03 | Antes de copiar, Pandex guarda un **punto de vuelta** en `DATOS/actualizacion.json`: la versión anterior y, según el modo, el respaldo de lo reemplazado y la lista de lo agregado (ZIP) o el commit anterior (git). | `PuntoDeVuelta::test_zip_guarda_el_punto`, `test_git_guarda_el_commit` |
| ACT-04 | **Volver a la versión anterior** (ventana «Buscar actualizaciones…», con confirmación) devuelve lo reemplazado y lo apartado como obsoleto, y aparta lo agregado en `DATOS/respaldos/deshecho-<versión>` (no lo borra). Con git usa `git reset --keep`, que no pisa cambios tuyos. | `PuntoDeVuelta::test_volver_con_zip`, `test_volver_con_git` |
| ACT-05 | Si la versión nueva **no abre**, Pandex vuelve solo a la anterior, lo anota y al abrir lo dice: «La versión X no abrió; volví a la Y.» | `VueltaAutomatica` |
| ACT-06 | Al empujar una etiqueta `vX.Y.Z`, la CI comprueba que coincide con `pandex/__init__.py`, arma el ZIP con `git archive`, calcula su SHA-256 y publica la versión con la sección del `CHANGELOG.md`. | `.github/workflows/publicar.yml` (se ve en la primera etiqueta) |

## Escenarios

**ACT-01 · Hay versión nueva**
- *Dado* que la mascota dice «¡Hay una versión nueva (2.8.0)!»
- *Cuando* haces clic en ella
- *Entonces* se abre la ventana con las novedades y el botón «Actualizar ahora»; nada cambia
  hasta que lo pulsas.

**ACT-02 · Descarga dañada**
- *Cuando* el ZIP descargado no coincide con su SHA-256
- *Entonces* la ventana dice «Lo descargado no coincide con la versión publicada; no toqué nada.
  Vuelve a intentar.» y tu carpeta queda igual.

**ACT-05 · La versión nueva no abre**
- *Dado* que actualizaste y Pandex se reinició
- *Cuando* la versión nueva falla al arrancar
- *Entonces* Pandex devuelve los archivos de la anterior, se abre otra vez y dice qué pasó.

## Fuera de alcance

- Volver atrás las dependencias de `.venv` (las nuevas suelen servir a la versión anterior; si
  no, `instalar.bat`/`./instalar.sh` lo repara).
- Un fallo que impide hasta leer `main.py` (por ejemplo, un error de sintaxis en él): ahí no
  corre nada de Pandex. Se cubre con la CI (`main.py --test` en cada PR).
- Firmar las versiones con una clave propia: la huella viene de la misma fuente (GitHub) y
  protege contra descargas cortadas o cambiadas en el camino, no contra un GitHub comprometido.

## Preguntas abiertas

| # | Pregunta | Por defecto | Decide |
|---|---|---|---|
| 1 | ¿Se quita el respaldo de `main` cuando ya haya versiones publicadas? | Se mantiene: solo se usa si no hay ninguna versión publicada. | Frank |

## Historial

| Fecha | Cambio | Por qué |
|---|---|---|
| 2026-11-15 | Primera versión. | Revisión de UX y seguridad (F4): instalar sin confirmar, sin versión publicada ni forma de volver atrás. |
