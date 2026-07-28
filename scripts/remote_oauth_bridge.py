#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
SCRIPT_PATH = ROOT / "scripts/auto_oauth_arbitrary.py"

def main():
    print("=== Remote OAuth Bridge ===")
    print("Please paste the Google OAuth URL from your local terminal/phone:")
    
    try:
        auth_url = input("\nURL: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return
        
    if not auth_url:
        print("ERROR: URL cannot be empty.")
        return
        
    print("\nProcessing flow on YOGA's graphical Chrome session...")
    print("Bypassing account chooser, warning screen, and scope checkboxes...")
    
    # Run the arbitrary OAuth clicker script
    res = subprocess.run(
        ["python3", str(SCRIPT_PATH), auth_url],
        capture_output=True,
        text=True
    )
    
    # Parse stdout for the RESULT_REDIRECT_URL
    redirect_url = None
    for line in res.stdout.splitlines():
        if line.startswith("RESULT_REDIRECT_URL:"):
            redirect_url = line.split("RESULT_REDIRECT_URL:", 1)[1].strip()
            break
            
    if redirect_url:
        print("\n" + "="*80)
        print("SUCCESS! Copy the URL below and paste it/open it in your Termux browser:")
        print("="*80)
        print(f"\n{redirect_url}\n")
        print("="*80)
    else:
        print("\nERROR: Failed to capture redirect URL.")
        print("Debugging output below:")
        print(res.stdout)
        print(res.stderr)

if __name__ == "__main__":
    main()
