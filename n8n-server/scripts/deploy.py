import argparse
import subprocess
import sys
import os
from pathlib import Path

# Paths
SCRIPTS_DIR = Path(__file__).parent
REPO_ROOT = SCRIPTS_DIR.parent

def run_command(cmd, cwd=None, exit_on_fail=True):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, text=True)
    if result.returncode != 0:
        print(f"Error: Command failed with exit code {result.returncode}")
        if exit_on_fail:
            sys.exit(result.returncode)
    return result.returncode

def git_pull():
    print("--- 1. Pulling latest changes ---")
    run_command(["git", "pull"], cwd=REPO_ROOT)

def npm_install():
    print("--- 2. Updating dependencies ---")
    # Check if package.json exists
    if (REPO_ROOT / "package.json").exists():
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        run_command([npm_cmd, "install"], cwd=REPO_ROOT)
    else:
        print("No package.json found, skipping.")

def import_workflows():
    print("--- 3. Importing workflows to n8n ---")
    sync_script = SCRIPTS_DIR / "sync_workflows.py"
    run_command(["python", str(sync_script), "--import"], cwd=SCRIPTS_DIR)

def restart_server():
    print("--- 4. Restarting n8n server ---")
    manage_script = SCRIPTS_DIR / "manage_services.py"
    run_command(["python", str(manage_script), "restart"], cwd=SCRIPTS_DIR)

def main():
    parser = argparse.ArgumentParser(description="Deploy changes to Local n8n")
    parser.add_argument("--no-pull", action="store_true", help="Skip git pull")
    parser.add_argument("--restart", action="store_true", help="Restart n8n after import")
    
    args = parser.parse_args()
    
    if not args.no_pull:
        git_pull()
    
    npm_install()
    import_workflows()
    
    if args.restart:
        restart_server()
        
    print("\n✅ Deployment Complete!")

if __name__ == "__main__":
    main()
