# ADR-0001: Instalación liviana, navegador a elección y actualizar que libera espacio

**Estado:** Aceptada (las partes que piden el visto bueno de Frank están marcadas)
**Fecha:** 31/10/2026
**Decide:** Frank
**Specs:** [002](../../specs/002_peso_y_funciones_opcionales/spec.md),
[003](../../specs/003_sin_residuos_y_desinstalar/spec.md) · Principios P2, P3, P5, P7, P8

## Contexto

Medido el 31/10/2026 en Linux (Python 3.13, entorno limpio, `pip --no-cache-dir`):

| Qué | Hoy | Límite |
|---|---|---|
| Instalación base | 341 MB | 350 MB |
| Con «Convertir a Markdown» | **660 MB** | 600 MB ❌ |
| Memoria en reposo (RSS, 60 s, sin pantalla) | 74–88 MB (privada: 17–31 MB) | 80 MB ⚠️ |
| CPU en reposo | 0 % | 0 % |

Además, hay cinco problemas:

1. **Paquetes que Pandex no usa.**
   - `markitdown[xlsx,xls]` instala **pandas** (81 MB) solo para leer Excel.
   - `magika` + `onnxruntime` + `numpy` pesan unos 140 MB, y MarkItDown los importa siempre.
   - pip guarda los `.pyc` de todos los paquetes (42 MB), aunque Pandex solo carga una parte.
2. **Residuos fuera de Pandex.**
   - Copias de pip en `~/.cache/pip` o `%LOCALAPPDATA%\pip\Cache`.
   - geckodriver en `~/.cache/selenium`.
   - Chromium en `%LOCALAPPDATA%\ms-playwright`.
3. **Dos motores de navegador.**
   - Windows usa Playwright (≈ 110 MB, y descarga Chromium si no hay Chrome).
   - Linux usa Selenium con tu Firefox.
   - Hay dos caminos de código para lo mismo, y nadie puede elegir su navegador.
4. **Actualizar solo agrega.**
   - Los paquetes que la versión nueva ya no pide se quedan en `.venv`.
   - Los respaldos se acumulan sin límite.
   - Una copia vieja de Pandex en otra carpeta sigue ocupando espacio.
5. **No hay desinstalador.**

Restricciones:
- Nada global ni `sudo` (P2).
- Nada destructivo sin confirmar (P4).
- Mismo comportamiento en Windows y Linux (P7).
- El usuario no edita archivos (P8).

## Decisión

### D1. Un solo motor de navegador: Selenium, con el navegador que elijas

- `pandex/canvas/navegador.py` reemplaza a `firefox.py` y a la parte de Playwright de
  `sesion.py`.
- Sabe abrir **Firefox, Chrome y Edge** en los dos sistemas, siempre con un perfil propio de
  Pandex.
- En **Configuración → Canvas → Navegador** eliges entre:
  - **«El que uso siempre»** (por defecto): lee tu navegador predeterminado.
    - En Windows lo lee del registro; en Linux, con `xdg-settings`.
    - Si no es uno de los tres, usa el primero que encuentre: Edge → Chrome → Firefox en
      Windows, y Firefox → Chrome → Edge en Linux.
  - Edge, Chrome o Firefox, a mano.
- Nunca se descarga un navegador. En Windows siempre hay Edge.
- El driver (3–15 MB) lo baja Selenium Manager a `DATOS/navegadores` (`SE_CACHE_PATH`).
  Así queda dentro de Pandex y se borra al desinstalar.
- Playwright sale de `requirements.txt`. Esto responde la pregunta 3 de la spec 002: Frank
  pidió elegir el navegador, y Playwright no puede usar tu Firefox.

### D2. «Convertir a Markdown» sin pandas

- `requirements-markdown.txt` pasa a `markitdown[pdf,docx,pptx]`, más `openpyxl` (3 MB) y
  `xlrd` (1 MB).
- Un conversor propio de Excel (`pandex/markdown/excel.py`) se registra en MarkItDown con
  prioridad. Sigue leyendo `.xlsx` y `.xls`, sin pandas.
- MarkItDown se queda: la pregunta 4 de la spec 002 sigue en «no por ahora».

### D3. Instalar sin copias y sin `.pyc` de sobra

- Todo `pip install` pasa por `pandex/paquetes.py`, con `--no-cache-dir --no-compile`.
- Los instaladores exportan `PIP_NO_CACHE_DIR=1` y usan `--no-compile`.
- Python crea los `.pyc` que hagan falta la primera vez que importa cada módulo. Eso tiene un
  costo de milisegundos, una sola vez.

Resultado medido en Linux:

| | Antes | Después |
|---|---|---|
| Base | 341 MB | **326 MB** |
| Completo | 660 MB | **532 MB** (68 MB por debajo del límite) |
| Caché de pip | 100–300 MB | 0 MB |

En Windows se ahorran además unos 75 MB al quitar Playwright, y nunca se descarga Chromium.
Estas cifras de Windows faltan medir: lo hará la CI (T002.1).

### D4. Actualizar = actualizar + liberar espacio

`pandex/limpieza.py` arma una lista de lo que sobra, con el tamaño de cada cosa. Corre la
**primera vez que se abre una versión nueva**, en segundo plano, y no al final de
`actualizar.aplicar()`: la actualización la ejecuta el código de la versión **anterior**, que
no sabe limpiar. Así también limpia quien actualiza desde la 2.4. Además se puede abrir cuando
quieras desde **Configuración → Comportamiento → Liberar espacio…** La ventana solo se abre
sola si fuera de Pandex hay 20 MB o más que liberar.

Solo quita paquetes si el Python es el de `.venv` de Pandex. Nunca toca el Python del sistema.

| Qué | Cómo se decide | ¿Pregunta? |
|---|---|---|
| Paquetes huérfanos en `.venv` (ninguno de los `requirements*.txt` instalados los pide, ni sus dependencias) | `importlib.metadata`; nunca toca `pip`, `setuptools` ni `wheel` | no: `.venv` es de Pandex |
| Respaldos de actualizaciones | se quedan los 2 más nuevos | no |
| Copias de configuración de Canvas | se quedan las 3 más nuevas | no |
| Caché de pip, geckodriver viejo (`~/.cache/selenium`), Chromium de Playwright | están **fuera** de Pandex; son cachés: si otro programa las necesita, las vuelve a descargar | **sí**: casillas con el tamaño de cada uno, marcadas |
| Otra copia de Pandex (`accesos.instalaciones_anteriores`) | el instalador anota cada carpeta donde se instaló | **sí**: desmarcada, con su ruta; va a la papelera si se puede |

- La interfaz es una sola ventana: «Puedo liberar 412 MB», con la lista y un botón
  **Liberar**.
- Lo que no se pudo borrar se lista al final, con su ruta (P8).

### D5. Desinstalar con inventario

- `pandex/inventario.py` anota lo que Pandex crea fuera de sus carpetas: accesos directos,
  arranque automático, despertador, perfil de snap y montaje de OneDrive.
- `pandex/desinstalar.py` muestra esa lista, pide confirmación y borra en este orden:
  despertador → arranque automático → accesos directos → OneDrive de Pandex → `DATOS` →
  `.venv`.
- Se llega a él desde `desinstalar.sh`, `desinstalar.bat` y desde **Configuración →
  Comportamiento → Desinstalar Pandex…**
- La carpeta de cursos nunca se toca.
- Ofrece conservar `config.json` para reinstalar.
- La carpeta del proyecto se borra a mano: se explica cómo (pregunta 1 de la spec 003, que
  queda en su valor por defecto).

### D6. Memoria en reposo: medir antes de cambiar · *pide visto bueno de Frank*

- Con `smaps`, el 80 % de los 74 MB son código de Qt (Gui, Core, Widgets) y librerías del
  sistema. Es el piso de cualquier app PyQt6.
- Lo propio de Pandex (`anon` + `heap`) son unos 17 MB.
- Bajar de 80 MB de RSS de forma estable exige quitar QtNetwork (≈ 5 MB; hoy da la instancia
  única) o cambiar de framework. Esto último está fuera de alcance en la spec 002.
- **Propuesta:** el presupuesto pasa a **memoria propia (USS) ≤ 40 MB**, y la CI lo mide.
  Hasta que Frank lo apruebe, el límite sigue siendo 80 MB de RSS y se registra el
  incumplimiento.

## Opciones consideradas

### Navegador

| | A. Seguir igual (Playwright en Windows, Selenium en Linux) | B. Playwright en los dos | **C. Selenium en los dos** |
|---|---|---|---|
| Peso en Windows | ≈ 110 MB + Chromium posible | ≈ 110 MB + Firefox propio (80 MB) | **≈ 34 MB, sin descargar navegadores** |
| Usa tu navegador | Chrome sí; Edge y Firefox no | Chrome y Edge; tu Firefox no | **Firefox, Chrome y Edge** |
| Código | dos caminos | uno | **uno** |
| Riesgo | — | medio | medio: cambia el inicio de sesión en Windows (ya se usa en Linux) |

Se elige **C**. Selenium también puede reutilizar el perfil de Chrome que creó Playwright
(`DATOS/browser-profile`), así que quien ya inició sesión no tiene que volver a hacerlo.

### Peso de «Convertir a Markdown»

| Opción | Ahorro | Riesgo | Decisión |
|---|---|---|---|
| a. `--no-cache-dir --no-compile` | 15–40 MB en `.venv` y toda la caché | nulo | **sí** |
| b. Podar librerías de Qt | 60–100 MB | medio, y hay que repetirlo tras cada actualización | no hace falta por ahora |
| c'. Excel sin pandas (conversor propio con openpyxl y xlrd) | 85 MB | bajo: un conversor de unas 60 líneas, con pruebas | **sí** |
| d. Selenium en Windows | ≈ 75 MB (Windows) | medio | **sí** (D1) |
| e. Quitar MarkItDown | 140 MB más | alto | no por ahora |

## Consecuencias

**Más fácil:**
- Elegir el navegador.
- Instalar en una PC con poco disco.
- Saber cuánto ocupa Pandex y liberarlo con un clic.
- Desinstalar sin dejar nada.

**Más difícil:**
- Selenium Manager necesita internet la primera vez que usas un navegador nuevo (baja el
  driver).
- El conversor de Excel es código propio que hay que mantener.

**Por revisar:**
- Pesos reales en Windows (CI, T002.1).
- La propuesta de memoria (D6).
- Si un antivirus bloquea el driver en `DATOS/navegadores`: el error dirá qué hacer.

## Nueva estructura

```
pandex/
  paquetes.py        NUEVO  instalar(), desinstalar(), huerfanos(): pip sin caché ni .pyc
  limpieza.py        NUEVO  qué sobra y cuánto pesa; liberar() con lista y confirmación
  inventario.py      NUEVO  lo creado fuera de Pandex (para desinstalar)
  desinstalar.py     NUEVO  lógica sin Qt; la usan los .sh/.bat y Configuración
  rutas.py           + NAVEGADORES = DATOS/navegadores, limitar(carpeta, patrón, n)
  extras.py          usa paquetes.py; quitar(extra)
  actualizar.py      usa paquetes.py; al terminar → limpieza
  canvas/
    navegador.py     NUEVO  Selenium: Firefox, Chrome o Edge; predeterminado del sistema
    sesion.py        solo el flujo de inicio de sesión (sin Playwright)
    firefox.py       SE VA (absorbido por navegador.py)
  markdown/
    excel.py         NUEVO  .xlsx/.xls → tabla Markdown sin pandas
  ui/
    limpieza.py      NUEVO  «Puedo liberar N MB»
desinstalar.sh / desinstalar.bat   NUEVOS
```

## Tareas (en el tablero)

1. [x] T003.2 + T003.5 · `paquetes.py` (sin caché ni `.pyc`; huérfanos al actualizar).
2. [x] T002.4 · Excel sin pandas (D2).
3. [x] T002.5 + T003.3 · Navegador a elección con Selenium; drivers en `DATOS/navegadores` (D1).
4. [x] T003.4 + D4 · «Liberar espacio» al actualizar y desde Configuración.
5. [x] T003.6 + T003.7 · Inventario y desinstalador (D5).
6. [ ] T002.1 · Medir el peso en la CI (Windows y Linux) y anotar las cifras reales. *(El job `peso` ya existe; faltan las cifras de Windows.)*
7. [ ] D6 · Visto bueno de Frank sobre el presupuesto de memoria.
