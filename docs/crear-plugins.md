# Crear y enviar plugins

## Preparar

1. Crea un paquete con `manifest.json` y un único archivo Python de entrada.
2. Declara id, nombre, versión semántica, licencia, descripción y permisos mínimos.
3. Mantén la lógica reutilizable en `pandex/` y el archivo de `tasks/` delgado.
4. Usa solo datos necesarios. No guardes contraseña, cookie, token o clave privada.
5. Incluye pruebas con datos falsos y no hagas cambios destructivos.

## Manifiesto mínimo

```json
{
  "id": "mi_plugin",
  "nombre": "Mi plugin",
  "version": "1.0.0",
  "entrada": "plugin.py",
  "descripcion": "Qué hace",
  "licencia": "MIT",
  "permisos": ["datos.tareas", "avisos.locales"]
}
```

## Permisos disponibles

- `red.departamento`: comunicarte con el servicio autorizado de Depa.
- `red.google`: usar Google con OAuth y endpoints oficiales.
- `red.proveedor_ia`: usar un proveedor autorizado.
- `datos.tareas`: leer o actualizar tareas permitidas.
- `calendario.leer`: consultar eventos.
- `calendario.escribir`: crear o actualizar eventos solo con confirmación.
- `ia.delegar`: pedir acciones al proveedor autorizado.
- `avisos.locales`: crear avisos dentro de Pandex.
- `almacenamiento.plugin`: guardar estado propio en `DATOS/plugins_personales`.

## Enviar

Envía el ZIP, su huella SHA-256, licencia, cambios y pruebas. Frank debe aprobar el PR
antes de publicar una versión.

## Lista rápida de aprobación

- [ ] Código y paquete coinciden con el manifiesto.
- [ ] Licencia permite redistribución y cada imagen o dependencia tiene crédito.
- [ ] No hay secretos, claves privadas, cookies, tokens ni datos reales.
- [ ] Los permisos son mínimos y no hay APIs ocultas.
- [ ] Solo usa hosts declarados.
- [ ] No abre procesos, sockets, DLL ni módulos destructivos.
- [ ] No escribe fuera de `DATOS/plugins_personales` salvo permisos autorizados.
- [ ] Actualizar conserva datos y permite deshacer cambios.
- [ ] Desinstalar conserva plugins personales salvo pedido explícito.
- [ ] Pruebas pasan sin internet.
- [ ] Funciona en Windows y Linux con Python 3.12/3.13.
- [ ] Respeta memoria, arranque, interfaz y 12 horas.
- [ ] Los errores dicen qué pasó y qué hacer.
