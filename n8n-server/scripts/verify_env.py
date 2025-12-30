import shutil
import subprocess
import sys
import os
import requests
from pathlib import Path

def load_env():
    """Load .env file manually."""
    env_path = Path(".env")
    if not env_path.exists():
        env_path = Path("../.env") # Try parent
    
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, val = line.strip().split("=", 1)
                    if key not in os.environ:
                        os.environ[key] = val

load_env()

def print_result(check_name, status, details=""):
    icon = "✅" if status else "❌"
    print(f"{icon} {check_name:<20} {details}")

def check_command(command, args=[]):
    if not shutil.which(command):
        print_result(command, False, "Not installed / Not in PATH")
        return False
    return True

def check_gh_auth():
    if not check_command("gh"): return False
    
    try:
        # gh auth status outputs to stderr usually
        result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        if result.returncode == 0:
            user = "Unknown"
            # Try to parse user from output
            for line in result.stderr.splitlines():
                if "Logged in to github.com" in line:
                    user = line.split(" as ")[-1].strip()
                    break
            print_result("GitHub Auth", True, f"Logged in as {user}")
            return True
        else:
            print_result("GitHub Auth", False, "Not logged in (run 'gh auth login')")
            return False
    except Exception as e:
        print_result("GitHub Auth", False, str(e))
        return False

def check_n8n_status():
    url = os.environ.get("N8N_API_URL", "http://localhost:5678/api/v1")
    # Clean up URL to get base
    base_url = url.split("/api/")[0]
    health_url = f"{base_url}/healthz"
    
    try:
        response = requests.get(health_url, timeout=2)
        if response.status_code == 200:
            print_result("n8n Server", True, "Running & Reachable")
            return True
        else:
            print_result("n8n Server", False, f"Responded with {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_result("n8n Server", False, "Connection Refused (Is it running?)")
        return False
    except Exception as e:
        print_result("n8n Server", False, str(e))
        return False

def check_env_vars():
    required_vars = [
        "N8N_API_KEY",
        "GITHUB_TOKEN",
        "REPO_OWNER",
        "REPO_NAME",
        "N8N_BASE_URL"
    ]
    
    all_set = True
    for key in required_vars:
        val = os.environ.get(key)
        if val:
            safe_val = val[:4] + "..." if len(val) > 4 else "***"
            print_result(key, True, f"Set ({safe_val})")
        else:
            print_result(key, False, "Not Set")
            all_set = False
    return all_set

def verify_github_token_api():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print_result("GitHub Token API", False, "Token not found in env")
        return False
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        response = requests.get("https://api.github.com/user", headers=headers, timeout=5)
        if response.status_code == 200:
            user_login = response.json().get("login", "Unknown")
            print_result("GitHub Token API", True, f"Valid (User: {user_login})")
            return True
        elif response.status_code == 401:
            print_result("GitHub Token API", False, "Invalid Credentials (401)")
            return False
        else:
            print_result("GitHub Token API", False, f"Failed (Status: {response.status_code})")
            return False
    except Exception as e:
        print_result("GitHub Token API", False, f"Error: {str(e)}")
        return False

def main():
    print("--- Environment Verification ---")
    
    # 1. Python
    print_result("Python", True, sys.version.split()[0])
    
    # 2. GitHub CLI (gh)
    check_gh_auth()
    
    # 3. Environment Variables Presence
    check_env_vars()

    # 4. GitHub Token Validity (API)
    verify_github_token_api()
    
    # 5. n8n Server
    check_n8n_status()
    
    print("--------------------------------")

if __name__ == "__main__":
    main()
