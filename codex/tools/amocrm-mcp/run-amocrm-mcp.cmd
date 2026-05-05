@echo off
setlocal

set "AMOCRM_MCP_ROOT=%~dp0"
set "AMOCRM_MCP_DEPS=%AMOCRM_MCP_ROOT%.deps"

if exist "%AMOCRM_MCP_ROOT%..\..\..\.runtime\amocrm-mcp\.deps" (
  set "AMOCRM_MCP_DEPS=%AMOCRM_MCP_ROOT%..\..\..\.runtime\amocrm-mcp\.deps"
)

set "PYTHONPATH=%AMOCRM_MCP_DEPS%;%AMOCRM_MCP_ROOT%;%PYTHONPATH%"

python -m amocrm_mcp
