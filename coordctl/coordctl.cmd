@echo off
setlocal
if not "%PROBE_BIN%"=="" (
  "%PROBE_BIN%" coord %*
  exit /b %ERRORLEVEL%
)
if exist "D:\int\probe\client\probe.exe" (
  "D:\int\probe\client\probe.exe" coord %*
  exit /b %ERRORLEVEL%
)
if exist "D:\int\probe\client\probe-client.exe" (
  "D:\int\probe\client\probe-client.exe" coord %*
  exit /b %ERRORLEVEL%
)
probe coord %*
