@echo off
rem Ajuste apenas se os arquivos estiverem em outro lugar.
set "OLLAMA_URL=http://127.0.0.1:11434"
set "OLLAMA_MODEL=qwen3-vl:4b"
set "WHISPER_CLI=%~dp0..\tools\whisper\whisper-cli.exe"
set "WHISPER_MODEL=%~dp0..\models\ggml-small.bin"
set "FFMPEG=%~dp0..\tools\ffmpeg\bin\ffmpeg.exe"
set "DOJO_DATA_DIR=%LOCALAPPDATA%\DojoDaMatematica"

