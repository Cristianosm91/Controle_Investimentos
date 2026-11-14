@echo off
rem Testes E2E (Playwright) da interface: banco SQLite descartavel, dados ficticios e rede externa bloqueada.
rem Nao faz parte do lint.bat. Uso: e2e.bat [argumentos do Playwright], ex.: e2e.bat --grep @smoke
rem Navegador: E2E_CHANNEL=chromium, msedge ou chrome (padrao: chromium do Playwright se instalado; senao, Edge local).
setlocal
cd /d "%~dp0"
set "NODE_DIR=%LOCALAPPDATA%\nodejs-portable\node-v26.13.0-win-x64"
if exist "%NODE_DIR%\node.exe" set "PATH=%NODE_DIR%;%PATH%"

where npm >nul 2>&1
if errorlevel 1 (
    echo npm nao encontrado. Instale o Node.js ou ajuste NODE_DIR neste script.
    exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente Python .venv nao encontrado: rode iniciar.bat uma vez antes.
    exit /b 1
)
if not exist "frontend\node_modules\@playwright\test" (
    call npm --prefix frontend install --no-fund --no-audit || goto :erro
)

rem Recompila a interface se o build nao existir ou se algum fonte for mais novo que ele (mesma regra do iniciar.bat).
powershell -NoProfile -Command "$b = Get-Item 'frontend\dist\index.html' -ErrorAction SilentlyContinue; if (-not $b) { exit 1 }; $f = Get-ChildItem 'frontend\src','frontend\index.html','frontend\package.json','frontend\package-lock.json','frontend\vite.config.ts','frontend\tsconfig.json' -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt $b.LastWriteTime } | Select-Object -First 1; if ($f) { exit 1 }; exit 0"
if errorlevel 1 (
    echo Compilando a interface...
    call npm --prefix frontend run build || goto :erro
)

call npm --prefix frontend run e2e -- %* || goto :erro
echo.
echo E2E: tudo certo. Relatorio: frontend\playwright-report\index.html
exit /b 0

:erro
echo.
echo E2E falhou. Relatorio: frontend\playwright-report\index.html; traces e screenshots em frontend\test-results.
exit /b 1
