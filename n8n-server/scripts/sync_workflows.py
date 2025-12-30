import argparse
import json
import os
import requests
import sys
from pathlib import Path

# Configuration
API_URL = os.environ.get("N8N_API_URL", "http://localhost:5678/api/v1")
API_KEY = os.environ.get("N8N_API_KEY")
# Relative to scripts/ (e.g. n8n-server/workflows)
WORKFLOWS_DIR = Path(__file__).parent / "../workflows"

def load_env():
    """Load .env file manually."""
    # Check current dir, then parent of script
    candidates = [
        Path(".env"),
        Path(__file__).parent / "../.env",  # If running as script
        Path(__file__).parent / ".env"
    ]
    
    for env_path in candidates:
        if env_path.resolve().exists():
            with open(env_path, "r") as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        key, val = line.strip().split("=", 1)
                        if key not in os.environ:
                            os.environ[key] = val
            break

load_env()
API_URL = os.environ.get("N8N_API_URL", "http://localhost:5678/api/v1")
API_KEY = os.environ.get("N8N_API_KEY")
def get_headers():
    if not API_KEY:
        print("Error: N8N_API_KEY not set. Please set it in your environment or .env file.")
        sys.exit(1)
    return {
        "X-N8N-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }

def fetch_all_workflows():
    """Fetch all workflows from n8n."""
    try:
        response = requests.get(f"{API_URL}/workflows", headers=get_headers())
        response.raise_for_status()
        return response.json().get("data", [])
    except Exception as e:
        print(f"Error fetching workflows: {e}")
        sys.exit(1)

def export_workflows():
    """Download all workflows from n8n and save to JSON files."""
    print("Exporting workflows...")
    workflows = fetch_all_workflows()
    
    if not WORKFLOWS_DIR.exists():
        WORKFLOWS_DIR.mkdir()
    
    for wf in workflows:
        # Fetch full details (the list endpoint might be brief)
        res = requests.get(f"{API_URL}/workflows/{wf['id']}", headers=get_headers())
        full_wf = res.json()
        
        # Sanitize name for filename
        safe_name = "".join([c for c in wf['name'] if c.isalnum() or c in (' ', '-', '_')]).strip()
        filename = WORKFLOWS_DIR / f"{safe_name}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(full_wf, f, indent=2)
        print(f"Saved: {filename}")

def import_workflows():
    """Read JSON files from repo and upsert to n8n."""
    print("Importing workflows...")
    if not WORKFLOWS_DIR.exists():
        print(f"Directory {WORKFLOWS_DIR} does not exist.")
        return

    files = list(WORKFLOWS_DIR.glob("*.json"))
    if not files:
        print("No workflow files found.")
        return

    # To upsert, we ideally need to know the ID. 
    # Strategy: 
    # 1. Read file. 
    # 2. Check if 'id' exists in file. 
    # 3. If yes, try PUT /workflows/{id}. 
    # 4. If 404 or no ID, POST /workflows.
    
    for wf_file in files:
        with open(wf_file, "r", encoding="utf-8") as f:
            try:
                wf_data = json.load(f)
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON: {wf_file}")
                continue
        
        wf_id = wf_data.get("id")
        name = wf_data.get("name", wf_file.stem)
        
        if "id" in wf_data:
            del wf_data["id"]
            
        print(f"Creating workflow '{name}'...")
        # Sanitize payload
        allowed_keys = {"name", "nodes", "connections", "settings"}
        sanitized_data = {k: v for k, v in wf_data.items() if k in allowed_keys}
        
        res = requests.post(f"{API_URL}/workflows", headers=get_headers(), json=sanitized_data)
        if res.status_code == 200:
            new_id = res.json().get("id")
            print(f"  Success (Created id: {new_id})")
        else:
            print(f"  Error {res.status_code}: {res.text}")

def import_workflows():
    """Read JSON files from repo and upsert to n8n."""
    print("Importing workflows...")
    if not WORKFLOWS_DIR.exists():
        print(f"Directory {WORKFLOWS_DIR} does not exist.")
        return

    files = list(WORKFLOWS_DIR.glob("*.json"))
    if not files:
        print("No workflow files found.")
        return
        
    for wf_file in files:
        with open(wf_file, "r", encoding="utf-8") as f:
            try:
                wf_data = json.load(f)
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON: {wf_file}")
                continue
        
        wf_id = wf_data.get("id")
        name = wf_data.get("name", wf_file.stem)
        
        # Sanitize payload for both update and create
        allowed_keys = {"name", "nodes", "connections", "settings"}
        sanitized_data = {k: v for k, v in wf_data.items() if k in allowed_keys}
        
        if wf_id:
            # Try update
            print(f"Updating workflow '{name}' ({wf_id})...")
            res = requests.put(f"{API_URL}/workflows/{wf_id}", headers=get_headers(), json=sanitized_data)
            if res.status_code == 200:
                print("  Success (Updated)")
                continue
            elif res.status_code == 404:
                print("  ID not found, creating new...")
            else:
                print(f"  Error {res.status_code}: {res.text}")
                continue
        
        # Create new if update failed or no ID
        print(f"Creating workflow '{name}'...")
        res = requests.post(f"{API_URL}/workflows", headers=get_headers(), json=sanitized_data)
        if res.status_code == 200:
            new_id = res.json().get("id")
            print(f"  Success (Created id: {new_id})")
        else:
            print(f"  Error {res.status_code}: {res.text}")

def main():
    parser = argparse.ArgumentParser(description="Sync n8n workflows")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--export", action="store_true", help="Export (n8n -> git)")
    group.add_argument("--import", dest="import_flag", action="store_true", help="Import (git -> n8n)")
    
    args = parser.parse_args()
    
    if args.export:
        export_workflows()
    elif args.import_flag:
        import_workflows()

if __name__ == "__main__":
    main()
