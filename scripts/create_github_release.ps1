<# scripts/create_github_release.ps1
   Create a GitHub release using gh.
   Examples:
     .\scripts\create_github_release.ps1 -Tag v0.1.0 -Title "Baseline Accessibility Build" -Draft
     .\scripts\create_github_release.ps1 -Tag v0.1.1 -Title "Auto VAD + Wake" -NotesFile docs/release-notes-v0.1.1.md -Assets "dist\*.zip","logs\*.txt"
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Tag,
  [Parameter(Mandatory=$true)][string]$Title,
  [string]$Notes,
  [string]$NotesFile,
  [string[]]$Assets = @(),
  [switch]$Draft,
  [switch]$GenerateNotes
)

function Write-Info($msg){ Write-Host $msg -ForegroundColor Cyan }
function Write-Ok($msg){ Write-Host $msg -ForegroundColor Green }
function Write-Err($msg){ Write-Host $msg -ForegroundColor Red }

# 1) gh presence
try { gh --version | Out-Null } catch {
  Write-Err "GitHub CLI (gh) is not installed. Run: .\scripts\install_gh.ps1"
  exit 1
}

# 2) auth status
Write-Info "Checking GitHub auth..."
gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Err "You are not authenticated. Run: gh auth login"
  exit 1
}

# 3) Build args
$flags = @("release","create",$Tag,"--title",$Title)
if ($Draft) { $flags += "--draft" }
if ($GenerateNotes) { $flags += "--generate-notes" }

# Notes precedence: NotesFile > Notes > default
if ($NotesFile) {
  if (-not (Test-Path $NotesFile)) {
    Write-Err "Notes file not found: $NotesFile"
    exit 1
  }
  $flags += @("--notes-file",$NotesFile)
} elseif ($Notes) {
  $flags += @("--notes",$Notes)
} elseif (-not $GenerateNotes) {
  # sensible default notes
  $default = @"
**Release: $Title ($Tag)**

## What's New
- Hands-free Auto VAD with wake word "agent"
- Audible beeps (start/stop)
- NVDA-friendly status line
- Repeat-last and logging to logs/agent.log
- Voice Command Catalog in docs/voice-commands.md

## Setup
- Start agent: .\scripts\start_agent.ps1
- Status: .\scripts\show_status.ps1
- Sanity: .\scripts\sanity_agent.ps1 -Mode auto -NoTTS
"@
  $flags += @("--notes",$default)
}

# 4) Expand assets (globs)
$expanded = @()
foreach ($pattern in $Assets) {
  $files = Get-ChildItem -Path $pattern -File -ErrorAction SilentlyContinue
  foreach ($f in $files) { $expanded += $f.FullName }
}
if ($expanded.Count -gt 0) { $flags += $expanded }

# 5) Create or update
Write-Info "Creating release: $Tag"
$env:GH_PAGER="cat"
gh @flags
if ($LASTEXITCODE -eq 0) {
  Write-Ok "Release created."
} else {
  Write-Err "Failed to create release (gh exit $LASTEXITCODE)."
  exit $LASTEXITCODE
}

