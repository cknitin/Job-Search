# Installs Python 3.12 and everything job-agent needs, then runs the offline demo.
# Run from any terminal:
#   powershell -ExecutionPolicy Bypass -File D:\Projects\Job-Search\job-agent\setup.ps1
# Safe to run again: finished steps are skipped or simply re-checked.

# 'Continue', not 'Stop': Windows PowerShell can treat harmless messages that pip and others
# write to the error stream as fatal. Failures are caught by exit code (Assert-Success).
$ErrorActionPreference = 'Continue'
Set-Location -LiteralPath $PSScriptRoot -ErrorAction Stop

function Find-Python312 {
    # Look in the install folders directly, so a new terminal is not needed after installing.
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:ProgramFiles\Python312\python.exe"
    )
    $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}

function Assert-Success([string]$Step) {
    # Native programs do not stop the script on failure, so check the exit code.
    if ($LASTEXITCODE -ne 0) { throw "$Step failed (exit code $LASTEXITCODE). See the messages above." }
}

Write-Host "`n[1/5] Python 3.12" -ForegroundColor Cyan
$python = Find-Python312
if (-not $python) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget not found. Install Python 3.12 from https://www.python.org/downloads/windows/ and run this script again."
    }
    winget install -e --id Python.Python.3.12 --source winget --accept-source-agreements --accept-package-agreements
    Assert-Success "Python install"
    $python = Find-Python312
    if (-not $python) { throw "Python installed but python.exe was not found. Open a new terminal and run this script again." }
}
Write-Host "Using $python"

Write-Host "`n[2/5] Virtual environment (.venv)" -ForegroundColor Cyan
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $python -m venv .venv
    Assert-Success "Creating the virtual environment"
}

Write-Host "`n[3/5] Python packages" -ForegroundColor Cyan
& $venvPython -m pip install -r requirements.txt
Assert-Success "Package install"

Write-Host "`n[4/5] Chromium browser for Playwright" -ForegroundColor Cyan
& $venvPython -m playwright install chromium
Assert-Success "Chromium install"

Write-Host "`n[5/5] Offline demo (no API key needed)" -ForegroundColor Cyan
& $venvPython run.py all --demo
Assert-Success "Demo run"

Write-Host "`nSetup complete." -ForegroundColor Green
Write-Host "To use the agent in a new Command Prompt:"
Write-Host "  cd /d $PSScriptRoot"
Write-Host "  .venv\Scripts\activate"
Write-Host "  set ANTHROPIC_API_KEY=your-key-here"
Write-Host "  python run.py hunt"
