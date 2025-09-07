Param(
    [string]$Tag = 'v0.1.0',
    [string]$Title = 'Baseline Accessibility Build',
    [string]$NotesPath = 'RELEASE_NOTES.md',
    [switch]$Draft
)

$ErrorActionPreference = 'Stop'

Write-Host "[release] Preparing GitHub release '$Tag' ($Title)" -ForegroundColor Cyan

if (-not (Test-Path $NotesPath)) {
    Write-Error "Notes file not found: $NotesPath"; exit 1
}

function Ensure-Tag {
    param([string]$T)
    $existing = git tag --list $T
    if (-not $existing) {
        Write-Host "[release] Creating tag $T" -ForegroundColor DarkGray
        git tag -a $T -m $Title
        git push origin $T
    } else {
        Write-Host "[release] Using existing tag $T" -ForegroundColor DarkGray
    }
}

function Ensure-GH {
    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if (-not $gh) {
        Write-Error "GitHub CLI ('gh') not found. Install from https://cli.github.com and authenticate with 'gh auth login'."; exit 1
    }
}

Ensure-Tag -T $Tag
Ensure-GH

$args = @('release','create', $Tag, '-t', $Title, '-F', $NotesPath)
if ($Draft) { $args += '-d' }

Write-Host "[release] gh $($args -join ' ')" -ForegroundColor DarkGray
gh @args

Write-Host "[release] Draft release created for tag $Tag" -ForegroundColor Green

