@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%..\..\codex\bin\mcp-lockctl.cmd"
exit /b %ERRORLEVEL%
