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

if not exist "frontend\dist\index.html" (
    echo Compilando a interface...
    pushd frontend
    call npm install --no-fund --no-audit || goto :erro
    call npm run build || goto :erro
    popd
)

pushd backend
"..\.venv\Scripts\python.exe" -m alembic upgrade head || goto :erro
start "" http://127.0.0.1:8000
"..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
popd
exit /b 0

:erro
echo.
echo Falha ao iniciar o InvestHub+.
pause
exit /b 1
