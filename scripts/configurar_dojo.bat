@echo off
rem Ajuste apenas se os arquivos estiverem em outro lugar.
set "OLLAMA_URL=http://127.0.0.1:11434"
set "OLLAMA_MODEL=qwen3-vl:4b"
set "VOSK_MODEL_DIR=%~dp0..\models\vosk-model-small-pt-0.3"
set "FFMPEG=%~dp0..\tools\ffmpeg\bin\ffmpeg.exe"
set "DOJO_DATA_DIR=%LOCALAPPDATA%\DojoDaMatematica"
set "AUDIO_TIMEOUT_SECONDS=120"
set "MAX_AUDIO_SECONDS=60"
