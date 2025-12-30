import subprocess
import time
import os
import sys
import argparse
import requests
import signal

# Configuration
N8N_PORT = 5678
N8N_CMD = ["npm", "start"]
MCP_CMD = ["python", "n8n_mcp_server.py"] # Assuming using the python one per roadmap preferences, or node one? The batch file used node.
# Let's stick to Node MCP for now as that's what was working, or switch to Python MCP if that's the goal?
# The user request mentioned "bridge.py" and "n8n_mcp_server.py" in the README diff, but the batch used @leonardsellem/n8n-mcp-server (Node).
# The README diff *also* mentioned "curl-mcp.mjs" (Node).
# The Roadmap mentions "Direct Service Control".
# Let's support both or pick one. The `start-all.bat` used: `npx -y @leonardsellem/n8n-mcp-server`.
# The `curl-mcp.mjs` is the new thing *I* created.
# I will make this script manage `n8n` and optionally the `curl-mcp` or `n8n-mcp`.
# Let's default to starting n8n and the curl bridge since that's my new architecture.

MCP_CMD_NODE = ["node", "curl-mcp.mjs"]

def is_port_open(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def start_process(cmd, cwd, log_file):
    print(f"Starting {' '.join(cmd)}...")
    with open(log_file, "a") as f:
        return subprocess.Popen(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NEW_CONSOLE)

def stop_process(name):
    # This is tricky on Windows without PID files.
    # For now, we might just rely on the user closing the window or use taskkill if we know the PID.
    # A robust way is to use `psutil` if available, or just tell the user.
    # Let's try to implement a basic PID file mechanism.
    pid_file = f"{name}.pid"
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
            print(f"Stopping {name} (PID {pid})...")
            os.kill(pid, signal.SIGTERM)
            os.remove(pid_file)
        except Exception as e:
            print(f"Failed to stop {name}: {e}")
            # Fallback to taskkill by name? Dangerous.
    else:
        print(f"No PID file for {name}. Is it running?")

def start_services():
    cwd = os.getcwd()
    
    # Start n8n
    if not is_port_open(N8N_PORT):
        p_n8n = start_process(N8N_CMD, cwd, "n8n.log")
        with open("n8n.pid", "w") as f:
            f.write(str(p_n8n.pid))
        print(f"n8n started (PID {p_n8n.pid}). Waiting for health check...")
        
        # Wait for health
        retries = 30
        while retries > 0:
            try:
                requests.get(f"http://localhost:{N8N_PORT}/healthz", timeout=1)
                print("n8n is UP!")
                break
            except:
                time.sleep(1)
                retries -= 1
        else:
            print("Warning: n8n did not respond to health check in time.")
    else:
        print(f"n8n is already running on port {N8N_PORT}.")

    # Start MCP / Curl Bridge
    # For now, let's just log it.
    print("Starting Curl Bridge MCP...")
    p_mcp = start_process(MCP_CMD_NODE, cwd, "mcp.log")
    with open("mcp.pid", "w") as f:
        f.write(str(p_mcp.pid))
    print(f"Curl Bridge started (PID {p_mcp.pid}).")

def stop_services():
    stop_process("mcp")
    stop_process("n8n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop", "restart"], help="Action to perform")
    args = parser.parse_args()

    if args.action == "start":
        start_services()
    elif args.action == "stop":
        stop_services()
    elif args.action == "restart":
        stop_services()
        time.sleep(2)
        start_services()

if __name__ == "__main__":
    main()
