@echo off
setlocal
where bash >nul 2>nul
if %ERRORLEVEL% neq 0 (
  echo mcp-bitrix24.cmd: bash not found in PATH 1>&2
  exit /b 1
)
set "SCRIPT_DIR=%~dp0"
bash "%SCRIPT_DIR%mcp-bitrix24.sh" %*
exit /b %ERRORLEVEL%
