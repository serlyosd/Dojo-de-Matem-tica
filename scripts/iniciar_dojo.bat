@echo off
setlocal
cd /d "%~dp0.."
call "%~dp0configurar_dojo.bat"
if not exist ".venv\Scripts\python.exe" (
  echo FALTA PREPARAR: execute scripts\preparar_windows.bat primeiro.
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0acao_necessaria.ps1" -Mensagem "Execute scripts\preparar_windows.bat."
  pause
  exit /b 1
)
echo [Dojo] Abrindo em http://127.0.0.1:8000
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 (
  echo.
  echo O aplicativo parou com erro. Confira a mensagem acima.
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0acao_necessaria.ps1" -Mensagem "Leia o ultimo erro exibido nesta janela."
  pause
)
