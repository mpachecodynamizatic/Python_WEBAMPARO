@echo off
title Restaurar Backup - Protectora Burjassot
color 0E

echo ========================================================
echo   Restaurar Backup - Protectora Burjassot
echo ========================================================
echo.

REM Verificar si existe la carpeta de backups
if not exist "backups" (
    echo [ERROR] No se encontro la carpeta de backups
    echo.
    echo Primero ejecuta: hacer_backup.bat
    echo.
    pause
    exit /b 1
)

REM Listar backups disponibles
echo Backups disponibles:
echo.
dir /B /AD backups
echo.

REM Pedir al usuario que ingrese el nombre del backup
set /p BACKUP_NAME="Ingresa el nombre del backup a restaurar (ej: backup_20260327_143022): "

if not exist "backups\%BACKUP_NAME%" (
    echo.
    echo [ERROR] El backup especificado no existe
    pause
    exit /b 1
)

echo.
echo ========================================================
echo [!] ADVERTENCIA
echo ========================================================
echo.
echo Esta accion reemplazara los datos actuales con el backup:
echo   - Base de datos actual sera reemplazada
echo   - Archivos subidos actuales seran reemplazados
echo.
echo [!] Se perderan todos los cambios desde el backup
echo.
choice /C SN /M "Estas seguro de continuar (S/N)"

if errorlevel 2 goto :cancel
if errorlevel 1 goto :restore

:restore
echo.
echo Restaurando backup...
echo.

REM Detener servidores si estan corriendo
echo Deteniendo servidores...
call stop.bat >nul 2>&1
timeout /t 2 /nobreak >nul

REM Restaurar base de datos
if exist "backups\%BACKUP_NAME%\protectora.db" (
    echo [1/2] Restaurando base de datos...
    copy /Y "backups\%BACKUP_NAME%\protectora.db" "admin\protectora.db" >nul
    echo [OK] Base de datos restaurada
) else (
    echo [!] No se encontro la base de datos en el backup
)

REM Restaurar uploads
if exist "backups\%BACKUP_NAME%\uploads" (
    echo [2/2] Restaurando archivos subidos...
    if exist "uploads" rmdir /s /q uploads
    xcopy "backups\%BACKUP_NAME%\uploads" "uploads" /E /I /Q >nul
    echo [OK] Archivos subidos restaurados
) else (
    echo [!] No se encontro la carpeta uploads en el backup
)

echo.
echo ========================================================
echo   Restauracion completada
echo ========================================================
echo.
echo Los datos han sido restaurados desde: %BACKUP_NAME%
echo.
echo Ya puedes ejecutar run.bat para iniciar los servidores
echo.
goto :end

:cancel
echo.
echo Operacion cancelada
echo No se ha modificado nada
echo.

:end
echo ========================================================
pause
