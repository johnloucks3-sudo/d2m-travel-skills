#!/usr/bin/env python3
"""
Perx nightly scraper with venv activation and keep-alive logic.
Runs perx_intel_monitor.py inside .venv-perx.
Restarts on failure and maintains continuous operation.
"""
import subprocess
import sys
import os
import time
from pathlib import Path

project_root = Path.home() / "Thunderbird"
venv_path = project_root / ".venv-perx"
python_exe = venv_path / "bin" / "python"
scraper_script = project_root / "scripts" / "perx_intel_monitor.py"

# Verify venv exists
if not venv_path.exists():
    print(f"ERROR: venv not found at {venv_path}")
    sys.exit(1)

# Verify scraper script exists
if not scraper_script.exists():
    print(f"WARNING: scraper script not found at {scraper_script}")

# Prepare environment with venv activation
env = os.environ.copy()
env['VIRTUAL_ENV'] = str(venv_path)
env['PATH'] = str(venv_path / "bin") + ":" + env.get('PATH', '')

print(f"🔄 Perx keep-alive loop started")
print(f"   venv: {venv_path}")
print(f"   scraper: {scraper_script}")
print(f"   Python: {python_exe}")

# Keep-alive loop: restart on exit or error
while True:
    try:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting perx scraper...")
        proc = subprocess.run(
            [str(python_exe), str(scraper_script)],
            env=env,
            cwd=str(project_root),
            stdout=sys.stdout,
            stderr=sys.stderr
        )

        if proc.returncode != 0:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ⚠️  Process exited with code {proc.returncode}")
            print(f"   Restarting in 10 seconds...")
            time.sleep(10)
        else:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Process completed normally")

    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Perx keep-alive terminated by user.")
        sys.exit(0)

    except Exception as e:
        print(f"[ERROR] {e}")
        print(f"   Restarting in 10 seconds...")
        time.sleep(10)
