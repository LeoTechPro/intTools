@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python "%SCRIPT_DIR%firefox_mcp_launcher.py" %*
  exit /b %ERRORLEVEL%
)

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 "%SCRIPT_DIR%firefox_mcp_launcher.py" %*
  exit /b %ERRORLEVEL%
)

echo mcp-firefox-devtools: python ^(or py^) not found in PATH 1>&2
exit /b 1
