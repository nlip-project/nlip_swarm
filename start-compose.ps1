#!/usr/bin/env pwsh
# Load environment variables from models.ini and run Docker Compose

# Read models.ini and set environment variables
$iniVars = & python scripts/load_models_ini.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to load models.ini"
    exit 1
}

foreach ($line in $iniVars) {
    if ($line -match '^([^=]+)=(.+)$') {
        $varName = $matches[1]
        $varValue = $matches[2]
        Set-Item -Path "env:$varName" -Value $varValue
        Write-Host "Set $varName=$varValue" -ForegroundColor Green
    }
}

# Run docker compose with all arguments passed to this script
Write-Host "`nStarting Docker Compose..." -ForegroundColor Cyan
docker compose @args
