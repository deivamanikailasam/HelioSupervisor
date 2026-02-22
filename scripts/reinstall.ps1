# Clear pip cache and reinstall from requirements.txt with pinned versions.
# Run from repo root: .\scripts\reinstall.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

$pip = "pip"
if (Test-Path ".\.venv\Scripts\pip.exe") {
    $pip = ".\.venv\Scripts\pip.exe"
}

Write-Host "Purging pip cache..."
& $pip cache purge

Write-Host "Installing from requirements.txt (pinned versions)..."
& $pip install --no-cache-dir -r requirements.txt

Write-Host "Done."
