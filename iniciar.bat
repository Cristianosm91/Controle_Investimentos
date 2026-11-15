@echo off
rem Sobe o InvestHub+ em http://127.0.0.1:8000 (API + interface).
setlocal
cd /d "%~dp0"

set "NODE_DIR=%LOCALAPPDATA%\nodejs-portable\node-v26.13.0-win-x64"
if exist "%NODE_DIR%\node.exe" set "PATH=%NODE_DIR%;%PATH%"

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente Python...
    python -m venv .venv || goto :erro
    set PIP_USER=0
    ".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt || goto :erro
)

echo.
echo [1] Recompilar a interface e iniciar
echo [2] Iniciar sem recompilar (usar o build existente)
choice /C 12 /N /M "Escolha uma opcao [1/2]: "
if errorlevel 2 goto :sem_compilar
if errorlevel 1 goto :compilar_interface
goto :erro

:compilar_interface
call :compilar
if errorlevel 1 goto :erro
goto :iniciar

:sem_compilar
if not exist "frontend\dist\index.html" (
    echo Build da interface nao encontrado. Escolha recompilar para gerar os arquivos.
    goto :erro
)

:iniciar

pushd backend
rem Backup verificado do banco antes de aplicar migracoes pendentes; se falhar, nao migra nem sobe o app.
"..\.venv\Scripts\python.exe" -m scripts.backup_antes_migrar || goto :erro
"..\.venv\Scripts\python.exe" -m alembic upgrade head || goto :erro
rem Abre o navegador so quando a API responder (o Uvicorn leva alguns segundos para subir).
start "" /b powershell -NoProfile -Command "$u = 'http://127.0.0.1:8000'; for ($i = 0; $i -lt 120; $i++) { try { Invoke-WebRequest ($u + '/api/saude') -UseBasicParsing -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep -Milliseconds 500 } }; Start-Process $u"
"..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
popd
exit /b 0

:compilar
where npm >nul 2>&1
if errorlevel 1 (
    echo npm nao encontrado. Instale o Node.js ou ajuste NODE_DIR para recompilar a interface.
    exit /b 1
)
echo Compilando a interface...
pushd frontend
if not exist "node_modules" (
    call npm install --no-fund --no-audit || (popd & exit /b 1)
) else (
    powershell -NoProfile -Command "$m = Get-Item 'node_modules\.package-lock.json' -ErrorAction SilentlyContinue; if (-not $m -or (Get-Item 'package-lock.json').LastWriteTime -gt $m.LastWriteTime) { exit 1 }; exit 0"
    if errorlevel 1 call npm install --no-fund --no-audit || (popd & exit /b 1)
)
call npm run build || (popd & exit /b 1)
popd
exit /b 0

:erro
echo.
echo Falha ao iniciar o InvestHub+.
pause
exit /b 1
