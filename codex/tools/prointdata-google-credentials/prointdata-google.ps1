[CmdletBinding()]
param(
    [Parameter(ValueFromPipeline = $true)]
    [string]$InputObject,

    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

begin {
    $ErrorActionPreference = 'Stop'
    $python = Get-Command python -ErrorAction Stop
    $stdinBuffer = [System.Text.StringBuilder]::new()
}

process {
    if ($PSBoundParameters.ContainsKey('InputObject')) {
        [void]$stdinBuffer.AppendLine($InputObject)
    }
}

end {
    if ($stdinBuffer.Length -gt 0) {
        $stdinBuffer.ToString() |
            & $python.Source (Join-Path $PSScriptRoot 'prointdata_google.py') @CliArgs
    } else {
        & $python.Source (Join-Path $PSScriptRoot 'prointdata_google.py') @CliArgs
    }
    exit $LASTEXITCODE
}
