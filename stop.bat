@echo off
title Detener Servidores - Protectora Burjassot
color 0C

echo ========================================================
echo   Detener Servidores - Protectora Burjassot
echo ========================================================
echo.
echo Deteniendo todos los servidores...
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

REM Detener proceso HTTP Server (puerto 8000)
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do (
    echo Deteniendo servidor Web (PID: %%a)...
    taskkill /F /PID %%a >nul 2>&1
    if not errorlevel 1 (
        echo [OK] Servidor Web detenido
        set FOUND_PROCESS=1
    ) else (
        echo [!] No se pudo detener (puede que ya este cerrado)
    )
)

REM Detener ventanas de comandos con titulos especificos
echo.
echo Buscando ventanas de comandos abiertas...
tasklist /FI "WINDOWTITLE eq CMS - Panel Admin" >nul 2>&1
if not errorlevel 1 (
    echo Cerrando ventana "CMS - Panel Admin"...
    taskkill /FI "WINDOWTITLE eq CMS - Panel Admin" /F >nul 2>&1
)

tasklist /FI "WINDOWTITLE eq Web - Sitio Publico" >nul 2>&1
if not errorlevel 1 (
    echo Cerrando ventana "Web - Sitio Publico"...
    taskkill /FI "WINDOWTITLE eq Web - Sitio Publico" /F >nul 2>&1
)

echo.

if "%FOUND_PROCESS%"=="1" (
    echo ========================================================
    echo   Servidores detenidos correctamente
    echo ========================================================
    echo.
    echo Los servidores han sido detenidos.
    echo Puedes volver a iniciarlos ejecutando: run.bat
) else (
    echo ========================================================
    echo   No se encontraron servidores en ejecucion
    echo ========================================================
    echo.
    echo No habia servidores corriendo en los puertos 5000 y 8000.
    echo.
    echo Si quieres iniciar los servidores, ejecuta: run.bat
)

echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause >nul
