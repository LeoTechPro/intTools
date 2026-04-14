@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%mcp-firefox-devtools.cmd" --capability assess-firefox-specialist-v1 --binding-origin codex/bin/mcp-firefox-assess-specialist-v1.cmd --profile-key assess-specialist-v1 --start-url http://127.0.0.1:8080/ %*
exit /b %ERRORLEVEL%
