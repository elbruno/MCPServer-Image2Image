# Activate the Python virtual environment for PowerShell
# Usage: .\scripts\activate_venv.ps1
# Dot-source this script to keep activation in the current session:
#   . .\scripts\activate_venv.ps1

$venvPath = Join-Path $PSScriptRoot "..\venv\Scripts\Activate.ps1" | Resolve-Path -ErrorAction SilentlyContinue
if (-not $venvPath) {
    Write-Error "Could not find venv activation script at '../venv/Scripts/Activate.ps1'. Ensure the virtual environment exists."
    exit 1
}

# Dot-source the venv activation script
. $venvPath
Write-Host "Virtual environment activated." -ForegroundColor Green
