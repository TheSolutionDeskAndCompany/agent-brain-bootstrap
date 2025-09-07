Param(
    [ValidateSet('ptt','auto')]
    [string]$Mode = 'auto',
    [switch]$NoTTS,
    [int]$Device,
    [int]$Threshold = 900,
    [string]$WakeWord = 'agent'
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

# Install required packages (lightweight)
$requiredPackages = @("requests", "sounddevice", "numpy", "python-dotenv")
foreach ($pkg in $requiredPackages) {
    try { python -m pip show $pkg 1>$null 2>$null } catch { }
    if ($LASTEXITCODE -ne 0) {
        python -m pip install --disable-pip-version-check --quiet $pkg
    }
}

# Set PYTHONPATH
$env:PYTHONPATH = $projectRoot

# Info banner
Write-Host "[agent] Starting ($Mode) | TTS: OFF | WakeWord: $WakeWord" -ForegroundColor Cyan

# Build argument list for Python
$argsList = @('agent/agent_main.py', '--mode', $Mode, '--no-tts')
if ($PSBoundParameters.ContainsKey('Device')) { $argsList += @('--device', $Device) }
if ($Mode -eq 'auto') { $argsList += @('--threshold', $Threshold) }
if ($PSBoundParameters.ContainsKey('WakeWord')) { $argsList += @('--wake-word', $WakeWord) }

python @argsList
