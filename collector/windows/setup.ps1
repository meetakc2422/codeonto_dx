# One-time setup of the live collector on a Windows server. Run from the collector folder:
#     powershell -ExecutionPolicy Bypass -File windows\setup.ps1
# Creates .venv, installs the packages and Playwright's Chromium, and starts .env from .env.example.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating .venv ..."
    py -3 -m venv .venv
}
.\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
.\.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
.\.venv\Scripts\python.exe -m playwright install chromium

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example: fill in the database URL, GOOGLE_TOKEN_KEY, login emails and IMAP passwords."
}
New-Item -ItemType Directory -Force -Path "logs", "sessions" | Out-Null

Write-Host ""
Write-Host "Done. Check the configuration without calling any platform:"
Write-Host "    .venv\Scripts\python run.py all session --check"
Write-Host "Then register the scheduled jobs:"
Write-Host "    powershell -ExecutionPolicy Bypass -File windows\register_tasks.ps1"
