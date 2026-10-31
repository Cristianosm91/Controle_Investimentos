@echo off
rem Sobe o ControleInv em http://127.0.0.1:8000 (API + interface).
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

rem Recompila a interface se o build nao existir ou se algum fonte for mais novo que ele.
powershell -NoProfile -Command "$b = Get-Item 'frontend\dist\index.html' -ErrorAction SilentlyContinue; if (-not $b) { exit 1 }; $f = Get-ChildItem 'frontend\src','frontend\index.html','frontend\package.json','frontend\package-lock.json','frontend\vite.config.ts','frontend\tsconfig.json' -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt $b.LastWriteTime } | Select-Object -First 1; if ($f) { exit 1 }; exit 0"
if errorlevel 1 call :compilar || goto :erro

pushd backend
"..\.venv\Scripts\python.exe" -m alembic upgrade head || goto :erro
start "" http://127.0.0.1:8000
"..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
popd
exit /b 0

:compilar
where npm >nul 2>&1
if errorlevel 1 (
    if exist "frontend\dist\index.html" (
        echo Aviso: npm nao encontrado; usando a interface ja compilada, que pode estar desatualizada.
        exit /b 0
    )
    echo npm nao encontrado. Instale o Node.js ou ajuste NODE_DIR neste script.
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
echo Falha ao iniciar o ControleInv.
pause
exit /b 1
