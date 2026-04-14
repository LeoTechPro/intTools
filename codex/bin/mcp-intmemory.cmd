@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
python "%SCRIPT_DIR%mcp-intmemory.py"
exit /b %ERRORLEVEL%
