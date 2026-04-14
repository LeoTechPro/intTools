@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%mcp-firefox-devtools.cmd" --capability assess-firefox-client --binding-origin codex/bin/mcp-firefox-assess-client.cmd --profile-key assess-client-diagnostics --start-url http://127.0.0.1:8081/ %*
exit /b %ERRORLEVEL%
