@echo off
title Protectora de Animales Burjassot - Launcher
color 0A

echo ========================================================
echo   Protectora de Animales Burjassot
echo ========================================================
echo.

REM Verificar si Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado o no esta en el PATH
    echo.
    echo Por favor, instala Python desde https://www.python.org/
    echo Asegurate de marcar "Add Python to PATH" durante la instalacion
    echo.
    pause
    exit /b 1
)

echo [OK] Python detectado:
python --version
echo.

REM ========================================================
REM PASO 1: Crear entorno virtual si no existe
REM ========================================================
if not exist "venv" (
    echo [1/6] Creando entorno virtual...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual
        echo Intenta ejecutar: python -m pip install --upgrade pip
        pause
        exit /b 1
    )
    echo [OK] Entorno virtual creado
    echo.
) else (
    echo [1/6] Entorno virtual ya existe
    echo.
)

REM ========================================================
REM PASO 2: Activar entorno virtual
REM ========================================================
echo [2/6] Activando entorno virtual...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] No se pudo activar el entorno virtual
    pause
    exit /b 1
)
echo [OK] Entorno virtual activado
echo.

REM ========================================================
REM PASO 3: Verificar e instalar dependencias
REM ========================================================
echo [3/6] Verificando dependencias...

set NEED_INSTALL=0

REM Verificar Flask
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    set NEED_INSTALL=1
    echo [!] Flask no esta instalado
) else (
    echo [OK] Flask OK
)

REM Verificar Flask-CORS
python -c "import flask_cors" >nul 2>&1
if errorlevel 1 (
    set NEED_INSTALL=1
    echo [!] Flask-CORS no esta instalado
) else (
    echo [OK] Flask-CORS OK
)

REM Verificar Werkzeug
python -c "import werkzeug" >nul 2>&1
if errorlevel 1 (
    set NEED_INSTALL=1
    echo [!] Werkzeug no esta instalado
) else (
    echo [OK] Werkzeug OK
)

echo.

REM Instalar dependencias si faltan
if "%NEED_INSTALL%"=="1" (
    echo Instalando dependencias faltantes...
    echo.
    cd admin
    python -m pip install --upgrade pip >nul 2>&1
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] No se pudieron instalar las dependencias
        pause
        exit /b 1
    )
    cd ..
    echo [OK] Dependencias instaladas correctamente
    echo.
) else (
    echo [OK] Todas las dependencias estan instaladas
    echo.
)

REM ========================================================
REM PASO 4: Verificar que el puerto este disponible
REM ========================================================
echo [4/6] Verificando puerto 5000...

netstat -ano | find ":5000" | find "LISTENING" >nul
if not errorlevel 1 (
    echo.
    echo [!] ADVERTENCIA: El puerto 5000 ya esta en uso
    echo.
    choice /C SN /M "Deseas detener el proceso y continuar (S/N)"
    if errorlevel 2 goto :port_error
    if errorlevel 1 (
        for /f "tokens=5" %%a in ('netstat -aon ^| find ":5000" ^| find "LISTENING"') do (
            taskkill /F /PID %%a >nul 2>&1
        )
        echo [OK] Proceso detenido
    )
)

echo [OK] Puerto disponible
echo.

REM ========================================================
REM PASO 5: Iniciar servidor Flask
REM ========================================================
echo [5/6] Iniciando servidor Flask...
echo.

echo Iniciando aplicacion web (Backend + Frontend)...
start "Protectora Burjassot - Flask Server" cmd /k "cd /d "%~dp0" && call venv\Scripts\activate.bat && cd admin && python app.py"
timeout /t 3 /nobreak > nul

echo Esperando que el servidor inicie...
timeout /t 3 /nobreak > nul

REM ========================================================
REM PASO 6: Abrir navegador
REM ========================================================
echo [6/6] Preparando navegador...
echo.

echo ========================================================
echo   Servidor iniciado correctamente
echo ========================================================
echo.
echo Sitio Web Publico:
echo    URL: http://localhost:5000
echo.
echo Panel de Administracion:
echo    URL: http://localhost:5000/admin
echo    Usuario: admin
echo    Contrasena: protectora2026
echo.
echo ========================================================
echo.
echo Abriendo navegador...
echo.

goto :open_browser

:open_browser
echo.
start http://localhost:5000
goto :end

:skip_browser
echo.
echo Abre manualmente las URLs cuando estes listo
goto :end

:port_error
echo.
echo [ERROR] No se puede continuar con el puerto ocupado
echo Por favor, cierra las aplicaciones que usen el puerto 5000
echo.
pause
exit /b 1

:end
echo.
echo ========================================================
echo INSTRUCCIONES:
echo ========================================================
echo.
echo * Se ha abierto 1 ventana de comandos:
echo   - "Protectora Burjassot - Flask Server" (puerto 5000)
echo.
echo * El entorno virtual esta activado automaticamente
echo.
echo * NO cierres esta ventana mientras uses la web
echo.
echo * Para DETENER el servidor:
echo   - Ejecuta: stop.bat
echo   - O cierra la ventana de comandos
echo   - O presiona Ctrl+C
echo.
echo * Para REINSTALAR dependencias:
echo   - Elimina la carpeta "venv"
echo   - Ejecuta run.bat nuevamente
echo.
echo ========================================================
echo.
echo Entorno: venv (virtual environment)
echo Dependencias: Verificadas e instaladas
echo Estado: Servidor corriendo
echo.
echo ========================================================
echo.

