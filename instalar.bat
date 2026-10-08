@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo.
echo  ===  Instalando Pandex  ===
echo.

rem 1. Python 3.12 o más nuevo
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>nul
if errorlevel 1 (
    echo No encontré Python 3.12 o más nuevo.
    echo Descárgalo de https://www.python.org/downloads/ y marca "Add python.exe to PATH".
    goto :fallo
)

rem 2. Entorno virtual propio, para no tocar el Python de tu PC
if not exist ".venv\Scripts\python.exe" (
    echo Creando el entorno virtual...
    %PY% -m venv .venv || goto :fallo
)

rem 3. Dependencias
echo Instalando dependencias: la primera vez tarda unos minutos...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet || goto :fallo

rem 4. Navegador para iniciar sesión en Canvas: Google Chrome si lo tienes; si no, Chromium
set "CHROME="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "CHROME=1"
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME=1"
if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "CHROME=1"
if not defined CHROME (
    echo No tienes Google Chrome: descargo Chromium para iniciar sesión en Canvas...
    ".venv\Scripts\python.exe" -m playwright install chromium || goto :fallo
)

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
