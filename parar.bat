@echo off
setlocal
rem Stops ControleInv by its Uvicorn app target, independent of the listening port.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command ^
  "$padrao = '(?i)(?:-m\s+uvicorn|uvicorn(?:\.exe)?)\s+app\.main:app';" ^
  "$processos = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('python.exe','pythonw.exe','uvicorn.exe') -and $_.CommandLine -match $padrao });" ^
  "if ($processos.Count -eq 0) { Write-Host 'Nenhum backend ControleInv (Uvicorn app.main:app) encontrado.'; exit 0 };" ^
  "$falhas = $false;" ^
  "foreach ($processo in $processos) {" ^
  "  Write-Host ('Backend encontrado: PID ' + $processo.ProcessId + ' (' + $processo.Name + ').');" ^
  "  $confirmacao = Read-Host 'Encerrar este processo? [s/N]'; if ($null -ne $confirmacao) { $confirmacao = $confirmacao.Trim() };" ^
  "  if ([string]::IsNullOrWhiteSpace($confirmacao) -or $confirmacao -notmatch '^(?i:s|sim)$') { Write-Host 'Mantido.'; continue };" ^
  "  $atual = Get-CimInstance Win32_Process -Filter ('ProcessId = ' + $processo.ProcessId) -ErrorAction SilentlyContinue;" ^
  "  if (-not $atual -or $atual.CommandLine -notmatch $padrao) { Write-Host 'Processo mudou ou ja foi encerrado; ignorado.'; continue };" ^
  "  try { Stop-Process -Id $atual.ProcessId -Force -ErrorAction Stop; Write-Host ('Backend encerrado (PID ' + $atual.ProcessId + ').') } catch { Write-Host ('Falha ao encerrar PID ' + $atual.ProcessId + ': ' + $_.Exception.Message); $falhas = $true };" ^
  "};" ^
  "if ($falhas) { exit 1 }"
if errorlevel 1 (
    echo.
    echo Ocorreu uma falha ao encerrar um dos processos.
)
echo.
pause
