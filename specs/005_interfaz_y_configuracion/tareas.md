# 005 · Tareas

## T005.1 · Reglas de aspecto como pruebas

- **Requisitos:** IU-01, IU-02, IU-03
- **Depende de:** —
- **Prueba primero:** `tests/test_interfaz.py`: `test_colores_solo_en_tema`,
  `test_contraste_de_paletas`, `test_botones_con_nombre`, `test_orden_de_tabulacion`
  (Configuración, asistente, informe, registro, actualización).
- **Cambio:** solo las pruebas. Los casos que hoy fallan se listan en el PR y se crea una
  tarea `T005.1x` por ventana para arreglarlos.
- **Terminado cuando:** las pruebas corren; lo que falla está documentado con su tarea.

## T005.2 · Globo conciso y errores con acción

- **Requisitos:** IU-06, IU-07
- **Depende de:** —
- **Prueba primero:** `test_globo_maximo_dos_lineas` (texto de 300 caracteres → 2 líneas y
  «…»), `test_errores_conocidos_tienen_accion` (cada mensaje conocido tiene un verbo de acción:
  «Instala», «Revisa», «Vuelve a», «Abre»…).
- **Cambio:** `ui/globo.py`; reescribir los mensajes que no pasen.
- **Terminado cuando:** pruebas en verde.

## T005.3 · Una acción principal por ventana

- **Requisitos:** IU-08
- **Depende de:** T005.1
- **Prueba primero:** `test_una_accion_principal_por_ventana` (exactamente un botón con la
  propiedad `primario=True`).
- **Cambio:** marcar el botón principal en cada diálogo; estilo en `tema.py`.
- **Terminado cuando:** prueba en verde; capturas regeneradas (IU-05).

## T005.4 · Primera vez solo con la URL

- **Requisitos:** IU-09
- **Depende de:** —
- **Prueba primero:** `tests/test_asistente.py::test_primera_vez_solo_con_la_url` y
  `test_url_mal_escrita_no_avanza`.
- **Cambio:** valores sugeridos donde falten; validación de la URL con mensaje claro.
- **Terminado cuando:** pruebas en verde.

## T005.5 · Configuración sin JSON

- **Requisitos:** IU-10, IU-11, IU-12
- **Depende de:** —
- **Prueba primero:** `test_toda_clave_tiene_control_o_es_interna`, `test_cancelar_no_guarda`,
  `test_restablecer_apariencia`.
- **Cambio:** `config.INTERNAS`; controles que falten; botón «Restablecer valores».
- **Terminado cuando:** pruebas en verde.

## T005.6 · Leer las preferencias del sistema en un solo lugar

- **Requisitos:** IU-13, IU-14, IU-15, IU-17 (IU-16 ya está cubierto por `tests/test_linux.py` y por T002.5)
- **Depende de:** —
- **Prueba primero:** `tests/test_interfaz.py::Sistema`
  - `test_cambia_con_el_sistema` (se emite `colorSchemeChanged` simulado → la hoja de estilos
    cambia);
  - `test_respeta_menos_animacion` (`sistema.preferencias` simulado → `mascota.animar` falso);
  - `test_carpeta_sugerida_onedrive_institucional`, `..._personal`, `..._documentos`;
  - `test_sistema_no_escribe` (con `subprocess.run` simulado, nunca se llama a `gsettings set`
    ni a `reg add`).
- **Cambio:** `pandex/sistema.py`; usarlo en `tema.py`, `mascota.py`, `asistente.py`.
- **Terminado cuando:** pruebas en verde en Windows y Linux.

## T005.7 · Configuración abre rápido

- **Requisitos:** IU-04
- **Depende de:** —
- **Prueba primero:** `test_configuracion_abre_rapido` (≤ 1 s en la CI, mediana de 3).
- **Cambio:** solo si falla (cargar páginas al mostrarlas).
- **Terminado cuando:** prueba en verde; medición real ≤ 300 ms anotada.
