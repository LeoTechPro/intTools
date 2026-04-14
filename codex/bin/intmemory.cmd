@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
python "%SCRIPT_DIR%intmemory.py" %*
exit /b %ERRORLEVEL%
