Param(
  [string]$Profile = "public/rdp/desktop.rdp"
)

Write-Host "[rdp] Reconnecting using profile: $Profile" -ForegroundColor Cyan

if (-not (Test-Path $Profile)) {
  Write-Host "Profile not found. Generate one with:" -ForegroundColor Yellow
  Write-Host "  python scripts/rdp_profile_generator.py --host <RDP_HOST> --username <USER>" -ForegroundColor DarkGray
  exit 1
}

try {
  # Use shell to open RDP profile with default app
  Start-Process $Profile
  Write-Host "Launched RDP client." -ForegroundColor Green
} catch {
  Write-Error $_.Exception.Message
  exit 1
}

