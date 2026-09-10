Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$source = Join-Path $PSScriptRoot "..\hermes-plugin"
$target = Join-Path $env:USERPROFILE ".hermes\plugins\hermes-desktop-operator"

if (-not (Test-Path -LiteralPath $source)) {
    throw "Hermes plugin source not found: $source"
}

New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -LiteralPath (Join-Path $source "plugin.yaml") -Destination $target -Force
Copy-Item -LiteralPath (Join-Path $source "__init__.py") -Destination $target -Force
Copy-Item -LiteralPath (Join-Path $source "client.py") -Destination $target -Force

Write-Host "Installed Hermes plugin to $target"
Write-Host "Next: add HERMES_OPERATOR_API_TOKEN to $env:USERPROFILE\.hermes\.env"
Write-Host "Then enable hermes-desktop-operator in Hermes Plugins and restart Hermes."

