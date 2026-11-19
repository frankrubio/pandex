# 014 · Plan

## Enfoque

Crear módulos livianos que usen la biblioteca estándar y el almacén seguro del sistema.
Los proveedores locales se ejecutan como programas separados; las API remotas usan `urllib`
con permisos exactos.

## Archivos

| Archivo | Cambio |
|---|---|
| `pandex/credenciales.py` | lectura y borrado mediante keyring |
| `pandex/ia.py` | proveedores locales y API compatibles |
| `pandex/calendar_google.py` | OAuth, lectura y escritura confirmada |
| `pandex/ui/conexiones.py` | páginas de conexión y permisos |
| `tests/test_conexiones.py` | pruebas de credenciales, IA y Calendar |

## Principios

- P1/P3: credenciales fuera del repositorio.
- P4: sin cambios destructivos ni escritura sin vista previa.
- P5/P6: carga bajo demanda y ejecución en hilo aparte.
- P8: interfaz breve y en español.
