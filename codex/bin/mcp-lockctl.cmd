@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
python "%SCRIPT_DIR%mcp-lockctl.py"
exit /b %ERRORLEVEL%
