# 005 · Interfaz bonita y configuración fácil

> Estado: aprobada  ·  Prefijo: `IU`  ·  Principios: P8, P5, P2

## Por qué

Pandex lo usan estudiantes que no programan. La interfaz tiene que ser **bonita, simple,
concisa y funcional**, y configurar la mascota tiene que ser fácil. «Bonita» y «fácil» no se
pueden probar con sí o no, así que esta spec los traduce a reglas medibles.

## Qué existe hoy

- Una sola hoja de estilos con paleta clara/oscura (`pandex/ui/tema.py`) que sigue al sistema.
- Configuración con barra lateral: Apariencia, Comportamiento, Tareas, Acerca de
  (`pandex/ui/configuracion.py`), con vista previa de la mascota.
- Asistente de Canvas en pasos (`pandex/canvas/asistente.py`) que sugiere la carpeta de
  OneDrive institucional si existe.
- La mascota aparece en el monitor correcto y respeta la escala de pantalla (`ui/mascota.py`).
- Horarios sin cron («Todos los días», «De lunes a viernes»).

## Requisitos

### Aspecto

| Id | Requisito | Se comprueba con |
|---|---|---|
| IU-01 | Ningún color, tamaño de letra ni radio está escrito fuera de `pandex/ui/tema.py` (salvo los dibujos de personajes). | `tests/test_interfaz.py::test_colores_solo_en_tema` (busca `#RRGGBB` y `font-size` en `pandex/**/*.py`) |
| IU-02 | Todo par texto/fondo de las paletas clara y oscura tiene contraste ≥ 4,5:1 (WCAG AA); los textos grandes y los íconos, ≥ 3:1. | `test_contraste_de_paletas` (calcula el contraste desde `CLARO` y `OSCURO`) |
| IU-03 | Todo botón tiene texto o nombre accesible, y toda ventana se puede usar solo con el teclado (Tab llega a cada control, Esc cierra, Enter acepta). | `test_botones_con_nombre`, `test_orden_de_tabulacion` |
| IU-04 | Configuración abre en ≤ 300 ms en la PC de referencia (≤ 1 s en la CI). | `test_configuracion_abre_rapido` |
| IU-05 | Las capturas del README coinciden con la interfaz: todo PR que cambie la interfaz regenera `docs/img/` con `herramientas/capturas.py`. | checklist del PR |

### Simple y conciso

| Id | Requisito | Se comprueba con |
|---|---|---|
| IU-06 | El globo de la mascota muestra como máximo **2 líneas**; lo largo va al informe. | `test_globo_maximo_dos_lineas` |
| IU-07 | Todo mensaje de error dice **qué pasó y qué hacer**, en español de Perú neutro, sin jerga ni trazas. El detalle técnico va al registro. | revisión + `test_errores_conocidos_tienen_accion` (recorre los mensajes de `mensaje_de_error`, `ErrorExtra`, `ErrorActualizacion`…) |
| IU-08 | Cada ventana tiene **una** acción principal resaltada (botón con estilo de acento). | `test_una_accion_principal_por_ventana` |

### Configuración fácil

| Id | Requisito | Se comprueba con |
|---|---|---|
| IU-09 | La primera vez, el usuario solo **escribe** la dirección de su Canvas e inicia sesión; cursos, carpeta y qué bajar vienen sugeridos y se aceptan con «Siguiente». | `tests/test_asistente.py::test_primera_vez_solo_con_la_url` |
| IU-10 | Toda opción que el usuario pueda querer cambiar está en la interfaz; `config.json` nunca hace falta editarlo. Las claves internas (posición, `version_config`…) están marcadas como internas. | `test_toda_clave_tiene_control_o_es_interna` |
| IU-11 | Cada cambio en Configuración se ve en la vista previa al instante y se puede deshacer con **Cancelar**. | `test_cancelar_no_guarda` |
| IU-12 | Configuración tiene **Restablecer valores** por página (no borra cursos ni personajes propios). | `test_restablecer_apariencia` |

### Se adapta a tu PC (solo leyendo)

| Id | Requisito | Se comprueba con |
|---|---|---|
| IU-13 | Sigue el modo claro/oscuro del sistema y cambia si el sistema cambia, sin reiniciar. | `test_cambia_con_el_sistema` |
| IU-14 | Si el sistema pide **menos animación** (Windows: «Efectos de animación» apagado; GNOME/Cinnamon: `enable-animations=false`), la mascota no se anima y las transiciones se apagan. | `test_respeta_menos_animacion` |
| IU-15 | Sugiere la carpeta destino según lo que encuentre: OneDrive institucional → OneDrive personal → Documentos (Windows: variables `OneDriveCommercial`/`OneDrive`; Linux: montajes de rclone de Pandex o `~/OneDrive*`). | `test_carpeta_sugerida_*` |
| IU-16 | Usa el navegador que ya tienes (ver 002, PES-07) y el nombre de las carpetas del sistema en tu idioma (Escritorio/Desktop). | existentes en `test_linux.py` |
| IU-17 | Nada de lo anterior **cambia** la configuración del sistema: solo se lee (P2). | revisión + `test_residuos.py` (003) |

## Escenarios

**IU-09 · Primera vez**
- *Dado* un usuario que abre Pandex recién instalado
- *Cuando* escribe `https://utec.instructure.com`, inicia sesión y pulsa «Siguiente» hasta el
  final
- *Entonces* queda configurado con los cursos del ciclo, la carpeta sugerida y la descarga
  inicial elegida, sin haber escrito nada más.

**IU-14 · Menos animación**
- *Dado* Windows con «Efectos de animación» apagado
- *Cuando* la mascota trabaja
- *Entonces* muestra la pose fija de «trabajando», sin cuadros animados.

**Error · URL mal escrita**
- *Cuando* escribe `utec.instructure` (sin `.com`)
- *Entonces* el asistente dice «No encontré un Canvas en esa dirección. Revisa que termine
  en .com o .edu, por ejemplo https://utec.instructure.com» y no avanza.

## Fuera de alcance

- Rediseñar la identidad visual (Rusty, paleta cálida, azul del panda). Cualquier cambio
  grande de aspecto necesita una maqueta aprobada por Frank antes de programar.
- Otros idiomas además del español.
- Temas personalizados por el usuario.

## Preguntas abiertas

| # | Pregunta | Por defecto | Decide |
|---|---|---|---|
| 1 | ¿Se usa el color de acento del sistema (Windows/GNOME) en vez del azul del panda? | No: el azul es parte de la identidad. | Frank |
| 2 | ¿Las acciones menos usadas del menú (Recargar tareas, Ver registro, Buscar actualizaciones) pasan a un submenú «Más»? | Sí, si el menú supera 9 entradas. | Frank |

## Historial

| Fecha | Cambio | Por qué |
|---|---|---|
| 2026-10-19 | Primera versión. | Requisitos de Frank: interfaz bonita, simple, concisa y funcional; configuración fácil; adaptarse a la PC. |
