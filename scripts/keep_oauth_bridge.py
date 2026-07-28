#!/usr/bin/env python3
import sys
import time
import subprocess
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.append(str(ROOT))

from api.thunderbird_keep import _get_keep
SCRIPT_PATH = ROOT / "scripts/auto_oauth_arbitrary.py"

def main():
    print("=== Google Keep OAuth Bridge Started ===")
    print("Watching Google Keep for a note titled 'For Hale'...")
    
    keep = _get_keep()
    
    while True:
        try:
            print("Syncing Keep...")
            keep.sync()
            
            # Look for active/archived notes titled "For Hale"
            target_note = None
            for note in list(keep.all()) + list(keep.getArchived() if hasattr(keep, 'getArchived') else []):
                if note.trashed:
                    continue
                title = (note.title or "").strip().lower()
                if title == "for hale":
                    target_note = note
                    break
                    
            if target_note:
                auth_url = target_note.text.strip()
                print(f"Found 'For Hale' note! Auth URL: {auth_url[:60]}...")
                
                # Delete the request note so we don't process it again
                target_note.trash()
                keep.sync()
                
                # Clean up any old "From Hale" notes first
                for note in list(keep.all()):
                    if (note.title or "").strip().lower() == "from hale":
                        note.trash()
                keep.sync()
                
                # Run browser automation
                print("Running browser automation on YOGA...")
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
                    print("Success! Creating 'From Hale' note...")
                    keep.createNote("From Hale", redirect_url)
                    keep.sync()
                    print("Bridge complete.")
                else:
                    print("Failed to capture redirect URL.")
                    err_msg = f"ERROR: Failed to capture redirect URL.\n\nSTDOUT:\n{res.stdout}\n\nSTDERR:\n{res.stderr}"
                    keep.createNote("From Hale", err_msg)
                    keep.sync()
                    
            time.sleep(10)
        except KeyboardInterrupt:
            print("Bridge stopped.")
            break
        except Exception as e:
            print(f"Error in Keep loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
