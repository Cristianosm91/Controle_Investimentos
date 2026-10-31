@echo off
rem Modo desenvolvimento: API com reload (8000) + Vite com hot reload (5173).
setlocal
cd /d "%~dp0"
set "NODE_DIR=%LOCALAPPDATA%\nodejs-portable\node-v26.13.0-win-x64"
if exist "%NODE_DIR%\node.exe" set "PATH=%NODE_DIR%;%PATH%"

start "ControleInv API" cmd /k "cd /d backend && ..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
start "ControleInv Front" cmd /k "cd /d frontend && npm run dev"
start "" http://127.0.0.1:5173
