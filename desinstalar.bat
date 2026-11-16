@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
rem Desinstala Pandex en Windows: muestra la lista exacta de lo que va a quitar y pregunta antes.
rem Tu carpeta de cursos no se toca.
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

rem todo menos .venv y .python (son el Python que está corriendo): se borran al final
"%PY%" -m pandex.desinstalar --sin-venv %*
if errorlevel 3 goto :fallo
if errorlevel 2 goto :fin
if errorlevel 1 goto :fallo
if exist ".venv" rmdir /s /q ".venv"
echo  Entorno de Python (.venv) borrado.
if exist ".python" rmdir /s /q ".python"
echo.
echo  Para terminar, borra esta carpeta: %CD%
echo  (cierra esta ventana y en el Explorador: clic derecho, Eliminar)
:fin
echo.
pause
exit /b 0

:fallo
echo.
echo  Algo falló. Lee el mensaje de arriba.
pause
exit /b 1
