# 005 · Plan

## Enfoque

1. **Primero las pruebas de reglas** (IU-01, IU-02, IU-03, IU-06): son baratas, encuentran
   lo que hoy está fuera de norma y evitan que vuelva. Lo que encuentren se arregla en PRs
   pequeños, uno por ventana.
2. **Configuración fácil** (IU-09 a IU-12): partir de `tests/test_asistente.py`, que ya maneja
   el asistente por código, y medir cuántos campos hay que tocar. Añadir «Restablecer» y
   marcar claves internas en `config.py` (`INTERNAS = {...}`).
3. **Adaptarse a la PC** (IU-13 a IU-15): una sola función `pandex/sistema.py → preferencias()`
   que devuelve un `dict` (`oscuro`, `menos_animacion`, `carpetas_sugeridas`, `navegador`)
   leyendo el sistema **una vez** al arrancar y cuando Qt avisa un cambio
   (`QStyleHints.colorSchemeChanged`). Todo lo demás consulta esa función: así hay un solo
   lugar para leer el sistema y un solo lugar para simularlo en las pruebas.
   - Windows, menos animación: `SystemParametersInfoW(SPI_GETCLIENTAREAANIMATION)` con `ctypes`
     (sin dependencias).
   - Linux: `gsettings get org.gnome.desktop.interface enable-animations` (o
     `org.cinnamon.desktop.interface`), con tiempo límite de 1 s y valor por defecto si falla.
4. **Diseño:** cualquier cambio visual grande se propone primero con una captura o maqueta en
   el PR (o issue) y espera el visto bueno de Frank.

## Principios

- P8 es el objetivo. P2: `sistema.py` solo lee. P5: nada de dependencias nuevas; las lecturas
  del sistema son de milisegundos y se hacen una vez.

## Archivos que se tocan

| Archivo | Cambio |
|---|---|
| `tests/test_interfaz.py` | nuevo: reglas IU-01 a IU-08 |
| `pandex/sistema.py` | nuevo: `preferencias()` |
| `pandex/ui/tema.py` | usa `sistema`; reacciona a cambios |
| `pandex/ui/mascota.py` | respeta `menos_animacion` |
| `pandex/canvas/asistente.py` | `_carpeta_sugerida` pasa a `sistema`; validación de URL |
| `pandex/config.py` | `INTERNAS` |
| `pandex/ui/configuracion.py` | «Restablecer valores» |

## Riesgos

| Riesgo | Qué se hace |
|---|---|
| Las pruebas de interfaz son frágiles | Se prueban reglas (colores, nombres, contraste), no posiciones en píxeles. |
| `gsettings` no existe (KDE, XFCE) | Valor por defecto: animaciones activas; se registra una vez. |
