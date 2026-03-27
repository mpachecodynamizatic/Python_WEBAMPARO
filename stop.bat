@echo off
title Detener Servidor - Protectora Burjassot
color 0C

echo ========================================================
echo   Detener Servidor - Protectora Burjassot
echo ========================================================
echo.
echo Deteniendo servidor Flask...
echo.

set FOUND_PROCESS=0

REM Detener proceso de Flask (puerto 5000)
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5000" ^| find "LISTENING"') do (
    echo Deteniendo servidor Flask (PID: %%a)...
    taskkill /F /PID %%a >nul 2>&1
    if not errorlevel 1 (
        echo [OK] Servidor Flask detenido
        set FOUND_PROCESS=1
    ) else (
        echo [!] No se pudo detener (puede que ya este cerrado)
    )
)

REM Detener ventana de comandos con titulo especifico
echo.
echo Buscando ventana de comandos abierta...
tasklist /FI "WINDOWTITLE eq Protectora Burjassot - Flask Server" >nul 2>&1
if not errorlevel 1 (
    echo Cerrando ventana "Protectora Burjassot - Flask Server"...
    taskkill /FI "WINDOWTITLE eq Protectora Burjassot - Flask Server" /F >nul 2>&1
)

echo.

if "%FOUND_PROCESS%"=="1" (
    echo ========================================================
    echo   Servidor detenido correctamente
    echo ========================================================
    echo.
    echo El servidor ha sido detenido.
    echo Puedes volver a iniciarlo ejecutando: run.bat
) else (
    echo ========================================================
    echo   No se encontro el servidor en ejecucion
    echo ========================================================
    echo.
    echo No habia servidor corriendo en el puerto 5000.
    echo.
    echo Si quieres iniciar el servidor, ejecuta: run.bat
)

echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause >nul
