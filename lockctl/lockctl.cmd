@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "SCRIPT=%SCRIPT_DIR%lockctl.py"
if not "%PYTHON%"=="" (
  "%PYTHON%" "%SCRIPT%" %*
) else (
  python "%SCRIPT%" %*
)
exit /b %ERRORLEVEL%
