import argparse
import requests
import sys
import time
import json
import os
from pathlib import Path

# Load env for verification if needed
def load_env():
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

def test_webhook(url, method="POST", payload=None, timeout=10):
    print(f"Testing Webhook: {url}")
    print(f"Method: {method}")
    if payload:
        print(f"Payload: {json.dumps(payload, indent=2)}")
    
    start_time = time.time()
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=payload, timeout=timeout)
        else:
            response = requests.post(url, json=payload, timeout=timeout)
            
        duration = time.time() - start_time
        print(f"\nResponse Code: {response.status_code}")
        print(f"Time: {duration:.2f}s")
        
        try:
            print("Response Body:")
            print(json.dumps(response.json(), indent=2))
        except:
            print(f"Response Body (Text): {response.text}")
            
        if 200 <= response.status_code < 300:
            print("\n✅ Test Passed")
            return True
        else:
            print("\n❌ Test Failed")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Integration Test for n8n Webhooks")
    parser.add_argument("--url", required=True, help="Webhook URL to test")
    parser.add_argument("--method", default="POST", help="HTTP Method")
    parser.add_argument("--payload", help="JSON payload string or path to JSON file")
    
    args = parser.parse_args()
    
    payload = {}
    if args.payload:
        if os.path.exists(args.payload):
            with open(args.payload, 'r') as f:
                payload = json.load(f)
        else:
            try:
                payload = json.loads(args.payload)
            except:
                print("Error: Payload is neither a file nor valid JSON string")
                sys.exit(1)
    
    success = test_webhook(args.url, args.method, payload)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
