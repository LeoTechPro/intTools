@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..") do set "INT_ROOT=%%~fI"

if not defined CODEX_HOME set "CODEX_HOME=%USERPROFILE%\.codex"
if not defined CODEX_RUNTIME_ROOT set "CODEX_RUNTIME_ROOT=%INT_ROOT%\.runtime"
if not defined CODEX_SECRETS_ROOT set "CODEX_SECRETS_ROOT=%CODEX_RUNTIME_ROOT%\codex-secrets"
if not defined LEGACY_CODEX_VAR_ROOT set "LEGACY_CODEX_VAR_ROOT=%CODEX_HOME%\var"

set "ENV_NAME=intbrain-agent.env"
call :source_env "%CODEX_SECRETS_ROOT%\%ENV_NAME%" 2>nul
if errorlevel 1 call :source_env "%LEGACY_CODEX_VAR_ROOT%\%ENV_NAME%" 2>nul

if not defined INTBRAIN_AGENT_ID goto missing_env
if not defined INTBRAIN_AGENT_KEY goto missing_env

python "%SCRIPT_DIR%mcp-intbrain.py"
exit /b %ERRORLEVEL%

:source_env
if not exist "%~1" exit /b 1
for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%~1") do (
  if not "%%A"=="" set "%%A=%%B"
)
exit /b 0

:missing_env
>&2 echo INTBRAIN_AGENT_ID/INTBRAIN_AGENT_KEY are not set.
>&2 echo Set them in %CODEX_SECRETS_ROOT%\%ENV_NAME% or export them before starting Codex/OpenClaw.
>&2 echo Legacy fallback: %LEGACY_CODEX_VAR_ROOT%\%ENV_NAME%
exit /b 1
