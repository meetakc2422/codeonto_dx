# One-time setup of the live collector on a Windows server. Run from the collector folder:
#     powershell -ExecutionPolicy Bypass -File windows\setup.ps1
# Creates .venv, installs the packages and Playwright's Chromium, and starts .env from .env.example.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    # the newest Python can be ahead of the packages (Playwright, psycopg wheels): prefer 3.13 / 3.12 when installed
    $ver = @("3.13", "3.12") | Where-Object { py "-$_" -c "pass" 2>$null; $LASTEXITCODE -eq 0 } | Select-Object -First 1
    if (-not $ver) { $ver = "3" }
    Write-Host "Creating .venv with Python $ver ..."
    py "-$ver" -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Couldn't create .venv: install Python 3.12 or 3.13 from python.org (tick 'Add to PATH')." }
}
# native commands don't stop the script on failure by themselves, so check each one
function Step($what, [scriptblock]$cmd) {
    & $cmd
    if ($LASTEXITCODE -ne 0) { throw "$what failed (exit code $LASTEXITCODE). Fix the error above, then run setup.ps1 again." }
}
.\.venv\Scripts\python.exe --version
Step "Upgrading pip" { .\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet }
Step "Installing packages" { .\.venv\Scripts\python.exe -m pip install -r requirements.txt }
Step "Installing the Playwright browser" { .\.venv\Scripts\python.exe -m playwright install chromium }

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example: fill in the database URL, GOOGLE_TOKEN_KEY, login emails and IMAP passwords."
}
New-Item -ItemType Directory -Force -Path "logs", "sessions" | Out-Null

Write-Host ""
Write-Host "Done. Check the configuration without calling any platform:"
Write-Host "    .venv\Scripts\python run.py all session --check"
Write-Host "Then either start single services in their own window (e.g. .venv\Scripts\python run.py worker)"
Write-Host "or register every job in Task Scheduler (only on a machine not already running them):"
Write-Host "    powershell -ExecutionPolicy Bypass -File windows\register_tasks.ps1"
