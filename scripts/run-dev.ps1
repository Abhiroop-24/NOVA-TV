# NOVA TV — Development/simulation runner for Windows.
#
# Runs the interface in a windowed "dev" mode with HDMI-CEC disabled so you
# can test D-pad navigation with a keyboard on your development computer.
#
# Usage from the repo root:
#     powershell -ExecutionPolicy Bypass -File scripts\run-dev.ps1
#
# First time only — set up the environment:
#     python -m venv .venv
#     .\.venv\Scripts\Activate.ps1
#     pip install -r requirements.txt
#     python scripts\generate_assets.py all

param([string[]]$ExtraArgs)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

# Prefer a local venv, fall back to system python
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $Py = $VenvPython
} else {
    $Py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $Py) {
        $Py = (Get-Command py -ErrorAction SilentlyContinue).Source
    }
}

if (-not $Py) {
    Write-Host "No Python interpreter found." -ForegroundColor Red
    Write-Host "Install Python 3.9+ from https://www.python.org/ then run:" -ForegroundColor Yellow
    Write-Host "    python -m venv .venv" -ForegroundColor Yellow
    Write-Host "    .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "    pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

$env:NOVA_DEV = "1"
& $Py -m nova.main --dev --no-cec @ExtraArgs
