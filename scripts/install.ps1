# JARVIS One-Command Installer for Windows PowerShell
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       JARVIS Personal AI Assistant Setup & Installer     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Python Version
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Python 3.11+ is required but not found in PATH." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Detected: $pythonVersion" -ForegroundColor Green

# 2. Create Virtual Environment if not present
if (-not (Test-Path "venv")) {
    Write-Host "[INFO] Creating virtual environment 'venv'..." -ForegroundColor Yellow
    python -m venv venv
}

# 3. Activate Virtual Environment
$venvActivate = ".\venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    & $venvActivate
}

# 4. Install Dependencies
Write-Host "[INFO] Installing required dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip
if (Test-Path "requirements.txt") {
    python -m pip install -r requirements.txt
} else {
    python -m pip install faster-whisper edge-tts sounddevice keyring pywin32-ctypes Pillow psutil rapidfuzz rich pyyaml requests
}

# 5. Run System Doctor
Write-Host "[INFO] Running JARVIS system diagnostics..." -ForegroundColor Yellow
python -m jarvis doctor

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Installation Complete! Start JARVIS using: .\scripts\run.ps1" -ForegroundColor Green
Write-Host "Or run in text mode: python -m jarvis --text" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
