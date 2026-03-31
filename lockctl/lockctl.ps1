$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "lockctl.py"
$python = if ($env:PYTHON -and $env:PYTHON.Trim()) { $env:PYTHON } else { "python" }
& $python $script @args
exit $LASTEXITCODE
