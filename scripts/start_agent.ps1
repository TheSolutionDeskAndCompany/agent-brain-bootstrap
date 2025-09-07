param(
  [ValidateSet("ptt","auto")] [string]$Mode = "ptt",
  [switch]$NoTTS = $true
)

Write-Host "[bootstrap] Loading env & paths..." -ForegroundColor Cyan

# Set error action preference
$ErrorActionPreference = "Stop"

# Set working directory to script root
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Split-Path -Parent $scriptRoot
Set-Location $projectRoot

# Activate virtual environment
$venvScripts = Join-Path $projectRoot ".venv\Scripts"
$venvActivate = Join-Path $venvScripts "Activate.ps1"

if (-not (Test-Path $venvScripts)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

if (Test-Path $venvActivate) {
    try {
        & $venvActivate
    } catch {
        Write-Host "Warning: Failed to activate virtual environment" -ForegroundColor Yellow
    }
}

# Install required packages
$requiredPackages = @("requests", "sounddevice", "numpy", "python-dotenv")
foreach ($pkg in $requiredPackages) {
    python -m pip install --quiet $pkg
}

# Set PYTHONPATH
$env:PYTHONPATH = $projectRoot

# Info banner
Write-Host ("[goose] Provider configured? {0}" -f (goose info 2>$null)) -ForegroundColor DarkGray
if ($NoTTS) { Write-Host "[agent] TTS disabled" -ForegroundColor Yellow }

# Launch the agent
$flags = @("--mode", $Mode)
if ($NoTTS) { $flags += "--no-tts" }

Write-Host "Starting agent..." -ForegroundColor Cyan
python -m agent.agent_main @flags
