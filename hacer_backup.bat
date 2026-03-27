@echo off
title Backup - Protectora Burjassot
color 0B

echo ========================================================
echo   Backup de Datos - Protectora Burjassot
echo ========================================================
echo.

REM Crear carpeta de backups si no existe
if not exist "backups" mkdir backups

REM Obtener fecha y hora actual
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set FECHA=%datetime:~0,8%
set HORA=%datetime:~8,6%
set TIMESTAMP=%FECHA%_%HORA%

REM Crear carpeta para este backup
set BACKUP_FOLDER=backups\backup_%TIMESTAMP%
mkdir "%BACKUP_FOLDER%"

echo Creando backup en: %BACKUP_FOLDER%
echo.

REM Copiar base de datos
if exist "admin\protectora.db" (
    echo [1/2] Copiando base de datos...
    copy "admin\protectora.db" "%BACKUP_FOLDER%\protectora.db" >nul
    echo [OK] Base de datos copiada
) else (
    echo [!] No se encontro la base de datos
)

REM Copiar carpeta uploads
if exist "uploads" (
    echo [2/2] Copiando archivos subidos...
    xcopy "uploads" "%BACKUP_FOLDER%\uploads" /E /I /Q >nul
    echo [OK] Archivos subidos copiados
) else (
    echo [!] No se encontro la carpeta uploads
)

echo.
echo ========================================================
echo   Backup completado
echo ========================================================
echo.
echo Ubicacion: %BACKUP_FOLDER%
echo.
echo Contenido del backup:
dir /B "%BACKUP_FOLDER%"
echo.
echo Para restaurar:
echo   1. Copia protectora.db a la carpeta admin/
echo   2. Copia la carpeta uploads/ a la raiz del proyecto
echo.
echo ========================================================
pause
