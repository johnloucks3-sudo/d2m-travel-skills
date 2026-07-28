#!/usr/bin/env python3
import sys
import time
import subprocess
from pathlib import Path

# Config
PHONE_IP = "100.75.104.71"
PHONE_PORT = "8022"
PHONE_USER = "u0_a588"
IDENTITY_KEY = "/home/john/.ssh/id_ed25519"

ROOT = Path("/home/john/Thunderbird")
SCRIPT_PATH = ROOT / "scripts/auto_oauth_arbitrary.py"

def run_ssh(cmd):
    """Run an SSH command on the phone."""
    res = subprocess.run([
        "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
        "-p", PHONE_PORT, "-i", IDENTITY_KEY,
        f"{PHONE_USER}@{PHONE_IP}", cmd
    ], capture_output=True, text=True)
    return res

def main():
    print("=== Automated Phone OAuth Login Script ===")
    print(f"Target Phone: {PHONE_USER}@{PHONE_IP}:{PHONE_PORT}")
    
    # 1. Test connection to phone
    print("Testing SSH connection to phone...")
    test_res = run_ssh("echo CONNECTED")
    if test_res.returncode != 0 or "CONNECTED" not in test_res.stdout:
        print("\nERROR: Cannot connect to the phone via SSH.")
        print(f"Exit Code: {test_res.returncode}")
        print(f"Stderr: {test_res.stderr.strip()}")
        print("\nFix: Please run 'sshd' in Termux on your phone to start the SSH server.")
        sys.exit(1)
        
    print("SSH connection verified!")
    
    # 2. Read URL from phone
    print("Retrieving the OAuth URL from phone...")
    url_res = run_ssh("cat url.txt")
    if url_res.returncode != 0 or not url_res.stdout.strip():
        print("\nERROR: Could not find 'url.txt' on the phone or it is empty.")
        print("Please run this command first in your phone's Termux Session 1:")
        print("   agy models 2>&1 | tee url.txt")
        sys.exit(1)
        
    auth_url = url_res.stdout.strip().splitlines()[-1] # Get last line just in case
    print(f"Retrieved OAuth URL: {auth_url[:60]}...")
    
    # 3. Process URL on YOGA
    print("\nRunning browser automation on YOGA...")
    auth_res = subprocess.run(
        ["python3", str(SCRIPT_PATH), auth_url],
        capture_output=True,
        text=True
    )
    
    redirect_url = None
    for line in auth_res.stdout.splitlines():
        if line.startswith("RESULT_REDIRECT_URL:"):
            redirect_url = line.split("RESULT_REDIRECT_URL:", 1)[1].strip()
            break
            
    if not redirect_url:
        print("\nERROR: Failed to capture the redirect URL from YOGA's browser.")
        print("Debugger Output:")
        print(auth_res.stdout)
        print(auth_res.stderr)
        sys.exit(1)
        
    print(f"Redirect URL Captured: {redirect_url[:60]}...")
    
    # 4. Push redirect back to phone via curl
    print("\nPushing redirect callback back to phone...")
    push_res = run_ssh(f"curl -s '{redirect_url}'")
    if push_res.returncode == 0:
        print("\n" + "="*60)
        print("SUCCESS! The OAuth code was fed back to your phone's agy.")
        print("Check Termux Session 1 - it should now be logged in!")
        print("="*60)
    else:
        print(f"\nWarning: push curl returned exit code {push_res.returncode}")
        print(f"Stderr: {push_res.stderr}")
        print("Please manually curl the redirect URL in Termux:")
        print(f"curl '{redirect_url}'")

if __name__ == "__main__":
    main()
