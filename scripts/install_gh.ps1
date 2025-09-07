<# scripts/install_gh.ps1
   Installs GitHub CLI (gh) via MSI on Windows.
   Run from an elevated PowerShell:  .\scripts\install_gh.ps1
#>

[CmdletBinding()]
param(
  [switch]$SkipLogin
)

function Write-Info($msg){ Write-Host $msg -ForegroundColor Cyan }
function Write-Ok($msg){ Write-Host $msg -ForegroundColor Green }
function Write-Warn($msg){ Write-Host $msg -ForegroundColor Yellow }
function Write-Err($msg){ Write-Host $msg -ForegroundColor Red }

# 1) Admin check
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  Write-Err "Please run this script in an ELEVATED PowerShell (Run as administrator)."
  exit 1
}

# 2) If gh already installed, short-circuit (but still offer login)
try {
  $v = (gh --version) 2>$null
  if ($LASTEXITCODE -eq 0 -and $v) {
    Write-Ok "GitHub CLI already installed:`n$v"
    if (-not $SkipLogin) {
      Write-Info "Checking authentication status..."
      gh auth status 2>$null
      if ($LASTEXITCODE -ne 0) {
        Write-Info "Launching: gh auth login"
        gh auth login
      } else {
        Write-Ok "Already authenticated."
      }
    }
    exit 0
  }
} catch {}

# 3) Get latest MSI from GitHub Releases
Write-Info "Fetching latest GitHub CLI release info..."
try {
  $release = Invoke-RestMethod https://api.github.com/repos/cli/cli/releases/latest
} catch {
  Write-Err "Failed to reach GitHub API. Check your network or proxy."
  exit 1
}
$asset = $release.assets | Where-Object { $_.name -match 'windows_amd64\.msi$' } | Select-Object -First 1
if (-not $asset) {
  Write-Err "Could not find a Windows x64 MSI in the latest release assets."
  exit 1
}

# 4) Download MSI
$msiUrl = $asset.browser_download_url
$msi = Join-Path $env:TEMP 'gh.msi'
Write-Info "Downloading: $msiUrl"
Invoke-WebRequest -Uri $msiUrl -OutFile $msi

# 5) Silent install
Write-Info "Installing GitHub CLI..."
Start-Process msiexec.exe -ArgumentList "/i `"$msi`" /qn" -Wait
Remove-Item $msi -ErrorAction SilentlyContinue

# 6) PATH nudge for current session
$ghBin = Join-Path $Env:ProgramFiles 'GitHub CLI'
if (Test-Path $ghBin) {
  $env:Path = "$env:Path;$ghBin"
}

# 7) Verify
try {
  $ver = gh --version
  if ($LASTEXITCODE -ne 0) { throw "gh not found on PATH yet." }
  Write-Ok "Installed successfully:`n$ver"
} catch {
  Write-Warn "gh not found in this session. Open a NEW PowerShell window and run: gh --version"
  exit 0
}

# 8) Login (optional)
if (-not $SkipLogin) {
  Write-Info "Checking authentication status..."
  gh auth status 2>$null
  if ($LASTEXITCODE -ne 0) {
    Write-Info "Launching: gh auth login"
    gh auth login
  } else {
    Write-Ok "Already authenticated."
  }
}

Write-Ok "Done."

