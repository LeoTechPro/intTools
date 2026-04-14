@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "OPEN_SPEC_BIN=%SCRIPT_DIR%..\tools\openspec\node_modules\.bin\openspec"
if not exist "%OPEN_SPEC_BIN%" (
  echo openspec не установлен локально. Запустите: %SCRIPT_DIR%..\tools\install_tools.sh 1>&2
  exit /b 2
)
node "%OPEN_SPEC_BIN%" %*
exit /b %ERRORLEVEL%
