<#
.SYNOPSIS
Starts the GazarZar FastAPI server for production.

.DESCRIPTION
This script checks if a virtual environment exists, activates it, installs dependencies if necessary, and starts the server using Uvicorn.
#>

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $ScriptDir

Write-Host "Starting GazarZar Production Server..." -ForegroundColor Green

if (-Not (Test-Path "venv")) {
    Write-Host "Virtual environment not found. Creating one..." -ForegroundColor Yellow
    python -m venv venv
}

Write-Host "Activating virtual environment..."
& .\venv\Scripts\Activate.ps1

Write-Host "Installing/Verifying dependencies..."
pip install -r requirements.txt | Out-Null

if (-Not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
        Copy-Item ".env.example" -Destination ".env"
    } else {
        Write-Host "Warning: .env file missing!" -ForegroundColor Red
    }
}

Write-Host "Seeding database..."
python seed_data.py

Write-Host "Starting server..." -ForegroundColor Green
uvicorn app.main:app --host 0.0.0.0 --port 8000
