# Wait until backend and Vite respond, then open the browser (called from 启动.bat)
$ErrorActionPreference = 'Continue'

function Wait-Http {
    param([string]$Uri, [string]$Label, [int]$MaxSeconds)
    Write-Host "Waiting for $Label ($Uri) ..."
    for ($i = 0; $i -lt $MaxSeconds; $i++) {
        try {
            $null = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 2
            Write-Host "OK: $Label"
            return $true
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    Write-Host "Timeout: $Label - check logs\backend.err.log or frontend.err.log"
    return $false
}

$null = Wait-Http -Uri 'http://127.0.0.1:8011/api/health' -Label 'backend' -MaxSeconds 90
$null = Wait-Http -Uri 'http://127.0.0.1:5173/' -Label 'frontend' -MaxSeconds 120
Start-Process 'http://localhost:5173/'
