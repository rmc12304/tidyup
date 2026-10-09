@echo off
setlocal
where pyw.exe >nul 2>nul
if not errorlevel 1 (
  start "" pyw.exe -3 "%~dp0Testar Fluxo Windows.pyw"
  exit /b
)
where pythonw.exe >nul 2>nul
if not errorlevel 1 (
  start "" pythonw.exe "%~dp0Testar Fluxo Windows.pyw"
  exit /b
)
echo Instale Python 3.12 ou mais recente de python.org e abra este teste novamente.
pause
