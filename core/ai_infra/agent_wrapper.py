import sys
import time
import os
import signal
from pathlib import Path

agent_name = sys.argv[1]
task = sys.argv[2]
nexus_lock = Path("/home/john/Thunderbird/OpsCenter/nexus.lock")

def check_heartbeat():
    if not nexus_lock.exists():
        os.kill(os.getpid(), signal.SIGTERM)
    # Check if lock has been updated in the last 60 seconds
    if time.time() - nexus_lock.stat().st_mtime > 60:
        os.kill(os.getpid(), signal.SIGTERM)

# Wrap task in heartbeat monitor
with open(f"/home/john/Thunderbird/logs/{agent_name}.log", "w") as f:
    f.write(f"Agent {agent_name} started task: {task}\n")

try:
    # Task simulation loop
    for _ in range(10):
        check_heartbeat()
        time.sleep(1)
    
    with open(f"/home/john/Thunderbird/logs/{agent_name}.log", "a") as f:
        f.write(f"Agent {agent_name} task complete.\n")
except Exception as e:
    with open(f"/home/john/Thunderbird/logs/{agent_name}.log", "a") as f:
        f.write(f"Agent {agent_name} terminated: {str(e)}\n")
