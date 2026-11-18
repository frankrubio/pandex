@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
rem pip no guarda copias de los paquetes fuera de Pandex (%LOCALAPPDATA%\pip\Cache)
set "PIP_NO_CACHE_DIR=1"
echo.
echo  ===  Instalando Pandex  ===
echo.

rem 1. Python 3.12 o más nuevo. Si no hay, uno solo para Pandex dentro de esta carpeta (.python,
rem    PLA-03); si ya lo bajaste antes, se sigue usando. PANDEX_PYTHON=portatil: el portátil sin preguntar.
set "PY=.python\python.exe"
if exist ".python\python.exe" goto :hay_python
if /i "%PANDEX_PYTHON%"=="portatil" goto :portatil
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>nul
if not errorlevel 1 goto :hay_python
echo No encontré Python 3.12 o más nuevo.
:portatil
call herramientas\python_portatil.bat
if errorlevel 1 goto :fallo
set "PY=.python\python.exe"
:hay_python

rem 2. Entorno virtual propio, para no tocar el Python de tu PC. Si no funciona (por ejemplo,
rem    moviste la carpeta), se rehace.
".venv\Scripts\python.exe" -c "" >nul 2>nul
if errorlevel 1 (
    echo Creando el entorno virtual...
    %PY% -m venv --clear .venv || goto :fallo
)

rem 3. Dependencias
echo Instalando dependencias: la primera vez tarda unos minutos...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet --no-compile
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet --no-compile || goto :fallo

rem 3b. "Convertir a Markdown" es opcional (unos 280 MB); se puede anadir despues en Configuracion - Tareas
".venv\Scripts\python.exe" -c "import markitdown" >nul 2>nul && goto :con_markdown
set "QUIERE=%PANDEX_MARKDOWN%"
if not defined QUIERE set /p "QUIERE=Instalar tambien Convertir a Markdown (PDF, Word, PowerPoint a .md; unos 280 MB)? [s/N] "
if /i "%QUIERE%"=="s" goto :con_markdown
if /i "%QUIERE%"=="si" goto :con_markdown
echo Sin Convertir a Markdown: Pandex queda mas liviano.
goto :sin_markdown
:con_markdown
echo Instalando Convertir a Markdown...
".venv\Scripts\python.exe" -m pandex.paquetes requirements-markdown.txt || goto :fallo
:sin_markdown

rem 4. Navegador para Canvas: el tuyo (Edge, Chrome o Firefox). No se descarga ninguno.

rem 5. Acceso directo en el Escritorio
".venv\Scripts\python.exe" -m pandex.accesos || goto :fallo

echo.
echo  Listo. Abre Pandex con el acceso directo "Pandex" de tu Escritorio.
echo  La primera vez te va a guiar para conectar tu Canvas.
echo.
pause
exit /b 0

:fallo
echo.
echo  Algo falló. Lee el mensaje de arriba; si no se entiende, abre un issue en GitHub.
echo.
pause
exit /b 1
