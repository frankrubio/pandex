# 011 · Tienda de plugins y extensiones

> Estado: aprobada · Prefijo: `PLG` · Principios: P1, P3, P4, P5, P8, P9, P10

## Por qué

Pandex ya carga tareas desde `tasks/`, pero no tiene distribución, revisión, permisos,
plugins personales persistentes ni una interfaz para descubrir funciones nuevas. La tienda
debe ampliarla sin volver pesado ni inseguro al núcleo.

## Qué existe hoy

- Contrato de tareas en `pandex/tareas.py`.
- Descubrimiento tolerante a errores.
- Datos personales fuera del proyecto en `rutas.DATOS`.
- Desinstalación que separa proyecto, datos y carpeta de cursos.
- Personajes personales que sobreviven a actualizaciones.

## Requisitos

| Id | Requisito | Se comprueba con |
|---|---|---|
| PLG-01 | Cada plugin tiene `manifest.json` con id, nombre, versión semántica, entrada Python, licencia y permisos. | `tests/test_plugins.py::Manifiestos` |
| PLG-02 | El id usa minúsculas ASCII y `_`; no puede repetirse entre plugins cargados. | `test_plugins.py::test_id_unico` |
| PLG-03 | Una entrada no puede salir de su carpeta ni apuntar a otro sistema o ejecutable. | `test_plugins.py::test_manifest_rechaza_rutas_inseguras` |
| PLG-04 | Un ZIP no puede contener rutas de escape ni superar 100 MB. | `test_plugins.py::test_instalar_zip_impide_ruta_de_escape` |
| PLG-05 | Los plugins personales viven en `DATOS/plugins_personales/<id>` y no en `tasks/` ni Git. | `test_plugins.py::test_directorio_personal_esta_fuera_del_repositorio` |
| PLG-06 | Actualizar Pandex no modifica los plugins personales. | prueba de actualización con una copia real temporal |
| PLG-07 | Desinstalar Pandex conserva los plugins personales por defecto y solo los elimina con `--borrar-plugins-personales` o confirmación explícita. | `tests/test_residuos.py::DesinstalarConPluginsPersonales` |
| PLG-08 | Solo Frank puede aprobar/publicar. El catálogo registra autor, licencia, versión, huella y estado. | revisión del flujo de PR y catálogo |
| PLG-09 | Instalar muestra los permisos antes de copiar o ejecutar y requiere confirmación. | prueba de UI y revisión manual |
| PLG-10 | Un plugin roto no tumba Pandex ni impide cargar los demás. | `test_plugins.py::test_plugin_roto_se_salta` |
| PLG-11 | Ningún plugin puede acceder a rutas, procesos o hosts no declarados por su manifiesto. | pruebas de API restringida |
| PLG-12 | La tienda permite buscar, filtrar, ver detalles, instalar, actualizar, desactivar y eliminar. | prueba de UI por Ventana y teclado |
| PLG-13 | Los textos son español de Perú breve; colores e iconos siguen `pandex/ui/tema.py`. | revisión + pruebas de interfaz |
| PLG-14 | Cada plugin nuevo tiene manual, licencia, changelog y pruebas sin datos reales. | revisión manual antes de publicar |

## Escenarios

**PLG-09 · Instalar desde la tienda**
- *Dado* un plugin publicado válido
- *Cuando* el usuario abre sus detalles y pulsa Instalar
- *Entonces* ve nombre, propietario, licencia y permisos; confirma; Pandex descarga, valida
  huellas y carga sin abrir otro programa.

**Error · Plugin corrupto**
- *Cuando* se intenta cargar un paquete con archivo de entrada faltante
- *Entonces* se muestra qué falta y qué hacer, se conserva la versión anterior y no cae la app.

**Error · Permiso nuevo**
- *Cuando* una versión pide `calendario.escribir` aunque la anterior no
- *Entonces* Pandex requiere confirmación nueva y no actualiza hasta aceptarla.

## Fuera de alcance

- Pagos y ventas dentro de Pandex.
- Plugins en otros lenguajes o DLL sin revisión separada.
- Ejecución remota de código desde el catálogo.
- Claves privadas o credenciales dentro de paquetes.

## Preguntas abiertas

| # | Pregunta | Por defecto | Decide |
|---|---|---|---|
| 1 | ¿El catálogo vive en una rama protegida del mismo repositorio o en GitHub Releases? | GitHub Releases + catálogo versionado; sin servidor propio. | Frank |
| 2 | ¿La aprobación se registra como PR o issue etiquetado? | PR protegido hacia `main`; la etiqueta no reemplaza la aprobación. | Frank |

## Historial

| Fecha | Cambio | Por qué |
|---|---|---|
| 2026-11-18 | Primera especificación. | Separar tienda, plugins personales y permisos antes de implementar. |
