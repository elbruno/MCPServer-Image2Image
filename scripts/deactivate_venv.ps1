# Deactivate the Python virtual environment for PowerShell
# Usage: .\scripts\deactivate_venv.ps1
# Dot-source this script to keep deactivation in the current session:
#   . .\scripts\deactivate_venv.ps1

$deactivatePath = Join-Path $PSScriptRoot "..\venv\Scripts\Deactivate.ps1" | Resolve-Path -ErrorAction SilentlyContinue
if (-not $deactivatePath) {
    # If Deactivate.ps1 isn't present (older venvs), try calling "deactivate" function if defined
    if (Get-Command -Name deactivate -ErrorAction SilentlyContinue) {
        deactivate
        Write-Host "Virtual environment deactivated." -ForegroundColor Green
        return
    }

    Write-Error "Could not find venv deactivation script at '../venv/Scripts/Deactivate.ps1'. If your venv doesn't include Deactivate.ps1, try using 'deactivate' if available."
    exit 1
}

. $deactivatePath
Write-Host "Virtual environment deactivated." -ForegroundColor Green
