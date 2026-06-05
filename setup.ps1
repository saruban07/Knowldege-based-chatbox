# Discord KB Support Bot — Windows setup script
# Usage: .\setup.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Discord KB Support Bot — Setup" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found. Install Python 3.10+ from https://python.org" -ForegroundColor Red
    exit 1
}

# Create venv if missing
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "[OK] Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "[OK] Virtual environment exists" -ForegroundColor Green
}

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
& "venv\Scripts\pip.exe" install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "[OK] Dependencies installed" -ForegroundColor Green

# Create .env from example if missing
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[ACTION] Created .env from .env.example" -ForegroundColor Yellow
    Write-Host "         Edit .env and add your DISCORD_TOKEN and GROQ_API_KEY" -ForegroundColor Yellow
} else {
    Write-Host "[OK] .env already exists" -ForegroundColor Green
}

# Create required directories
@("kb", "tickets", "chroma_db") | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ | Out-Null
    }
}

Write-Host ""
Write-Host "Running setup checks..." -ForegroundColor Yellow
& "venv\Scripts\python.exe" check_setup.py
$checkExit = $LASTEXITCODE

Write-Host ""
if ($checkExit -eq 0) {
    Write-Host "Setup complete! Start the bot with:" -ForegroundColor Green
    Write-Host "  venv\Scripts\activate" -ForegroundColor White
    Write-Host "  python bot.py" -ForegroundColor White
} else {
    Write-Host "Setup checks failed. Fix .env and run again:" -ForegroundColor Red
    Write-Host "  notepad .env" -ForegroundColor White
    Write-Host "  .\setup.ps1" -ForegroundColor White
}

exit $checkExit
