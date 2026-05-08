@echo off
setlocal

set "GETCOURSE_MCP_ROOT=%~dp0"
set "GETCOURSE_MCP_DEPS=%GETCOURSE_MCP_ROOT%.deps"

if exist "%GETCOURSE_MCP_ROOT%..\..\..\.runtime\getcourse-mcp\.deps" (
  set "GETCOURSE_MCP_DEPS=%GETCOURSE_MCP_ROOT%..\..\..\.runtime\getcourse-mcp\.deps"
)

set "PYTHONPATH=%GETCOURSE_MCP_DEPS%;%GETCOURSE_MCP_ROOT%;%PYTHONPATH%"

python -m getcourse_mcp
