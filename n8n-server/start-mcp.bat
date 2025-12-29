@echo off
set /p N8N_API_KEY="Enter your n8n API Key: "
if "%N8N_API_KEY%"=="" goto error

set N8N_API_URL=http://localhost:5678/api/v1

echo Starting n8n MCP Server...
npx -y @leonardsellem/n8n-mcp-server
goto end

:error
echo API Key is required!
pause

:end
