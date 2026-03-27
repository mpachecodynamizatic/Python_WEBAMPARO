@echo off
title Limpiar Entorno Virtual - Protectora Burjassot
color 0E

echo ========================================================
echo   Limpiar Entorno Virtual
echo   Protectora de Animales Burjassot
echo ========================================================
echo.
echo Esta herramienta eliminara el entorno virtual (carpeta venv)
echo y la base de datos para empezar desde cero.
echo.
echo [!] ADVERTENCIA: Esta accion NO se puede deshacer
echo.
echo Se eliminaran:
echo   - Carpeta venv (entorno virtual)
echo   - admin\protectora.db (base de datos)
echo   - admin\__pycache__ (archivos temporales)
echo.
echo ========================================================
echo.
choice /C SN /M "Estas seguro de que quieres continuar (S/N)"

if errorlevel 2 goto :cancel
if errorlevel 1 goto :clean

:clean
echo.
echo Limpiando entorno...
echo.

REM Eliminar entorno virtual
if exist "venv" (
    echo [1/3] Eliminando carpeta venv...
    rmdir /s /q venv
    if exist "venv" (
        echo [!] No se pudo eliminar completamente (puede estar en uso)
    ) else (
        echo [OK] Carpeta venv eliminada
    )
) else (
    echo [1/3] Carpeta venv no existe
)

REM Eliminar base de datos
if exist "admin\protectora.db" (
    echo [2/3] Eliminando base de datos...
    del /f /q "admin\protectora.db"
    if exist "admin\protectora.db" (
        echo [!] No se pudo eliminar (puede estar en uso)
    ) else (
        echo [OK] Base de datos eliminada
    )
) else (
    echo [2/3] Base de datos no existe
)

REM Eliminar __pycache__
if exist "admin\__pycache__" (
    echo [3/3] Eliminando archivos temporales...
    rmdir /s /q "admin\__pycache__"
    echo [OK] Archivos temporales eliminados
) else (
    echo [3/3] No hay archivos temporales
)

echo.
echo ========================================================
echo   Limpieza completada
echo ========================================================
echo.
echo El entorno ha sido limpiado.
echo.
echo Proximos pasos:
echo    1. Ejecuta: run.bat
echo       (Creara automaticamente un nuevo entorno virtual)
echo    2. O ejecuta: instalar_dependencias.bat
echo       (Si prefieres instalar manualmente primero)
echo.
echo [!] NOTA: La base de datos se recreara con usuario:
echo    - Usuario: admin
echo    - Contrasena: protectora2026
echo.
goto :end

:cancel
echo.
echo Operacion cancelada
echo No se ha eliminado nada
echo.

:end
echo ========================================================
pause
