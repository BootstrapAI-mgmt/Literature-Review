@echo off
cd /d "%~dp0"

echo Setting up environment...
set /p N8N_API_KEY="Enter your n8n API Key: "
if "%N8N_API_KEY%"=="" goto error
set N8N_API_URL=http://localhost:5678/api/v1

echo Importing workflows...
call npx n8n import:workflow "Doc Chain - Trigger.json"
call npx n8n import:workflow "Doc Chain - Distributor.json"
call npx n8n import:workflow "Doc Chain - Agent.json"
call npx n8n import:workflow "Doc Chain - Errors.json"
call npx n8n import:workflow "Doc Chain - Staleness.json"
call npx n8n import:workflow "Doc Chain - State Reconciliation.json"

echo Starting n8n server in background...
start /B npm start > n8n.log 2>&1

echo Waiting for n8n to initialize (10s)...
timeout /t 10 /nobreak >nul

echo Starting MCP server in background...
start /B npx -y @leonardsellem/n8n-mcp-server > mcp.log 2>&1

echo.
echo Services started!
echo - n8n: http://localhost:5678
echo - Logs: n8n.log, mcp.log
goto end

:error
echo API Key is required!
pause

:end
