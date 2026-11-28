# Adds Python 3.12 to your user PATH so 'python' and 'pip' work in new terminals.
# Run:
#   powershell -ExecutionPolicy Bypass -File D:\Projects\Job-Search\job-agent\set-python-path.ps1
# Changes only the current user's PATH (no administrator rights needed). Safe to run again.

$ErrorActionPreference = 'Stop'

$pythonDir = @(
    "$env:LOCALAPPDATA\Programs\Python\Python312",
    "$env:ProgramFiles\Python312"
) | Where-Object { Test-Path -LiteralPath "$_\python.exe" } | Select-Object -First 1

if (-not $pythonDir) { throw "Python 3.12 not found. Run setup.ps1 first." }

$wanted = @($pythonDir, "$pythonDir\Scripts")

# Read and write the registry directly, so entries such as %USERPROFILE% are not expanded.
$key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment', $true)
$old = [string]$key.GetValue('Path', '', 'DoNotExpandEnvironmentNames')

$others = $old -split ';' | Where-Object { $_ -and ($wanted -notcontains $_.TrimEnd('\')) }

# Python goes first, ahead of the Microsoft Store shortcut in WindowsApps.
$new = (@($wanted) + @($others)) -join ';'

if ($new -eq $old) {
    Write-Host "PATH is already set. Nothing changed."
} else {
    $backup = Join-Path $env:USERPROFILE ("path-backup-{0:yyyyMMdd-HHmmss}.txt" -f (Get-Date))
    Set-Content -LiteralPath $backup -Value $old -Encoding UTF8
    $key.SetValue('Path', $new, 'ExpandString')

    # Tell Windows the environment changed, so new terminals pick it up.
    [Environment]::SetEnvironmentVariable('PathRefresh', '1', 'User')
    [Environment]::SetEnvironmentVariable('PathRefresh', $null, 'User')

    Write-Host "Added to your user PATH:" -ForegroundColor Green
    $wanted | ForEach-Object { Write-Host "  $_" }
    Write-Host "Previous PATH saved to $backup"
}
$key.Close()

Write-Host "`nClose all terminals (restart VS Code too), open a new one, then check:"
Write-Host "  python --version"
Write-Host "  pip --version"
