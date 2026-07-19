@echo off
setlocal
set "BITRIX24_MCP_ROOT=%~dp0"
set "PYTHONPATH=%BITRIX24_MCP_ROOT%;%PYTHONPATH%"
python -m bitrix24_mcp %*
