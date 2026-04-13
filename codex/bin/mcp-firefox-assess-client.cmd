@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%mcp-firefox-devtools.cmd" -ProfileKey assess-client-diagnostics -StartUrl http://127.0.0.1:8081/ %*
exit /b %ERRORLEVEL%
