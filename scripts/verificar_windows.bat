@echo off
setlocal
cd /d "%~dp0.."
call "%~dp0configurar_dojo.bat"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0verificar_windows.ps1"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (echo PRONTO: os componentes foram encontrados.) else (echo PENDENTE: instale ou ajuste os itens marcados acima.)
pause
exit /b %RESULT%

