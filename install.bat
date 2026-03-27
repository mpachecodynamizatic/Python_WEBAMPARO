@echo off
setlocal enabledelayedexpansion
echo ============================================================
echo INSTALADOR AUTOMATIZADO - Proyecto Python + GitHub
echo Usuario GitHub: mpacheco@dynamizatic.com
echo ============================================================
echo.

REM Verificar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado o no esta en el PATH
    echo.
    echo Por favor instala Python desde: https://python.org
    echo Asegurate de marcar "Add Python to PATH" durante la instalacion
    pause
    exit /b 1
)

echo [OK] Python encontrado
python --version
echo.

REM Verificar si Git está instalado
git --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Git no encontrado - no es obligatorio para el funcionamiento
) else (
    echo [OK] Git encontrado
    
    REM Verificar si ya existe un repositorio Git
    if exist ".git" (
        echo [OK] Repositorio Git encontrado
        
        REM Obtener el nombre de la carpeta actual
        for %%I in (.) do set "PROJECT_NAME=%%~nxI"
        
        REM Detectar usuario de GitHub automáticamente
        for /f "tokens=*" %%i in ('gh api user --jq .login 2^>nul') do set "GITHUB_USER=%%i"
        if "!GITHUB_USER!"=="" set "GITHUB_USER=mpacheco@dynamizatic.com"
        
        echo [INFO] Verificando sincronizacion con GitHub...
        echo [INFO] Usuario GitHub: !GITHUB_USER!
        echo [INFO] Repositorio: !PROJECT_NAME!
        
        REM Verificar y sincronizar repositorio existente
        call :sync_github_repo
    ) else (
        echo.
        echo [INFO] No se encontro repositorio Git - creando automaticamente...
        
        REM Crear repositorio automáticamente
        REM Crear repositorio automáticamente
        echo [INFO] Inicializando repositorio Git automaticamente...
        git init
        if errorlevel 1 (
            echo [ERROR] Error inicializando repositorio Git
        ) else (
            echo [OK] Repositorio Git creado exitosamente
            
            REM Crear .gitignore si no existe
            if not exist ".gitignore" (
                echo [INFO] Creando archivo .gitignore...
                (
                    echo # Entorno virtual
                    echo .venv/
                    echo __pycache__/
                    echo *.pyc
                    echo.
                    echo # Archivos de salida
                    echo *.xlsx
                    echo *.csv
                    echo.
                    echo # Archivos del sistema
                    echo .DS_Store
                    echo Thumbs.db
                    echo desktop.ini
                    echo.
                    echo # Archivos temporales
                    echo *.tmp
                    echo *.temp
                    echo ~*
                ) > .gitignore
                echo [OK] Archivo .gitignore creado
            )
            
            echo [INFO] Agregando archivos al repositorio...
            git add .
            git commit -m "Initial commit: Descargador de Correos de Microsoft"
            if errorlevel 1 (
                echo [WARNING] Error haciendo commit inicial
            ) else (
                echo [OK] Commit inicial realizado
            )
            
            REM Obtener el nombre de la carpeta actual y configurar GitHub
            for %%I in (.) do set "PROJECT_NAME=%%~nxI"
            
            REM Detectar usuario de GitHub automáticamente
            for /f "tokens=*" %%i in ('gh api user --jq .login 2^>nul') do set "GITHUB_USER=%%i"
            if "!GITHUB_USER!"=="" set "GITHUB_USER=mpacheco@dynamizatic.com"
            
            echo.
            echo [INFO] Creando repositorio en GitHub automaticamente...
            echo [INFO] Usuario GitHub: !GITHUB_USER!
            echo [INFO] Nombre del repositorio: !PROJECT_NAME!
            
            REM Crear y sincronizar repositorio
            call :create_github_repo
        )
    )
)

echo.
goto :continue_installation

REM Función para crear repositorio en GitHub
:create_github_repo
echo [INFO] Verificando GitHub CLI...
gh --version >nul 2>&1
if errorlevel 1 (
    REM Verificar si GitHub CLI está instalado pero no en PATH
    if exist "C:\Program Files\GitHub CLI\gh.exe" (
        echo [INFO] GitHub CLI encontrado - agregando al PATH temporalmente...
        set "PATH=%PATH%;C:\Program Files\GitHub CLI"
        gh --version >nul 2>&1
        if errorlevel 1 (
            echo [WARNING] Error configurando GitHub CLI
            goto :github_manual_setup
        ) else (
            echo [OK] GitHub CLI configurado exitosamente!
            goto :github_auto_setup
        )
    ) else (
        echo [WARNING] GitHub CLI no encontrado
        goto :github_manual_setup
    )
) else (
    echo [OK] GitHub CLI encontrado y configurado
    goto :github_auto_setup
)

:github_manual_setup
echo.
echo [INFO] Para configurar GitHub automaticamente:
echo [INFO] Ejecuta: setup_github.bat
echo.
echo [INFO] O instala manualmente:
echo [INFO] 1. Descarga desde: https://cli.github.com/
echo [INFO] 2. Instala el archivo descargado
echo [INFO] 3. Reinicia PowerShell/CMD
echo [INFO] 4. Ejecuta: gh auth login
echo [INFO] 5. Ejecuta: gh repo create !PROJECT_NAME! --public --source=. --push
echo.
echo [INFO] Configurando repositorio local para GitHub...
git remote remove origin >nul 2>&1
git remote add origin https://github.com/!GITHUB_USER!/!PROJECT_NAME!.git
git branch -M main

echo [INFO] URL del repositorio: https://github.com/!GITHUB_USER!/!PROJECT_NAME!
echo [INFO] Una vez configurado GitHub CLI, ejecuta: git push -u origin main
goto :eof

:github_auto_setup

echo [OK] GitHub CLI disponible - configurando automaticamente...

REM Verificar autenticación
gh auth status >nul 2>&1
if errorlevel 1 (
    echo [INFO] Autenticando con GitHub CLI automaticamente...
    echo [INFO] Se abrira el navegador para autenticacion...
    gh auth login --hostname github.com --git-protocol https --web
    if errorlevel 1 (
        echo [WARNING] Error en autenticacion
        echo [INFO] Configurando repositorio local...
        git remote remove origin >nul 2>&1
        git remote add origin https://github.com/!GITHUB_USER!/!PROJECT_NAME!.git
        git branch -M main
        echo [INFO] Autentica manualmente: gh auth login
        echo [INFO] Luego crea el repo: gh repo create !PROJECT_NAME! --public --source=. --push
        goto :eof
    )
)

echo [OK] Autenticacion verificada

REM Verificar si el repositorio ya existe en GitHub
echo [INFO] Verificando si el repositorio existe en GitHub...
gh repo view !PROJECT_NAME! >nul 2>&1
if errorlevel 1 (
    echo [INFO] Repositorio no existe - creando automaticamente...
    
    REM Crear repositorio público automáticamente
    echo [INFO] Creando repositorio publico en GitHub...
    gh repo create !PROJECT_NAME! --public --source=. --remote=origin --push
    
    if errorlevel 1 (
        echo [WARNING] Error creando repositorio automaticamente
        echo [INFO] Intentando metodo alternativo...
        git remote remove origin >nul 2>&1
        git remote add origin https://github.com/!GITHUB_USER!/!PROJECT_NAME!.git
        git branch -M main
        echo [INFO] Crea manualmente: gh repo create !PROJECT_NAME! --public
        echo [INFO] Luego: git push -u origin main
    ) else (
        echo [OK] Repositorio creado y sincronizado automaticamente!
        echo [INFO] URL: https://github.com/!GITHUB_USER!/!PROJECT_NAME!
    )
) else (
    echo [OK] Repositorio ya existe en GitHub
    echo [INFO] Configurando conexion local...
    
    REM Configurar remote si no existe
    git remote get-url origin >nul 2>&1
    if errorlevel 1 (
        git remote add origin https://github.com/!GITHUB_USER!/!PROJECT_NAME!.git
    )
    
    REM Sincronizar con GitHub
    git branch -M main
    echo [INFO] Sincronizando con repositorio existente...
    git push -u origin main
    
    if errorlevel 1 (
        echo [INFO] Sincronizando con pull primero...
        git pull origin main --allow-unrelated-histories >nul 2>&1
        git push -u origin main
        if errorlevel 1 (
            echo [WARNING] Error sincronizando - posibles conflictos
            echo [INFO] Resuelve manualmente: git pull origin main
        ) else (
            echo [OK] Sincronizacion completada!
        )
    ) else (
        echo [OK] Repositorio sincronizado con GitHub!
    )
    
    echo [INFO] URL: https://github.com/!GITHUB_USER!/!PROJECT_NAME!
)
goto :eof

REM Función para sincronizar repositorio existente
:sync_github_repo
gh --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] GitHub CLI no encontrado - sincronizacion manual disponible
    git remote get-url origin >nul 2>&1
    if errorlevel 1 (
        echo [INFO] Configurando remote origin...
        git remote add origin https://github.com/!GITHUB_USER!/!PROJECT_NAME!.git
    )
    echo [INFO] Para sincronizar: git push -u origin main
    goto :eof
)

echo [OK] GitHub CLI disponible
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo [INFO] Configurando conexion con GitHub...
    git remote add origin https://github.com/!GITHUB_USER!/!PROJECT_NAME!.git
)

echo [INFO] Verificando estado del repositorio...
git status --porcelain >nul 2>&1

REM Verificar si hay cambios para commit
git diff --staged --quiet >nul 2>&1
if errorlevel 1 (
    echo [INFO] Hay cambios sin commit - creando commit automatico...
    git add .
    git commit -m "Actualizacion automatica desde install.bat"
)

echo [INFO] Sincronizando con GitHub...
git push -u origin main >nul 2>&1
if errorlevel 1 (
    echo [INFO] Primera sincronizacion o cambios remotos detectados...
    git pull origin main --allow-unrelated-histories >nul 2>&1
    git push -u origin main >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] Error de sincronizacion - revisar manualmente
    ) else (
        echo [OK] Repositorio sincronizado exitosamente!
    )
) else (
    echo [OK] Repositorio actualizado en GitHub!
)

echo [INFO] URL: https://github.com/!GITHUB_USER!/!PROJECT_NAME!
goto :eof

:continue_installation



echo.
echo ============================================================
echo [EXITO] INSTALACION COMPLETADA EXITOSAMENTE!
echo ============================================================
echo.
