# Cambios

Cada versión, en lenguaje simple. Pandex muestra la sección de la versión nueva
cuando buscas actualizaciones desde el menú.

## 2.3.1

- **Buscar actualizaciones dice la causa real.** Antes, cualquier falla mostraba «revisa tu
  conexión a internet», aunque hubiera internet (un antivirus que revisa HTTPS, el wifi de
  la universidad o GitHub pidiendo esperar se veían igual). Ahora el mensaje explica qué
  pasó y el motivo exacto queda en «Ver registro».

## 2.3.0

- **Personajes nuevos:** BMO (fan art de *Hora de Aventura*) y un robot blanco con
  detalles cian, los dos en pixel art con el mismo estilo de Rusty. Se eligen en
  Configuración → Apariencia → Personaje.
- **Logo a tu gusto:** en Configuración → Apariencia → Logo, el ícono de Pandex puede
  seguir al personaje o quedar fijo en otro. Cambia en las ventanas, junto al reloj y en
  el acceso directo del Escritorio.
- **Tu propio personaje:** Configuración → Apariencia → **Añadir personaje…** Elige una
  imagen PNG, GIF o JPG, ponle nombre y aparece en la lista. Entiende una imagen sola,
  varias poses en fila (normal, trabajando, feliz, error), un GIF o una mascota de
  Codex Pets (su ZIP, su pet.json o su spritesheet), y quita el fondo liso. Las de
  Codex Pets se mueven mientras trabajan o reaccionan (en reposo, quietas). Pandex
  guarda su propia copia y no duplica una mascota que ya añadiste.
- **Explorador de archivos renovado** en Convertir a Markdown: columnas de estado, tipo,
  tamaño y fecha, ordenar con un clic, buscar en la carpeta (Ctrl+F), abrir en el
  Explorador de Windows, y tu carpeta de cursos de Canvas y el Escritorio en el inicio.
- **Horarios sin cron:** en Configuración → Tareas eliges «Todos los días» o «De lunes a
  viernes» y la hora.
- **Hora en formato de 12 horas** (7:00 p. m.) en todo Pandex: saludo, horarios, informes
  y registro.
- **Saludar es instantáneo** (antes contaba hasta 3) y te dice la hora y la fecha. Al abrir,
  Pandex saluda según la hora del día.
- **Limpieza:** se quitaron el panda robot dibujado («Panda robot»; quien lo usaba pasa a
  Rusty), `Pandex.bat` (hacía lo mismo que `Pandex.pyw`) y herramientas viejas. Si
  actualizaste con el ZIP, Pandex aparta solo esos archivos (quedan en una copia de
  respaldo). El panda robot pixel art sigue disponible como «Panda robot (clásico)».
- Para programadores: cada personaje es una carpeta en `assets/personajes/`, y
  `herramientas/skins/` dibuja los nuevos en el estilo de Rusty.

## 2.2.0

- **Actualizar con un clic:** Pandex revisa una vez al día, mientras está abierto, si
  hay versión nueva (se puede apagar en Configuración → Comportamiento). Si la hay,
  Rusty avisa y **un clic sobre él** la descarga, la aplica y reinicia Pandex.
- **Archivos que el docente programó para más adelante:** Sincronizar Canvas ya no
  los marca como error («Canvas devolvió 403»). Dice «🔒 aún sin abrir en Canvas», con la
  fecha en que se abren si Canvas la informa, y los baja solo cuando se abren.
- **PDF a Markdown más limpio:** las palabras ya no quedan separadas por tabulaciones
  y se quitan las líneas en blanco de sobra.
- **Interfaz pulida:** el menú ya no muestra esquinas negras detrás de los bordes
  redondeados; los botones ya no cortan su texto; las casillas marcadas muestran ✓.
- Corrige un cierre inesperado al cerrar una ventana mientras aparecía.
- README más corto, con pasos claros para descargar e instalar y otras formas de hacerlo.

## 2.1.0

- **Rusty, el panda rojo** (de LuoSKraD, en Codex Pets), es el nuevo personaje,
  con una pose para cada estado. El logo y el ícono también son suyos. El panda robot sigue disponible en Configuración → Apariencia.
- **Interfaz renovada.** Colores cálidos, tipografía más cuidada, esquinas
  redondeadas y modo oscuro que sigue a Windows. Menú con secciones e íconos.
- **Configuración nueva**, con barra lateral, vista previa de la mascota y
  selector de personaje.
- **Globo de diálogo** más claro: un punto de color dice si es un aviso, un éxito
  o un error, y durante una tarea muestra una barra de avance sin parpadear.
- **Buscar actualizaciones…** en el menú: actualiza Pandex con un clic, con
  respaldo de lo reemplazado. Tu configuración, tus cursos y tus tareas propias
  no se tocan.
- **Más liviano.** La mascota es una imagen fija por estado: en reposo no usa CPU.
  Arranca en la mitad de tiempo, el navegador y el programador de horarios se cargan
  solo si se usan, y convertir a Markdown ya no deja ~130 MB ocupados hasta cerrar
  Pandex (corre en un proceso aparte).
- **Acceso directo fácil:** `Pandex.pyw` para abrir con doble clic, y el botón
  Configuración → Comportamiento → Crear en el Escritorio.
- **Registro con filtro**, y avisos y errores resaltados.
- Correcciones: el menú del clic derecho ya no se acumula en memoria; el globo
  aparece en el monitor correcto; los cambios del personaje ahora sí llegan a
  quien actualiza.

## 2.0.0

- Primera versión pública: Sincronizar Canvas, Convertir a Markdown y tareas
  propias en `tasks/`.
