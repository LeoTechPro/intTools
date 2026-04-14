@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%mcp-firefox-devtools.cmd" --capability firefox-default --binding-origin codex/bin/mcp-firefox-default.cmd --profile-key firefox-default --start-url http://127.0.0.1:8080/ %*
exit /b %ERRORLEVEL%
