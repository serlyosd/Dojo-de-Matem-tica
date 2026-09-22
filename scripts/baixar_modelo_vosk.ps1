$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$models = Join-Path $root "models"
$target = Join-Path $models "vosk-model-small-pt-0.3"
$archive = Join-Path $env:TEMP "vosk-model-small-pt-0.3.zip"
$url = "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip"

if (Test-Path (Join-Path $target "conf\model.conf") -PathType Leaf) {
    Write-Host "[PRONTO] Modelo portugues pequeno do Vosk ja esta instalado." -ForegroundColor Green
    exit 0
}

New-Item -ItemType Directory -Path $models -Force | Out-Null
Write-Host "[Dojo] Baixando o modelo portugues pequeno do Vosk..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri $url -OutFile $archive -UseBasicParsing
    Expand-Archive -Path $archive -DestinationPath $models -Force
} finally {
    Remove-Item $archive -Force -ErrorAction SilentlyContinue
}

if (-not (Test-Path (Join-Path $target "conf\model.conf") -PathType Leaf)) {
    throw "O modelo Vosk baixado nao possui a estrutura esperada."
}
Write-Host "[PRONTO] Modelo Vosk instalado em $target" -ForegroundColor Green
