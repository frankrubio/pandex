# Cambios

Cada versión, en lenguaje simple. Pandex muestra la sección de la versión nueva
cuando buscas actualizaciones desde el menú.

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
- **Archivos que el docente programó para más adelante:** Sincronizar Canvas ya no
  los marca como error («Canvas devolvió 403»). Dice «🔒 aún sin abrir en Canvas», con la
  fecha en que se abren si Canvas la informa, y los baja solo cuando se abren.
- Correcciones: el menú del clic derecho ya no se acumula en memoria; el globo
  aparece en el monitor correcto; los cambios del personaje ahora sí llegan a
  quien actualiza.

## 2.0.0

- Primera versión pública: Sincronizar Canvas, Convertir a Markdown y tareas
  propias en `tasks/`.
