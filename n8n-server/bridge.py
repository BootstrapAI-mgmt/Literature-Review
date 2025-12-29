import os
import sys
import json
import requests
import argparse
import time

# Configuration
# Tries to load from environment or defaults (matches start-all.bat)
API_URL = os.environ.get("N8N_API_URL", "http://localhost:5678/api/v1")
API_KEY = os.environ.get("N8N_API_KEY")

def get_headers():
    if not API_KEY:
        print("Error: N8N_API_KEY environment variable is not set.")
        print("Please set it or run this script from a session where it is initialized.")
        sys.exit(1)
    return {
        "X-N8N-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }

def check_health(wait=False, timeout=30):
    """
    Checks if the n8n server is reachable.
    If wait=True, loops until connected or timeout.
    """
    start_time = time.time()
    while True:
        try:
            # We can use /users or just /workflows to test auth and connectivity
            response = requests.get(f"{API_URL}/workflows", headers=get_headers(), params={"limit": 1})
            if response.status_code == 200:
                return True
            else:
                if not wait:
                    print(f"Server reachable but returned {response.status_code}: {response.text}")
                    return False
        except requests.exceptions.ConnectionError:
            if not wait:
                print("Server unreachable (ConnectionError). Is n8n running?")
                return False
        
        if not wait or (time.time() - start_time > timeout):
            break
        
        time.sleep(1)
        print(".", end="", flush=True)
    
    print(" Timeout reached.")
    return False

def list_workflows(args):
    try:
        response = requests.get(f"{API_URL}/workflows", headers=get_headers())
        response.raise_for_status()
        workflows = response.json().get("data", [])
        
        print(f"{'ID':<25} | {'Active':<8} | {'Name'}")
        print("-" * 60)
        for wf in workflows:
            print(f"{wf['id']:<25} | {str(wf['active']):<8} | {wf['name']}")
            
    except Exception as e:
        print(f"Error listing workflows: {e}")

def get_workflow(args):
    try:
        response = requests.get(f"{API_URL}/workflows/{args.id}", headers=get_headers())
        response.raise_for_status()
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error getting workflow: {e}")

def activate_workflow(args):
    try:
        url = f"{API_URL}/workflows/{args.id}/activate"
        response = requests.post(url, headers=get_headers())
        # Note: API might use PATCH /workflows/{id} with {"active": true} depending on version
        # Let's try the standard PATCH method which is more robust for modern n8n
        if response.status_code == 404:
             url = f"{API_URL}/workflows/{args.id}"
             response = requests.patch(url, headers=get_headers(), json={"active": True})
        
        response.raise_for_status()
        print(f"Workflow {args.id} activated.")
    except Exception as e:
        print(f"Error activating workflow: {e}")

def deactivate_workflow(args):
    try:
        url = f"{API_URL}/workflows/{args.id}"
        response = requests.patch(url, headers=get_headers(), json={"active": False})
        response.raise_for_status()
        print(f"Workflow {args.id} deactivated.")
    except Exception as e:
        print(f"Error deactivating workflow: {e}")

def main():
    parser = argparse.ArgumentParser(description="n8n Bridge Script for Antigravity Agents")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Health command
    health_parser = subparsers.add_parser("health", help="Check server health")
    health_parser.add_argument("--wait", action="store_true", help="Wait for server to become ready")

    # List command
    subparsers.add_parser("list", help="List all workflows")

    # Get command
    get_parser = subparsers.add_parser("get", help="Get workflow details")
    get_parser.add_argument("id", help="Workflow ID")

    # Activate command
    activate_parser = subparsers.add_parser("activate", help="Activate a workflow")
    activate_parser.add_argument("id", help="Workflow ID")

    # Deactivate command
    deactivate_parser = subparsers.add_parser("deactivate", help="Deactivate a workflow")
    deactivate_parser.add_argument("id", help="Workflow ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Check health before proceeding (optional but good practice)
    # For 'health' command, we let the function handle it. For others, we assume basic connectivity checking is implicitly done by requests,
    # but strictly speaking, checking first is safer if we want to "pause logic".
    if args.command == "health":
        if check_health(wait=args.wait):
            print("Status: OK")
        else:
            print("Status: Error")
            sys.exit(1)
    elif args.command == "list":
        list_workflows(args)
    elif args.command == "get":
        get_workflow(args)
    elif args.command == "activate":
        activate_workflow(args)
    elif args.command == "deactivate":
        deactivate_workflow(args)

if __name__ == "__main__":
    main()
