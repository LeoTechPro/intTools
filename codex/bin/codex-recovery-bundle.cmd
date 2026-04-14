@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python "%SCRIPT_DIR%codex_recovery_bundle.py" --binding-origin codex/bin/codex-recovery-bundle.cmd %*
  exit /b %ERRORLEVEL%
)

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 "%SCRIPT_DIR%codex_recovery_bundle.py" --binding-origin codex/bin/codex-recovery-bundle.cmd %*
  exit /b %ERRORLEVEL%
)

echo codex-recovery-bundle: python ^(or py^) not found in PATH 1>&2
exit /b 1
