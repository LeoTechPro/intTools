[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$payload = @{
    ok = $false
    error_code = "UNSUPPORTED_PLATFORM"
    error = "openclaw/ops/install is linux-only; use --skip-openclaw on Windows"
} | ConvertTo-Json -Compress

[Console]::Error.WriteLine($payload)
exit 1
