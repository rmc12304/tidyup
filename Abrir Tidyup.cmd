@echo off
setlocal
where pyw.exe >nul 2>nul
if not errorlevel 1 (
  start "" pyw.exe -3 "%~dp0Abrir Tidyup.pyw"
  exit /b
)
where pythonw.exe >nul 2>nul
if not errorlevel 1 (
  start "" pythonw.exe "%~dp0Abrir Tidyup.pyw"
  exit /b
)
echo Para abrir o Tidyup, instale Python 3.12 ou mais recente de python.org.
echo Marque a opcao do launcher ou de adicionar Python ao PATH na instalacao.
echo Depois, abra este arquivo novamente com duplo clique.
pause
