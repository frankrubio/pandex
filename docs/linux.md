# Pandex en Linux

Funciona igual que en Windows. Las diferencias: inicias sesión en Canvas con **tu Firefox** (no se
descarga ningún navegador), OneDrive se conecta desde Pandex y el OCR usa Tesseract.

## Instalar (una sola vez)

Todo se hace en la **Terminal** (en Linux Mint: menú → Terminal, o `Ctrl+Alt+T`). Cuando abre, ya
estás en tu carpeta personal (`~`, es decir `/home/tu-usuario`). Copia y pega cada bloque.

**¿Ya lo tienes?** Si `ls ~/pandex/main.py` lo encuentra, no lo descargues otra vez: actualízalo
con clic derecho → **Buscar actualizaciones…** (o `cd ~/pandex && git pull`).

**1. Programas del sistema** (pide tu contraseña; da igual en qué carpeta estés):

```bash
sudo apt install python3-venv git libxcb-cursor0 rclone fuse3
```

`rclone` y `fuse3` son para OneDrive; si no lo vas a usar, puedes quitarlos del comando.

**2. Descargar Pandex** (se crea la carpeta `~/pandex`):

```bash
cd ~
git clone https://github.com/frankrubio/pandex.git
```

Sí, conviene tener el repositorio **clonado con git**: así «Buscar actualizaciones…» se actualiza
con un clic. ¿Prefieres sin git? Descarga el ZIP (**Code → Download ZIP**) y extráelo en tu carpeta
personal; luego renombra la carpeta `pandex-main` a `pandex`. También se actualiza solo.
Elige **una** de las dos formas: con las dos te quedan dos copias (`~/pandex` y `~/pandex-main`).

**3. Instalar** (siempre dentro de la carpeta de Pandex):

```bash
cd ~/pandex
./instalar.sh
```

Te pregunta si quieres **«Convertir a Markdown»** (unos 280 MB más). Si no lo usas, responde `n`:
Pandex queda mucho más liviano y no aparece en el menú. Lo puedes añadir cuando quieras desde
**Configuración → Tareas → Instalar**.

Al final queda **Pandex** en el menú de aplicaciones y en el Escritorio.

## Abrirlo

Desde el menú de aplicaciones (busca «Pandex»), o en la Terminal:

```bash
cd ~/pandex
.venv/bin/python main.py
```

La primera vez te guía para conectar tu Canvas: se abre **tu Firefox** con una ventana aparte
(perfil propio de Pandex: no toca tus pestañas ni tus contraseñas) para que inicies sesión.

## Dónde queda

Pandex no tiene paquete `.deb`, AppImage ni `pip install`: es solo la carpeta `~/pandex` con su
propio Python dentro (`.venv`). No usa `sudo` ni instala nada fuera de estos lugares:

| Qué | Dónde |
|---|---|
| Pandex, su Python, tu configuración y el registro | `~/pandex/` (`.venv/`, `config.json`, `logs/`) |
| Acceso en el menú de aplicaciones | `~/.local/share/applications/pandex.desktop` |
| Acceso en el Escritorio | `~/Escritorio/pandex.desktop` |
| Arrancar al iniciar sesión (si lo activas) | `~/.config/autostart/pandex.desktop` |
| Abrirse sola a su hora (si lo activas) | `~/.config/systemd/user/pandex.service` y `pandex.timer` |
| Tu sesión de Canvas e historial | `~/.local/share/Pandex/` |
| Perfil de Firefox (solo con el Firefox de snap) | `~/snap/firefox/common/pandex-perfil/` |

¿Ves dos «Pandex» en el menú o dos carpetas? [¿Tengo Pandex dos veces?](ayuda.md#tengo-pandex-dos-veces)

## Que corra a su hora y se cierre

**Configuración → Comportamiento → «Cerrarse, y abrirse sola a la hora de sus tareas».** Eliges las
horas en **Tareas** (o en «Configurar Canvas…»). A esa hora el sistema abre a Pandex, hace la
tarea, y se cierra: el resto del día no ocupa memoria. Si a esa hora la PC estaba **apagada o
suspendida**, la hace apenas la prendas.

Funciona con un temporizador de systemd de tu usuario. Para ver cuándo toca:

```bash
systemctl --user list-timers pandex.timer
```

Con «Quedarse en el escritorio» (lo de siempre) también se pone al día: lo que se perdió con la
PC apagada se hace al abrir Pandex.

## Lo que cambia

| | Windows | Linux |
|---|---|---|
| Navegador para iniciar sesión | Chrome | **tu Firefox** |
| Tus datos (sesión, historial) | `%LOCALAPPDATA%\Pandex` | `~/.local/share/Pandex` |
| Acceso directo | `.lnk` | `.desktop` |
| Arrancar con el sistema | Carpeta *Inicio* | `~/.config/autostart` |
| A su hora con la PC apagada | Programador de tareas | temporizador de systemd |
| OCR de PDFs escaneados | El de Windows | Tesseract (opcional) |
| OneDrive | La app de OneDrive | rclone, desde Configuración → OneDrive |

## OneDrive

Microsoft no tiene app de OneDrive para Linux. Pandex lo conecta con **rclone**, un programa
libre que pone tu OneDrive como una carpeta más:

1. Instala rclone una vez: `sudo apt install rclone fuse3`.
2. En Pandex: **Configuración → OneDrive → Conectar una cuenta…** Ponle un nombre («UTEC»,
   «Personal») e inicia sesión en la página de Microsoft que se abre. Pandex nunca ve tu contraseña.
3. Aparece la carpeta: la cuenta personal en `~/OneDrive` y las demás en `~/OneDrive - Nombre`
   (igual que en Windows). Puedes conectar las dos.
4. En **Configurar Canvas…** elige una carpeta dentro de esa. Desde ahí Pandex baja, ordena y
   convierte a Markdown directo en tu OneDrive; lo que guarda se sube solo, en segundo plano.

Al abrir Pandex se vuelven a conectar solas. Si tu OneDrive no está disponible (sin internet,
sesión caducada), Pandex **no sincroniza Canvas** y te avisa, para no dejar archivos en tu PC
creyendo que están en la nube.

- *"Necesitas la aprobación de un administrador"* al iniciar sesión: tu universidad no deja usar
  apps externas con esa cuenta. Usa tu cuenta personal o pide acceso a TI.
- *"Tu sesión de OneDrive caducó"*: Configuración → OneDrive → **Quitar** y conéctala de nuevo.
- La carpeta se ve vacía: **Volver a abrir** en la misma pantalla.
- Si conectar falla aunque iniciaste sesión bien, tu rclone puede ser viejo (el de `apt` en Mint 22
  es la 1.60). Instala el más nuevo con el método oficial: `sudo -v ; curl https://rclone.org/install.sh | sudo bash`.
- Antes de apagar la PC justo después de sincronizar, espera un minuto: si no, lo pendiente se
  sube la próxima vez que abras Pandex.

## OCR (opcional)

Solo si instalaste «Convertir a Markdown», y solo para PDFs escaneados o imágenes. Sin él, Pandex convierte todo lo demás y avisa
cuáles quedaron sin texto.

```bash
sudo apt install tesseract-ocr tesseract-ocr-spa
```

## Si algo falla

| Qué pasa | Qué hacer |
|---|---|
| No abre y dice algo de `xcb` o `libxcb-cursor` | `sudo apt install libxcb-cursor0` |
| *"No encontré Firefox"* | `sudo apt install firefox` |
| *"No pude abrir Firefox"* la primera vez | Pandex descarga `geckodriver` (unos 3 MB) la primera vez: revisa tu internet. Si sigue, pásale a quien te ayude el mensaje de «Ver registro». |
| No veo el ícono junto al reloj (GNOME) | GNOME no muestra íconos de bandeja por defecto. Instala la extensión *AppIndicator and KStatusNotifierItem Support*. Mientras tanto, clic derecho sobre la mascota abre el mismo menú. |
| El acceso del Escritorio dice "no confiable" | Clic derecho sobre el ícono → **Permitir lanzar**. |
| No se abre sola a su hora | `systemctl --user list-timers pandex.timer` debe mostrarlo. Si no, vuelve a guardar en Configuración → Comportamiento. |
| Quiero probar en Wayland puro | `QT_QPA_PLATFORM=wayland .venv/bin/python main.py`. Ahí el sistema no deja que la mascota se mueva ni quede siempre encima; por eso Pandex usa XWayland por defecto. |

## Para programadores

```bash
.venv/bin/python -m pip install ruff
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -t .
QT_QPA_PLATFORM=offscreen .venv/bin/python main.py --test
```

Las dependencias `winrt-*` solo se instalan en Windows. La CI corre en Windows y en Ubuntu.
