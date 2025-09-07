# Cleanup script for Agent Brain Bootstrap
# Removes redundant files and consolidates documentation

Write-Host "=== Starting Cleanup ===" -ForegroundColor Cyan

# Remove redundant test scripts
$filesToRemove = @(
    "scripts\\test_audio.ps1",
    "scripts\\repair_audio.ps1"
)

foreach ($file in $filesToRemove) {
    $fullPath = Join-Path $PSScriptRoot "..\$file"
    if (Test-Path $fullPath) {
        Remove-Item -Path $fullPath -Force
        Write-Host "Removed: $file" -ForegroundColor Yellow
    }
}

# Clean up temporary files
$tempFiles = @(
    "*.log",
    "*.tmp",
    "*.pyc",
    "__pycache__",
    ".DS_Store",
    "Thumbs.db"
)

Write-Host "`nCleaning up temporary files..." -ForegroundColor Cyan
Get-ChildItem -Path $PSScriptRoot\.. -Include $tempFiles -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue

# Merge READMEs
Write-Host "`nConsolidating README files..." -ForegroundColor Cyan
$mainReadme = Join-Path $PSScriptRoot "..\README.md"
$accessibleReadme = Join-Path $PSScriptRoot "..\README-ACCESSIBLE.md"
$liveReadme = Join-Path $PSScriptRoot "..\README-LIVE.md"

if (Test-Path $accessibleReadme) {
    $accessibleContent = Get-Content $accessibleReadme -Raw
    $mainContent = Get-Content $mainReadme -Raw
    
    # Add accessible content to main README if not already present
    if ($mainContent -notmatch "## Accessible Setup Guide") {
        $mainContent = $mainContent + "`n`n" + $accessibleContent
        Set-Content -Path $mainReadme -Value $mainContent
        Write-Host "Merged README-ACCESSIBLE.md into README.md" -ForegroundColor Green
    }
    
    # Remove the old file
    Remove-Item -Path $accessibleReadme -Force
}

if (Test-Path $liveReadme) {
    $liveContent = Get-Content $liveReadme -Raw
    $mainContent = Get-Content $mainReadme -Raw
    
    # Add live content to main README if not already present
    if ($mainContent -notmatch "## Live Voice Loop") {
        $mainContent = $mainContent + "`n`n" + $liveContent
        Set-Content -Path $mainReadme -Value $mainContent
        Write-Host "Merged README-LIVE.md into README.md" -ForegroundColor Green
    }
    
    # Remove the old file
    Remove-Item -Path $liveReadme -Force
}

Write-Host "`n=== Cleanup Complete ===" -ForegroundColor Green
Write-Host "Review the changes and commit them to version control." -ForegroundColor Cyan
