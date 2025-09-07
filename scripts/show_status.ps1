Param(
    [int]$Tail = 5
)

$ErrorActionPreference = "SilentlyContinue"

# Resolve repo root and log path
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$logPath = Join-Path $repoRoot.Path "logs/agent.log"

# Try to activate venv for Python deps (sounddevice)
$venvActivate = Join-Path $repoRoot.Path ".venv/Scripts/Activate.ps1"
if (Test-Path $venvActivate) { . $venvActivate }

Write-Host "=== Agent Status ===" -ForegroundColor Cyan
Write-Host "Mode: AUTO (default)"
Write-Host "Wake Word: agent (default)"
Write-Host "TTS: OFF"
Write-Host "Model: qwen2.5 via Goose"

# Audio device info via Python (best effort)
Write-Host "Input Device:" -NoNewline
try {
    python - << 'PY'
import sounddevice as sd
try:
    d = sd.default.device[0]
    if d is not None:
        print(" ", sd.query_devices(d)["name"], sep="")
    else:
        print(" default (not set)")
except Exception as e:
    print(" error:", e)
PY
} catch {
    Write-Host " (python/sounddevice unavailable)"
}

if (Test-Path $logPath) {
    Write-Host "`n=== Last $Tail log lines ===" -ForegroundColor DarkGray
    Get-Content $logPath -Tail $Tail
} else {
    Write-Host "`nNo logs found yet." -ForegroundColor DarkGray
}

