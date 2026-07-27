#!/usr/bin/env python3
"""
Clean up orphaned systemd user unit files pointing to non-existent scripts.
"""
import os
import subprocess

def main():
    user_systemd_dir = os.path.expanduser("~/.config/systemd/user")
    if not os.path.exists(user_systemd_dir):
        print("User systemd directory does not exist.")
        return

    cleaned = 0
    for fname in os.listdir(user_systemd_dir):
        if fname.endswith(".service") or fname.endswith(".timer"):
            fpath = os.path.join(user_systemd_dir, fname)
            with open(fpath, "r", errors="ignore") as f:
                content = f.read()
            # Check for ExecStart pointing to missing script in /home/john/Thunderbird
            for line in content.splitlines():
                if line.startswith("ExecStart=") and "/home/john/Thunderbird/" in line:
                    script_path = line.split("ExecStart=")[1].split()[0]
                    if not os.path.exists(script_path):
                        print(f"Orphaned unit found: {fname} -> missing script: {script_path}")
                        os.remove(fpath)
                        cleaned += 1
                        break
    print(f"Cleaned {cleaned} orphaned systemd user units.")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)

if __name__ == "__main__":
    main()
