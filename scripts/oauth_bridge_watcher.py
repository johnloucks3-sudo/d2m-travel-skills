#!/usr/bin/env python3
import time
import os
import subprocess
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
AUTH_URL_FILE = ROOT / "auth_url.txt"
REDIRECT_URL_FILE = ROOT / "redirect_url.txt"
SCRIPT_PATH = ROOT / "scripts/auto_oauth_arbitrary.py"

def main():
    print("=== OAuth Bridge Watcher Started ===")
    print(f"Watching for: {AUTH_URL_FILE}")
    print(f"Will output to: {REDIRECT_URL_FILE}")
    
    # Clean up any stale files
    if AUTH_URL_FILE.exists():
        os.remove(AUTH_URL_FILE)
    if REDIRECT_URL_FILE.exists():
        os.remove(REDIRECT_URL_FILE)
        
    while True:
        try:
            if AUTH_URL_FILE.exists() and AUTH_URL_FILE.stat().st_size > 0:
                # Read the auth URL
                auth_url = AUTH_URL_FILE.read_text().strip()
                # Remove it immediately so we don't double process
                os.remove(AUTH_URL_FILE)
                
                print(f"[{time.strftime('%H:%M:%S')}] Found auth URL: {auth_url[:60]}...")
                REDIRECT_URL_FILE.write_text("PROCESSING...")
                
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
                    print(f"[{time.strftime('%H:%M:%S')}] Success! Outputting redirect URL.")
                    REDIRECT_URL_FILE.write_text(redirect_url)
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] Failed to capture redirect URL.")
                    print(f"Stdout:\n{res.stdout}")
                    print(f"Stderr:\n{res.stderr}")
                    REDIRECT_URL_FILE.write_text(f"ERROR: {res.stderr or 'Check YOGA logs'}")
                    
            time.sleep(2)
        except KeyboardInterrupt:
            print("Watcher stopped.")
            break
        except Exception as e:
            print(f"Error in watcher loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
