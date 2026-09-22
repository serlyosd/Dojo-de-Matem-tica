param(
    [Parameter(Mandatory = $true)]
    [string]$Mensagem
)

try {
    [console]::Beep(880, 250)
    Start-Sleep -Milliseconds 100
    [console]::Beep(880, 250)
} catch {
    [System.Media.SystemSounds]::Exclamation.Play()
}

Write-Host "`nACAO NECESSARIA: $Mensagem" -ForegroundColor Yellow
