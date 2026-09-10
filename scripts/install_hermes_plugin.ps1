param(
    [switch]$ConfigureToken
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$source = Join-Path $PSScriptRoot "..\hermes-plugin"
$localHermesHome = Join-Path $env:LOCALAPPDATA "hermes"
$legacyHermesHome = Join-Path $env:USERPROFILE ".hermes"
$hermesHome = if (Test-Path -LiteralPath $localHermesHome) {
    $localHermesHome
} else {
    $legacyHermesHome
}
$target = Join-Path $hermesHome "plugins\hermes-desktop-operator"

if (-not (Test-Path -LiteralPath $source)) {
    throw "Hermes plugin source not found: $source"
}

New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -LiteralPath (Join-Path $source "plugin.yaml") -Destination $target -Force
Copy-Item -LiteralPath (Join-Path $source "__init__.py") -Destination $target -Force
Copy-Item -LiteralPath (Join-Path $source "client.py") -Destination $target -Force

Write-Host "Installed Hermes plugin to $target"

if ($ConfigureToken) {
    $operatorEnv = Join-Path $PSScriptRoot "..\.env"
    $hermesEnv = Join-Path $hermesHome ".env"
    $tokenLine = Get-Content -LiteralPath $operatorEnv |
        Where-Object { $_ -match '^HERMES_OPERATOR_API_TOKEN=' } |
        Select-Object -First 1
    if (-not $tokenLine) {
        throw "HERMES_OPERATOR_API_TOKEN was not found in $operatorEnv"
    }

    $existing = if (Test-Path -LiteralPath $hermesEnv) {
        Get-Content -LiteralPath $hermesEnv
    } else {
        @()
    }
    $updated = @($existing | Where-Object {
        $_ -notmatch '^HERMES_OPERATOR_API_TOKEN=' -and
        $_ -notmatch '^HERMES_OPERATOR_URL='
    }) + @($tokenLine, "HERMES_OPERATOR_URL=http://127.0.0.1:8765")
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($hermesEnv, [string[]]$updated, $utf8NoBom)
    Write-Host "Configured the daemon URL and token in $hermesEnv"
} else {
    Write-Host "Next: add HERMES_OPERATOR_API_TOKEN to $hermesHome\.env"
}

Write-Host "Then enable hermes-desktop-operator in Hermes Plugins and restart Hermes."
