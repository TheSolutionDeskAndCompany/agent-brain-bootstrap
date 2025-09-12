Param(
  [Parameter(Mandatory=$true)][string]$Name,
  [Parameter(Mandatory=$true)][string]$Value
)

Write-Host "[secrets] Storing secret '$Name' into Windows Credential Manager via python-keyring" -ForegroundColor Cyan

try {
  # Ensure keyring is available
  python -c "import keyring" 2>$null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing keyring..." -ForegroundColor Yellow
    python -m pip install --quiet keyring
  }

  $code = @"
import sys, keyring
name = sys.argv[1]
value = sys.argv[2]
keyring.set_password('agent-brain', name, value)
print('OK')
"@
  $out = python - <<PY
$code
PY
  if ($LASTEXITCODE -eq 0) { Write-Host "[secrets] Stored." -ForegroundColor Green }
  else { Write-Error "Failed to store secret (python exit $LASTEXITCODE)" }
} catch {
  Write-Error $_.Exception.Message
  exit 1
}

Write-Host "Tip: Leave the matching value blank in your .env to prefer keyring." -ForegroundColor DarkGray

