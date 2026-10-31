@echo off
rem Verificações antes do commit: lint do backend (ruff), testes (pytest) e tipos do frontend (tsc).
setlocal
cd /d "%~dp0"
set "NODE_DIR=%LOCALAPPDATA%\nodejs-portable\node-v26.13.0-win-x64"
if exist "%NODE_DIR%\node.exe" set "PATH=%NODE_DIR%;%PATH%"

pushd backend
"..\.venv\Scripts\python.exe" -m ruff check . || goto :erro
"..\.venv\Scripts\python.exe" -m pytest -q || goto :erro
popd

call npm --prefix frontend run lint || goto :erro
echo.
echo Tudo certo.
exit /b 0

:erro
echo.
echo Verificacao falhou.
exit /b 1
