@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "PYTHONUTF8=1"

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python "%SCRIPT_DIR%lib\dba.py" %*
  exit /b %ERRORLEVEL%
)

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 "%SCRIPT_DIR%lib\dba.py" %*
  exit /b %ERRORLEVEL%
)

echo dba: python ^(or py^) not found in PATH 1>&2
exit /b 1
