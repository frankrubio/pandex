# 011 · Plan

## Enfoque

Ampliar el descubrimiento existente sin cambiar el contrato público de tareas. Los paquetes
se validan antes de cargar, los personales viven fuera del repositorio y la tienda presenta
manifiestos y permisos en Configuración.

## Principios

- P1/P3/P6: secretos fuera de Git y datos fuera de lugares no autorizados.
- P4: instalar y eliminar exige confirmación; cargar errores no tumba Pandex.
- P5/P6: validación liviana, sin servicios ni temporizadores al arrancar.
- P8/P9: español breve y núcleo reutilizable; tareas delgadas.
- P10: licencia obligatoria y sin activos de terceros sin crédito.

## Archivos que se tocan

| Archivo | Cambio |
|---|---|
| `pandex/plugins.py` | manifiestos, ZIP, carga personal y permisos declarados |
| `pandex/rutas.py` | rutas de plugins personales y publicados |
| `pandex/ui/configuracion.py` | página Extensiones |
| `pandex/desinstalar.py` | conservar personales por defecto |
| `tests/test_plugins.py` | pruebas primero de manifiestos y ZIP |
| `tests/test_residuos.py` | conservación al desinstalar |
| `docs/crear-plugins.md` | creación y lista de aprobación |

Lo que no se toca:
- credenciales reales de usuarios,
- dependencias globales,
- API de IA o Google hasta tener credenciales y permisos.

## Medición

- Suite completa: 357 pruebas.
- Paquete máximo validado: 100 MB.
- Arranque: sin cargar extensiones personalizadas fuera de su descubrimiento explícito.

## Riesgos

| Riesgo | Qué se hace |
|---|---|
| Plugin defectuoso | carga aislada y error en registro |
| ZIP con rutas | validación contra escape antes de copiar |
| Plugin personal eliminado por actualización | carpeta fuera del proyecto y del desinstalador |
| Desinstalar borra credenciales personales | confirmación separada obligatoria |
