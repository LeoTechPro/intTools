@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%mcp-firefox-devtools.cmd" --capability assess-firefox-specialist-restricted --binding-origin codex/bin/mcp-firefox-assess-specialist-restricted.cmd --profile-key assess-specialist-restricted --start-url http://127.0.0.1:8080/v2/ %*
exit /b %ERRORLEVEL%
