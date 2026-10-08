@echo off
rem Abre Pandex sin dejar una ventana de consola abierta.
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Falta instalar Pandex: ejecuta primero instalar.bat
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "main.py"
