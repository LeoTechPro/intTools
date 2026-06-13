if ($env:PROBE_BIN -and (Test-Path $env:PROBE_BIN)) {
  & $env:PROBE_BIN coord @args
  exit $LASTEXITCODE
}

$probe = "D:\int\probe\client\probe.exe"
if (Test-Path $probe) {
  & $probe coord @args
  exit $LASTEXITCODE
}

$probeClient = "D:\int\probe\client\probe-client.exe"
if (Test-Path $probeClient) {
  & $probeClient coord @args
  exit $LASTEXITCODE
}

probe coord @args
