@echo off
setlocal
cd /d "%~dp0.."
call "%~dp0configurar_dojo.bat"
if "%~1"=="" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0acao_necessaria.ps1" -Mensagem "Arraste um arquivo de audio sobre scripts\diagnosticar_windows.bat."
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\diagnosticar_fluxos.py --audio "%~1"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (echo PRONTO: fluxo testado de ponta a ponta.) else (echo FALHA: leia a etapa e o detalhe acima.)
pause
exit /b %RESULT%
