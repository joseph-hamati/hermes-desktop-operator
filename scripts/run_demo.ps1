Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Virtual environment not found. Run scripts\install_windows.ps1 first."
}

.\.venv\Scripts\python.exe .\examples\notepad_demo.py
