@echo off
setlocal
where bash >nul 2>nul
if %ERRORLEVEL% neq 0 (
  echo mcp-github-from-gh.cmd: bash not found in PATH 1>&2
  exit /b 1
)
set "SCRIPT_DIR=%~dp0"
bash "%SCRIPT_DIR%mcp-github-from-gh.sh" %*
exit /b %ERRORLEVEL%
