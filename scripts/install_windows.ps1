Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.12+ from https://www.python.org/downloads/windows/."
}

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Edit HERMES_OPERATOR_API_TOKEN before use."
}

Write-Host "Install complete. Activate with: .\.venv\Scripts\Activate.ps1"
