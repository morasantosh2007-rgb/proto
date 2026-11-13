# JARVIS One-Command Run Script for Windows PowerShell
param (
    [switch]$Text,
    [switch]$DryRun
)

if (Test-Path ".\venv\Scripts\Activate.ps1") {
    & ".\venv\Scripts\Activate.ps1"
}

$argsList = @()
if ($Text) { $argsList += "--text" }
if ($DryRun) { $argsList += "--dry-run" }

python -m jarvis @argsList
