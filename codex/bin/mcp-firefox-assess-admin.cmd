@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%mcp-firefox-devtools.cmd" -ProfileKey assess-specialist-admin -StartUrl http://127.0.0.1:8080/v2/ %*
exit /b %ERRORLEVEL%
