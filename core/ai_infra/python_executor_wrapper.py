"""
Python Executor Wrapper v1.2
Provides: heartbeat monitoring, timeout handling, error logging
"""
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

class PythonExecutor:
    def __init__(self, task_id, script_name, timeout_seconds=30):
        self.task_id = task_id
        self.script_name = script_name
        self.timeout_seconds = timeout_seconds
        self.heartbeat_file = Path("/home/john/Thunderbird/logs/python_heartbeat.txt")
        self.error_file = Path("/home/john/Thunderbird/logs/python_errors.txt")
        self.audit_file = Path("/home/john/Thunderbird/logs/python_audit.jsonl")
        
    def heartbeat(self, status="running"):
        """Log execution heartbeat"""
        self.heartbeat_file.parent.mkdir(exist_ok=True)
        entry = f"{datetime.now().isoformat()} | {self.task_id} | {status}"
        with open(self.heartbeat_file, 'a') as f:
            f.write(entry + "\n")
    
    def log_error(self, error_msg):
        """Log execution error"""
        self.error_file.parent.mkdir(exist_ok=True)
        entry = f"{datetime.now().isoformat()} | {self.task_id} | {error_msg}"
        with open(self.error_file, 'a') as f:
            f.write(entry + "\n")
    
    def log_audit(self, output, confidence=100, escalated=False):
        """Log to audit trail"""
        self.audit_file.parent.mkdir(exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "task_id": self.task_id,
            "script": self.script_name,
            "confidence": confidence,
            "escalated": escalated,
            "final_decision_by": "Python" if not escalated else "Pending",
        }
        with open(self.audit_file, 'a') as f:
            f.write(json.dumps(entry) + "\n")
    
    @contextmanager
    def execute(self):
        """Context manager for safe execution"""
        self.heartbeat("STARTING")
        try:
            yield self
            self.heartbeat("COMPLETE")
        except Exception as e:
            self.log_error(str(e))
            self.heartbeat("FAILED")
            raise

# Usage:
# executor = PythonExecutor("TASK-001", "my_script.py", timeout_seconds=30)
# with executor.execute():
#     # do work here
#     executor.log_audit(output_data, confidence=95)
