param(
    [switch]$SomenteNormalizar
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$models = Join-Path $root "models"
$target = Join-Path $models "vosk-model-small-pt-0.3"
$nested = Join-Path $target "vosk-model-small-pt-0.3"
$archive = Join-Path $env:TEMP "vosk-model-small-pt-0.3.zip"
$extract = Join-Path $env:TEMP "vosk-model-small-pt-0.3-$PID"
$url = "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip"
$requiredFiles = @("final.mdl", "Gr.fst", "HCLr.fst", "mfcc.conf", "phones.txt", "word_boundary.int")

function Test-LegacyVoskModel([string]$path) {
    if (-not (Test-Path $path -PathType Container)) { return $false }
    foreach ($name in $requiredFiles) {
        if (-not (Test-Path (Join-Path $path $name))) { return $false }
    }
    return (Test-Path (Join-Path $path "ivector") -PathType Container)
}

function Normalize-NestedModel {
    if ((-not (Test-LegacyVoskModel $target)) -and (Test-LegacyVoskModel $nested)) {
        Write-Host "[Dojo] Corrigindo pasta duplicada do modelo Vosk..." -ForegroundColor Cyan
        Get-ChildItem -LiteralPath $nested -Force | Move-Item -Destination $target -Force
        Remove-Item -LiteralPath $nested -Recurse -Force
    }
}

Normalize-NestedModel
if (Test-LegacyVoskModel $target) {
    Write-Host "[PRONTO] Modelo portugues oficial do Vosk ja esta instalado." -ForegroundColor Green
    exit 0
}
if ($SomenteNormalizar) { exit 1 }

New-Item -ItemType Directory -Path $models -Force | Out-Null
Write-Host "[Dojo] Baixando o modelo portugues pequeno do Vosk..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri $url -OutFile $archive -UseBasicParsing
    Remove-Item -LiteralPath $extract -Recurse -Force -ErrorAction SilentlyContinue
    Expand-Archive -Path $archive -DestinationPath $extract -Force
    $source = Join-Path $extract "vosk-model-small-pt-0.3"
    $sourceNested = Join-Path $source "vosk-model-small-pt-0.3"
    if ((-not (Test-LegacyVoskModel $source)) -and (Test-LegacyVoskModel $sourceNested)) { $source = $sourceNested }
    if (-not (Test-LegacyVoskModel $source)) { $source = $extract }
    if (-not (Test-LegacyVoskModel $source)) {
        throw "O modelo baixado nao possui a estrutura oficial esperada."
    }
    Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction SilentlyContinue
    Move-Item -LiteralPath $source -Destination $target
} finally {
    Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $extract -Recurse -Force -ErrorAction SilentlyContinue
}

if (-not (Test-LegacyVoskModel $target)) {
    throw "O modelo Vosk instalado nao possui a estrutura oficial esperada."
}
Write-Host "[PRONTO] Modelo Vosk instalado em $target" -ForegroundColor Green
