@echo off
setlocal

set "TILDA_MCP_ROOT=%~dp0"
set "TILDA_MCP_DEPS=%TILDA_MCP_ROOT%.deps"

if exist "%TILDA_MCP_ROOT%..\..\..\.runtime\tilda-mcp\.deps" (
  set "TILDA_MCP_DEPS=%TILDA_MCP_ROOT%..\..\..\.runtime\tilda-mcp\.deps"
)

if not exist "%TILDA_MCP_DEPS%\fastmcp" if exist "%TILDA_MCP_ROOT%..\..\..\.runtime\amocrm-mcp\.deps" (
  set "TILDA_MCP_DEPS=%TILDA_MCP_ROOT%..\..\..\.runtime\amocrm-mcp\.deps"
)

set "PYTHONPATH=%TILDA_MCP_DEPS%;%TILDA_MCP_ROOT%;%PYTHONPATH%"

python -m tilda_mcp.server