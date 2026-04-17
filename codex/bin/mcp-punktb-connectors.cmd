@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
python "%SCRIPT_DIR%mcp-intdata-cli.py" --profile punktb-connectors
exit /b %ERRORLEVEL%
