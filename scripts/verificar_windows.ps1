$ErrorActionPreference = "SilentlyContinue"
$failed = $false
$nextAction = $null

function Report($ok, $label, $detail) {
    if ($ok) { Write-Host "[PRONTO] $label - $detail" -ForegroundColor Green }
    else { Write-Host "[FALTA]  $label - $detail" -ForegroundColor Yellow; $script:failed = $true }
}

function Test-LegacyVoskModel([string]$path) {
    if (-not (Test-Path $path -PathType Container)) { return $false }
    foreach ($name in @("final.mdl", "Gr.fst", "HCLr.fst", "mfcc.conf", "phones.txt", "word_boundary.int")) {
        if (-not (Test-Path (Join-Path $path $name))) { return $false }
    }
    return (Test-Path (Join-Path $path "ivector") -PathType Container)
}

function Resolve-VoskModel([string]$path) {
    if (Test-LegacyVoskModel $path) { return $path }
    $nested = Join-Path $path (Split-Path $path -Leaf)
    if (Test-LegacyVoskModel $nested) { return $nested }
    return $null
}

Write-Host "`nDojo da Matematica - verificacao da fase 1`n" -ForegroundColor Cyan
$python = Get-Command py
Report ($null -ne $python) "Python" "comando py"
if (-not $python -and -not $nextAction) { $nextAction = "Instale o Python 3.12." }
$appPython = Join-Path (Split-Path $PSScriptRoot -Parent) ".venv\Scripts\python.exe"
$dependenciesReady = $false
if (Test-Path $appPython -PathType Leaf) {
    & $appPython -c "import fastapi, httpx, multipart, uvicorn, vosk" 2>$null
    $dependenciesReady = $LASTEXITCODE -eq 0
}
Report $dependenciesReady "Aplicativo Python" ".venv e bibliotecas"
if (-not $dependenciesReady -and -not $nextAction) { $nextAction = "Execute scripts\preparar_windows.bat." }

$ollama = Get-Command ollama
Report ($null -ne $ollama) "Ollama" "programa instalado"
if (-not $ollama -and -not $nextAction) { $nextAction = "Instale e abra o Ollama." }
try {
    $tags = Invoke-RestMethod -Uri "$env:OLLAMA_URL/api/tags" -TimeoutSec 5
    Report $true "Servidor Ollama" $env:OLLAMA_URL
    $modelReady = @($tags.models | Where-Object {
        $_.name -eq $env:OLLAMA_MODEL -or $_.name.StartsWith("$($env:OLLAMA_MODEL):")
    }).Count -gt 0
    Report $modelReady "Modelo de visao" $env:OLLAMA_MODEL
    if (-not $modelReady -and -not $nextAction) { $nextAction = "Execute: ollama run $env:OLLAMA_MODEL" }
} catch {
    Report $false "Servidor Ollama" "abra o Ollama e tente novamente"
    if (-not $nextAction) { $nextAction = "Abra o Ollama." }
}

$resolvedVoskModel = Resolve-VoskModel $env:VOSK_MODEL_DIR
$voskModelReady = $null -ne $resolvedVoskModel
$ffmpegReady = Test-Path $env:FFMPEG -PathType Leaf
Report $voskModelReady "Modelo Vosk portugues pequeno" $env:VOSK_MODEL_DIR
Report $ffmpegReady "FFmpeg" $env:FFMPEG
if (-not $voskModelReady -and -not $nextAction) { $nextAction = "Execute scripts\preparar_windows.bat para baixar o modelo Vosk." }
if (-not $ffmpegReady -and -not $nextAction) { $nextAction = "Coloque ffmpeg.exe na pasta tools\ffmpeg\bin." }

$voskRuntimeReady = $false
if ($dependenciesReady -and $voskModelReady) {
    $env:VOSK_MODEL_DIR = $resolvedVoskModel
    & $appPython -c "import os; from vosk import Model,SetLogLevel; SetLogLevel(-1); Model(os.environ['VOSK_MODEL_DIR'])" 2>$null
    $voskRuntimeReady = $LASTEXITCODE -eq 0
}
Report $voskRuntimeReady "Vosk no processador" "modelo carregado neste computador"
if (-not $voskRuntimeReady -and -not $nextAction) { $nextAction = "Execute scripts\preparar_windows.bat novamente." }

$drive = Get-PSDrive -Name ([System.IO.Path]::GetPathRoot($env:LOCALAPPDATA).Substring(0,1))
if ($drive) {
    $diskReady = $drive.Free -gt 5GB
    Report $diskReady "Espaco livre" ("{0:N1} GB" -f ($drive.Free / 1GB))
    if (-not $diskReady -and -not $nextAction) { $nextAction = "Libere pelo menos 5 GB no disco." }
}

if ($failed) {
    & "$PSScriptRoot\acao_necessaria.ps1" -Mensagem $nextAction
    exit 1
}
Write-Host "`n[INSTALADO] Componentes encontrados. Isto nao comprova o fluxo completo." -ForegroundColor Green
Write-Host "[PROXIMO] Execute scripts\diagnosticar_windows.bat com um audio ficticio." -ForegroundColor Cyan
exit 0
