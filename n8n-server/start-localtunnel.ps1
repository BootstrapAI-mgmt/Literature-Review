
Write-Host " Starting localtunnel (port 5678)..." -ForegroundColor Cyan

$logFile = "$PWD\localtunnel.log"
# Use cmd /c wrapper with npx -y
$process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npx -y localtunnel --port 5678 > ""$logFile"" 2>&1" -PassThru -NoNewWindow

Write-Host " localtunnel started with PID $($process.Id)."
Write-Host " Log file: $logFile"
Write-Host " Waiting for URL..."

$maxRetries = 30
$found = $false

for ($i = 0; $i -lt $maxRetries; $i++) {
    Start-Sleep -Seconds 2
    if (Test-Path $logFile) {
        $content = Get-Content $logFile
        $urlLine = $content | Where-Object { $_ -match "your url is: (https://.*)" }
        if ($urlLine) {
            $url = $matches[1]
            Write-Host " "
            Write-Host "✅ TUNNEL URL: $url" -ForegroundColor Green
            
            # Save to .env
            # Append or Replace N8N_TUNNEL_URL
            $envFile = ".env"
            if (Test-Path $envFile) {
                $envContent = Get-Content $envFile
                $newContent = $envContent | Where-Object { -not ($_ -match "N8N_TUNNEL_URL=") }
                $newContent += "N8N_TUNNEL_URL=$url"
                $newContent | Set-Content $envFile
            }
            else {
                "N8N_TUNNEL_URL=$url" | Set-Content $envFile
            }
            Write-Host " Saved to .env"
            
            $found = $true
            break
        }
    }
    Write-Host -NoNewline "."
}

if (-not $found) {
    Write-Host "`nTimeout waiting for URL. Log tail:" -ForegroundColor Red
    if (Test-Path $logFile) {
        Get-Content $logFile -Tail 10
    }
}
