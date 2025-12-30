
Write-Host " Stopping any existing n8n/node processes..." -ForegroundColor Yellow
Stop-Process -Name "node" -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 1

Write-Host " Starting n8n with --tunnel (using cmd wrapper)..." -ForegroundColor Green

$logFile = "$PWD\n8n-tunnel.log"
# Use cmd /c to handle the redirection and npx execution reliably
$process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npx -y n8n start --tunnel > ""$logFile"" 2>&1" -PassThru -NoNewWindow

Write-Host " n8n started with PID $($process.Id)."
Write-Host " Log file: $logFile"
Write-Host " Waiting for Tunnel URL..."

$maxRetries = 60
$found = $false

for ($i = 0; $i -lt $maxRetries; $i++) {
    Start-Sleep -Seconds 2
    if (Test-Path $logFile) {
        $content = Get-Content $logFile
        $tunnelUrlLine = $content | Where-Object { $_ -match "Tunnel URL:" }
        if ($tunnelUrlLine) {
            Write-Host " "
            Write-Host "✅ FOUND: $tunnelUrlLine" -ForegroundColor Cyan
            
            # Extract just the URL part if possible for variable use
            if ($tunnelUrlLine -match "Tunnel URL: (http.*)") {
                $url = $matches[1]
                # Write to .env for other tools to pick up
                Set-Content ".env" "N8N_API_URL=$url/api/v1`r`nN8N_TUNNEL_URL=$url"
                Write-Host "Saved to .env: N8N_TUNNEL_URL=$url"
            }
            
            $found = $true
            break
        }
    }
    Write-Host -NoNewline "."
}

if (-not $found) {
    Write-Host "`nTimeout waiting for Tunnel URL. Logging tail:" -ForegroundColor Red
    if (Test-Path $logFile) {
        Get-Content $logFile -Tail 10
    }
}
