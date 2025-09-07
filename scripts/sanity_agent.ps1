Param(
    [ValidateSet('ptt','auto')]
    [string]$Mode = 'ptt',
    [switch]$NoTTS = $true,
    [int]$Device,
    [int]$Threshold = 900,
    [string]$WakeWord = 'agent'
)

Write-Host "[sanity] Agent Brain sanity check ($Mode, NoTTS=$NoTTS, WakeWord=$WakeWord)" -ForegroundColor Cyan

# Try to activate local venv if present
$venvActivate = Join-Path $PSScriptRoot '..' | Join-Path -ChildPath '.venv\Scripts\Activate.ps1'
if (Test-Path $venvActivate) {
    Write-Host "[sanity] Activating virtual environment" -ForegroundColor DarkGray
    . $venvActivate
}

# Build argument list
$argsList = @('agent/agent_main.py', '--mode', $Mode)
if ($NoTTS) { $argsList += '--no-tts' }
if ($PSBoundParameters.ContainsKey('Device')) { $argsList += @('--device', $Device) }
if ($Mode -eq 'auto') { $argsList += @('--threshold', $Threshold) }
if ($PSBoundParameters.ContainsKey('WakeWord')) { $argsList += @('--wake-word', $WakeWord) }

Write-Host "[sanity] Running: python $($argsList -join ' ')" -ForegroundColor DarkGray
python @argsList

if ($LASTEXITCODE -ne 0) {
    Write-Host "[sanity] Agent exited with code $LASTEXITCODE" -ForegroundColor Yellow
} else {
    Write-Host "[sanity] Agent exited cleanly" -ForegroundColor Green
}
