## Qué cambia

<!-- Una o dos frases. -->

**Tarea:** T___._  ·  **Requisitos:** ___-__  ·  **Spec:** specs/___/

## Cómo se probó

- [ ] La prueba nueva fallaba antes del cambio (pega la salida o el nombre de la prueba).
- [ ] Toda la suite pasa: `python -m unittest discover -s tests -t .`
- [ ] `main.py --test` abre y se cierra solo.
- [ ] Probado a mano en: ☐ Windows  ☐ Linux (distribución: ____ )

<!-- Si toca rendimiento o peso, pega aquí las líneas «fases:» o la salida de medir_peso.py, antes y después. -->

## Principios (specs/principios.md)

- [ ] **P1 Privacidad:** no se registran ni guardan contraseñas, cookies, tokens ni datos personales; nada personal en el diff.
- [ ] **P2/P3 Sistema y residuos:** no escribe fuera de los lugares permitidos; lo que crece tiene límite.
- [ ] **P4 Nada destructivo:** no borra, mueve ni pisa archivos del usuario sin confirmación y deshacer.
- [ ] **P5 Liviano:** sin dependencias nuevas, o con su peso medido y su spec.
- [ ] **P7 Windows y Linux:** lo que depende del sistema está detrás de `rutas.WINDOWS` y probado en los dos.
- [ ] **P8 Simple:** textos en español de Perú neutro; horas en 12 h; errores dicen qué hacer.

## Documentación

- [ ] `CHANGELOG.md` (si el usuario lo nota) y versión en `pandex/__init__.py`.
- [ ] `docs/` actualizado si cambió cómo funciona; capturas regeneradas si cambió la interfaz.
- [ ] Tarea marcada en su `tareas.md` y en `specs/tablero.md`.
