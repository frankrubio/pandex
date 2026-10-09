# Ayuda: la primera vez, dudas y errores

Esta guía muestra lo que vas a ver al usar Pandex por primera vez, responde las dudas más comunes y explica qué hacer cuando algo falla.

## Qué vas a ver la primera vez

**1. Al descargar.** Si te saltas el paso de **Desbloquear** el ZIP, Windows puede frenarte más adelante con dos tipos de aviso:
- Al abrir `instalar.bat`, una ventana azul que dice *"Windows protegió tu PC"*.
- Al abrir Pandex, un aviso del *Control inteligente de aplicaciones*.

Si ya lo desbloqueaste, no aparece ninguno. Más abajo, en [Errores frecuentes](#errores-frecuentes), está cómo arreglarlo si ya extrajiste el ZIP.

**2. Al instalar (`instalar.bat`).** Se abre una ventana negra con texto. Es normal, no la cierres.

```
 ===  Instalando Pandex  ===

Creando el entorno virtual...
Instalando dependencias: la primera vez tarda unos minutos...

 Listo. Abre Pandex con el acceso directo "Pandex" de tu Escritorio.
```

- Puede parecer congelada de 2 a 5 minutos mientras descarga. Está trabajando.
- Si no tienes Google Chrome, también descarga un navegador para entrar a Canvas. Eso agrega un par de minutos.
- Al final dice **Listo** y pide presionar una tecla. En tu Escritorio aparece **Pandex** con la cara de Rusty.

**3. Al abrir Pandex.** Rusty aparece en una esquina de la pantalla con un globo que dice *"¡Buenas tardes! Soy Pandex. Clic derecho para ver lo que puedo hacer."* (o buenos días o buenas noches, según la hora). No se abre ninguna ventana grande: **Pandex es la mascota**. También queda un ícono junto al reloj de Windows.

**4. El asistente de Canvas.** Segundo y medio después aparece *"Antes de empezar, configuremos «Sincronizar Canvas»"* y se abre el asistente:

| Paso | Qué haces |
|---|---|
| Conectemos tu Canvas | Escribes la dirección, por ejemplo `https://utec.instructure.com`. |
| Iniciar sesión | Se abre el navegador. Entras con tu cuenta de la universidad, como siempre, y la ventana se cierra sola. Tienes 5 minutos. |
| Tus cursos | Marcas los cursos que quieres. Puedes cambiar el nombre de su carpeta. |
| ¿Dónde guardo tus cursos? | Una carpeta nueva (te recomendamos dentro de OneDrive) o una donde ya tengas tus cursos: Pandex la ordena sin borrar nada. |
| Descarga inicial | Todo lo publicado, solo desde una semana o nada por ahora. Opcional: revisar Canvas todos los días a una hora. |
| Todo listo | Un resumen. Al pulsar **Terminar** empieza la primera descarga. |

Si eliges una carpeta donde ya tienes tus cursos, aparecen dos pasos más: confirmar qué carpeta es de cada curso y ver qué archivos se moverían. Ese reordenamiento se puede deshacer.

**5. La primera descarga.** Rusty pone cara de concentrado y el globo muestra una barra de avance. Al terminar dice algo como *"✓ 42 nuevo(s): Cálculo, Física…"* y abre un resumen. La primera vez puede tardar varios minutos si tus cursos tienen mucho material.

**6. Las siguientes veces.** El navegador ya no se abre, porque Pandex recuerda tu sesión. Solo baja lo nuevo, y si no hay nada te dice *"Nada nuevo"*.

## Dudas y respuestas

**¿Pandex guarda mi contraseña?**
No. Inicias sesión tú, en el navegador. Pandex solo usa la sesión que queda abierta, igual que cuando Chrome te recuerda.

**¿Dónde quedan mis archivos?**
En la carpeta que elegiste en el asistente, ordenados así: `Curso / Sem 3 / Material de clase / archivo.pdf`. Para abrirla rápido, usa el botón **Abrir carpeta** del resumen que aparece al terminar de sincronizar.

**¿Borra o reemplaza mis archivos?**
Nunca. Sincronizar solo crea archivos. Si ya hay uno con ese nombre en su lugar, lo deja como está y no lo vuelve a bajar.

**¿Tengo que dejarlo abierto?**
Solo si activaste la revisión diaria. Si Pandex está cerrado a esa hora, ese día no revisa nada. Puedes sincronizar a mano cuando quieras. Para que se abra solo al encender la PC: **Configuración → Comportamiento → Arrancar con Windows**.

**¿Consume mucha batería o memoria?**
No. Rusty es una imagen quieta: sin hacer nada usa 0 % de CPU y unos 70 MB de memoria. Solo trabaja cuando le pides algo o a la hora que programaste.

**¿Dónde se guardan los `.md` cuando convierto a Markdown?**
Junto a cada archivo original y con el mismo nombre: `Clase 3.pdf` → `Clase 3.md`. Si ya existe un `.md`, no lo vuelve a convertir, salvo que marques *Forzar reconversión*.

**¿Puedo poner mi propio personaje?**
Sí: **Configuración → Apariencia → Añadir personaje…**, eliges la imagen y le pones nombre. Sirve un PNG, GIF o JPG:
- **Una sola imagen:** se usa para todos los estados.
- **Varias poses del mismo tamaño, una al lado de otra:** van en este orden: normal, trabajando, feliz y error.
- **Un GIF:** cada cuadro es una pose, en ese mismo orden.

Si la imagen tiene fondo blanco u otro color liso, Pandex lo quita. El personaje aparece en la lista con «(tuyo)». Pulsa **Guardar** para usarlo.

**¿Cómo lo cierro o lo escondo?**
Clic derecho en Rusty → **Ocultar**, o **Salir**. Si lo ocultas, vuelve a aparecer al hacer clic en su ícono junto al reloj.

**¿Cómo me entero de una versión nueva?**
Pandex revisa una vez al día mientras está abierto. Si hay una versión nueva, Rusty te avisa: haz clic sobre él y Pandex se descarga, se actualiza y se reinicia solo. Tus cursos y tu configuración no se tocan.

**Empezó el ciclo nuevo y no aparecen mis cursos.**
Clic derecho → **Configurar Canvas…** y vuelve a marcar tus cursos. La lista anterior se guarda en una copia.

**¿Puedo moverlo a otra carpeta?**
Mejor no, porque el acceso directo apunta a la carpeta original. Si ya lo moviste, abre **`Pandex.pyw`** desde su carpeta nueva y crea de nuevo el acceso directo: **Configuración → Comportamiento → Crear en el Escritorio**.

**¿Funciona en Mac o Linux?**
No. Pandex está hecho para Windows 10 y 11.

## Errores frecuentes

| Lo que ves | Por qué pasa | Qué hacer |
|---|---|---|
| *"Windows protegió tu PC"* al abrir `instalar.bat` | No desbloqueaste el ZIP antes de extraerlo. | **Más información → Ejecutar de todas formas**. Después desbloquea toda la carpeta con el comando de la fila siguiente. |
| *Control inteligente de aplicaciones* bloquea Pandex | Lo mismo: los archivos traen la marca de "descargado de internet". | En PowerShell: `Get-ChildItem "ruta\de\pandex-main" -Recurse \| Unblock-File`. No desactives el Control inteligente de aplicaciones. |
| *"No encontré Python 3.12 o más nuevo"* | Python no está instalado, o lo instalaste sin marcar **Add python.exe to PATH**. | Vuelve a abrir el instalador de Python → **Modify** (o instálalo de nuevo) y marca esa casilla. Luego repite `instalar.bat`. |
| La ventana negra se cierra sola o dice *"Algo falló"* | Casi siempre es el internet durante la descarga. | Vuelve a abrir `instalar.bat`: continúa desde donde quedó. |
| *"Falta instalar Pandex: haz doble clic en instalar.bat"* | Abriste Pandex sin haberlo instalado, o borraste la carpeta `.venv`. | Doble clic en `instalar.bat`. |
| El acceso directo no hace nada o dice que no encuentra el archivo | Moviste o renombraste la carpeta de Pandex. | Doble clic en `Pandex.pyw` y vuelve a crear el acceso directo (ver arriba). |
| *"¡Aquí estoy! Ya estaba abierto."* | Pandex ya estaba abierto, quizás escondido. | No es un error. Solo puede haber un Rusty a la vez. |
| *"Cerraste el navegador antes de terminar de iniciar sesión"* o *"Se acabó el tiempo…"* | Se cerró la ventana del login, o pasaron 5 minutos. | En el asistente, pulsa **Reintentar**. Si fue al sincronizar, vuelve a pulsar **Sincronizar Canvas**. |
| *"No encontré un navegador"* | No tienes Chrome, y la descarga del navegador alternativo falló. | Instala Google Chrome. |
| *"No hay conexión: no pude llegar a Canvas"* | Sin internet, o el wifi de la universidad pide iniciar sesión. | Revisa que Canvas abra en tu navegador y vuelve a intentarlo. |
| *"No reconocí ninguno de tus cursos en Canvas"* | Empezó otro ciclo y tus cursos cambiaron. | Clic derecho → **Configurar Canvas…** |
| *"No encuentro tu carpeta de cursos"* | Moviste, renombraste o borraste esa carpeta, o OneDrive no terminó de sincronizar. | Devuélvela a su lugar, o elige otra en **Configurar Canvas…** |
| *"N aún sin abrir en Canvas"* (🔒) | El docente programó esos archivos para más adelante. | Nada: Pandex los baja solo cuando se abran. |
| *"N no se pudieron bajar"* | Un archivo dio error (internet, archivo dañado en Canvas). | Vuelve a sincronizar. Si se repite, mira el motivo en **Ver registro**. |
| Al convertir: *"La conversión se cerró de golpe"* | Un archivo muy pesado o dañado. | Conviértelo solo, o déjalo fuera. El motivo está en **Ver registro**. |
| Rusty desapareció | Lo ocultaste, o quedó en otra pantalla que desconectaste. | Clic en el ícono de Pandex junto al reloj, o abre el acceso directo otra vez. |

**¿Nada de esto?** Clic derecho en Rusty → **Ver registro**: ahí se explica cada decisión y cada error. Si aun así no lo entiendes, [abre un issue](https://github.com/frankrubio/pandex/issues/new/choose) y pega lo que dice el registro. Antes de pegarlo, borra cualquier dato personal.
