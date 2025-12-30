
# Local Development Environment Guide

## 🚀 Overview
This guide describes the robust setup for running the n8n automation server locally on Windows, ensuring external connectivity for webhook testing.

---

## 🛠️ Key Scripts
Located in `n8n-server/`:

### 1. `start-n8n-tunnel.ps1` (Deprecated / Native Tunnel)
Attempts to start n8n with the native `--tunnel` flag.
*   **Status**: Known to be flaky or fail silently on some Windows setups.
*   **Use Case**: Quick testing if it works for you.

### 2. `start-localtunnel.ps1` (Recommended)
Uses `localtunnel` (via `npx`) to expose port 5678.
*   **Features**:
    *   Automatically updates `.env` with the new `N8N_TUNNEL_URL`.
    *   Runs non-interactively using `npx -y`.
    *   Robustly handles file redirection and logging.
*   **Usage**:
    ```powershell
    .\n8n-server\start-localtunnel.ps1
    ```

### 3. Startup Sequence (Manual)
If the scripts fail, follow this sequence:
1.  **Stop n8n**: `Stop-Process -Name node -Force`
2.  **Start Tunnel**: `npx -y localtunnel --port 5678` -> Copy URL.
3.  **Start n8n**: `npx n8n start` -> In a separate terminal.
4.  **Update Config**: Set `N8N_TUNNEL_URL` in `.env`.

---

## ⚠️ Known Issues

### Database Locks (`SQLITE_BUSY`)
*   **Symptom**: `n8n import:workflow` fails or API calls hang.
*   **Cause**: Multiple `node.exe` processes (n8n server + CLI commands) fighting for the SQLite database.
*   **Fix**:
    ```powershell
    Stop-Process -Name node -Force
    ```
    Always stop the server before running CLI imports.

### Webhook & Tunneling
*   **Localtunnel Warning**: Accessing the tunnel URL in a browser shows a "Click to Continue" page.
*   **Fix**: Add header `Bypass-Tunnel-Reminder: true` to your webhook requests (or open the URL in a browser once to whitelist your IP).

---

## 🧪 Verification
To verify your environment is ready for e2e testing:
1.  Run `.\n8n-server\start-localtunnel.ps1`.
2.  Wait for "✅ TUNNEL URL".
3.  Run `npx n8n start` in another terminal.
4.  Test connectivity:
    ```powershell
    $url = (Get-Content .env | Select-String "N8N_TUNNEL_URL").ToString().Split('=')[1]
    Invoke-RestMethod -Uri "$url/healthz" -Headers @{"Bypass-Tunnel-Reminder"="true"}
    ```
    Expect `status: ok`.
