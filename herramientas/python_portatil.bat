@echo off
rem Baja un Python solo para Pandex en .python\ (dentro de esta carpeta) cuando no tienes
rem Python 3.12 o mas nuevo (spec 006, PLA-03). Sin tocar el sistema: ni PATH, ni registro, ni
rem cachés fuera. La versión y su huella (SHA-256) están fijas en python_portatil.txt: si lo
rem descargado no coincide, no se usa. Usa curl.exe y tar.exe, que trae Windows 10 y 11.
rem Lo llama instalar.bat desde la carpeta de Pandex. Con PANDEX_PYTHON=portatil no pregunta.
setlocal
set "FIJO=%~dp0python_portatil.txt"
set "ARCHIVO=.python-descarga.tar.gz"
set "NUEVO=.python-nuevo"
set "HUELLA="
set "URL="
for /f "tokens=1,2,3" %%a in ('findstr /b /c:"windows-x86_64 " "%FIJO%"') do (
    set "HUELLA=%%b"
    set "URL=%%c"
)
if not defined URL (
    echo No encontré qué Python descargar: falta herramientas\python_portatil.txt.
    exit /b 1
)

if /i "%PANDEX_PYTHON%"=="portatil" goto :bajar
set "SI="
set /p "SI=Descargo un Python solo para Pandex? Ocupa unos 70 MB dentro de esta carpeta (.python) y no toca tu Windows. [S/n] "
if /i "%SI%"=="n" goto :no
if /i "%SI%"=="no" goto :no

:bajar
if exist "%ARCHIVO%" del /q "%ARCHIVO%"
if exist "%NUEVO%" rmdir /s /q "%NUEVO%"
echo Descargando Python...
curl.exe -fL --retry 2 --proto "=https" --proto-redir "=https" -o "%ARCHIVO%" "%URL%"
if errorlevel 1 goto :sin_descarga

set "REAL="
for /f "usebackq delims=" %%h in (`powershell -NoProfile -NonInteractive -Command "(Get-FileHash -Algorithm SHA256 -LiteralPath '%ARCHIVO%').Hash"`) do set "REAL=%%h"
if /i not "%REAL%"=="%HUELLA%" goto :otra_huella

mkdir "%NUEVO%"
tar -xzf "%ARCHIVO%" -C "%NUEVO%"
if errorlevel 1 goto :sin_descomprimir
if not exist "%NUEVO%\python\python.exe" goto :sin_descomprimir
if exist ".python" rmdir /s /q ".python"
move "%NUEVO%\python" ".python" >nul
if errorlevel 1 goto :sin_descomprimir
call :limpiar
echo Python listo en .python (solo para Pandex).
exit /b 0

:no
echo Instala Python 3.12 o más nuevo de https://www.python.org/downloads/ (marca "Add python.exe to PATH") y vuelve a ejecutar instalar.bat.
exit /b 1

:sin_descarga
echo No pude descargar Python. Revisa tu conexión y vuelve a intentar.
call :limpiar
exit /b 1

:otra_huella
echo Lo descargado no coincide con su huella (SHA-256): no lo uso. Vuelve a intentar.
call :limpiar
exit /b 1

:sin_descomprimir
echo No pude descomprimir Python. Vuelve a intentar.
call :limpiar
exit /b 1

:limpiar
if exist "%ARCHIVO%" del /q "%ARCHIVO%"
if exist "%NUEVO%" rmdir /s /q "%NUEVO%"
exit /b 0
