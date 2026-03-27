@echo off
title Instalar Dependencias - Protectora Burjassot
color 0B

echo ========================================================
echo   Instalacion de Dependencias
echo   Protectora de Animales Burjassot
echo ========================================================
echo.

REM Verificar si Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado
    echo.
    echo Por favor, instala Python desde:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANTE: Marca la opcion "Add Python to PATH" durante la instalacion
    echo.
    pause
    exit /b 1
)

echo [OK] Python detectado:
python --version
echo.

REM ========================================================
REM Crear entorno virtual si no existe
REM ========================================================
if not exist "venv" (
    echo [1/4] Creando entorno virtual...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual
        echo.
        echo Intenta ejecutar:
        echo   python -m pip install --upgrade pip
        echo   python -m pip install virtualenv
        echo.
        pause
        exit /b 1
    )
    echo [OK] Entorno virtual creado
    echo.
) else (
    echo [1/4] Entorno virtual ya existe
    echo.
)

REM ========================================================
REM Activar entorno virtual
REM ========================================================
echo [2/4] Activando entorno virtual...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] No se pudo activar el entorno virtual
    pause
    exit /b 1
)
echo [OK] Entorno virtual activado
echo.

REM ========================================================
REM Actualizar pip
REM ========================================================
echo [3/4] Actualizando pip...
python -m pip install --upgrade pip --quiet
echo [OK] pip actualizado
echo.

REM ========================================================
REM Instalar dependencias
REM ========================================================
echo [4/4] Instalando dependencias de Flask...
echo.
echo Este proceso puede tardar unos minutos...
echo.

cd admin

echo Instalando Flask...
pip install Flask==3.0.0
if errorlevel 1 goto :install_error
echo [OK] Flask instalado

echo Instalando Flask-CORS...
pip install Flask-CORS==4.0.0
if errorlevel 1 goto :install_error
echo [OK] Flask-CORS instalado

echo Instalando Werkzeug...
pip install Werkzeug==3.0.1
if errorlevel 1 goto :install_error
echo [OK] Werkzeug instalado

cd ..

echo.
echo ========================================================
echo   Instalacion completada exitosamente
echo ========================================================
echo.
echo Resumen de dependencias instaladas:
echo.
echo [OK] Flask 3.0.0
echo [OK] Flask-CORS 4.0.0
echo [OK] Werkzeug 3.0.1
echo.
echo Entorno virtual: %CD%\venv
echo Python:
python --version
echo.
echo ========================================================
echo.
echo Proximo paso:
echo    Ejecuta run.bat para iniciar los servidores
echo.
pause
exit /b 0

:install_error
cd ..
echo.
echo ========================================================
echo   ERROR durante la instalacion
echo ========================================================
echo.
echo No se pudieron instalar todas las dependencias.
echo.
echo Posibles soluciones:
echo 1. Verifica tu conexion a Internet
echo 2. Ejecuta como Administrador
echo 3. Desactiva temporalmente el antivirus
echo 4. Intenta ejecutar:
echo    venv\Scripts\activate.bat
echo    pip install -r admin\requirements.txt
echo.
pause
exit /b 1
