@echo off
setlocal
cd /d "%~dp0.."
echo [Dojo] Preparando o aplicativo...
where py >nul 2>nul
if errorlevel 1 (
  echo ERRO: Python nao encontrado. Instale Python 3.12.
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0acao_necessaria.ps1" -Mensagem "Instale o Python 3.12 e execute este arquivo novamente."
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
if errorlevel 1 goto :erro
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :erro
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :erro
echo.
echo PRONTO: dependencias do aplicativo instaladas.
echo Agora execute scripts\verificar_windows.bat.
pause
exit /b 0
:erro
echo.
echo ERRO: a preparacao nao terminou. Confira a mensagem acima.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0acao_necessaria.ps1" -Mensagem "Confira o erro acima e execute este arquivo novamente."
pause
exit /b 1
