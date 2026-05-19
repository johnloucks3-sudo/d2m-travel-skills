#!/usr/bin/env python3
"""
persona_task_watcher.py — Real-time NEXUS task router to BRAVO
Dreams2Memories Travel, LLC | Gold Standard Coordination v1

Watches opencode_inbox.md for new NEXUS tasks and routes them to BRAVO in real-time.
Implements the gold standard protocol with active monitoring and escalation.
"""

import os
import sys
import time
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import threading

# Paths
INBOX_PATH = Path("/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md")
VERIFICATION_PATH = Path("/home/john/Thunderbird/OpsCenter/verification_checkpoint.py")
TASK_REGISTRY = Path("/home/john/Thunderbird/OpsCenter/task_registry.json")
AUDIT_LOG = Path("/home/john/Thunderbird/logs/persona_handoff_audit.jsonl")
WATCHER_LOG = Path("/home/john/Thunderbird/logs/persona_watcher.log")

# Telegram notification (fallback to system alert if Telegram fails)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_COMMANDER_ID", "7554895206")  # Commander for alerts

class PersonaTaskWatcher:
    """Real-time watcher that routes NEXUS tasks to BRAVO"""
    
    def __init__(self):
        self.ensure_directories()
        self.last_position = 0
        self.active_tasks = {}
        self.running = True
        
        # Load existing tasks on startup
        self.load_existing_tasks()
        
        print(f"[WATCHER] Starting gold standard persona task watcher")
        print(f"[WATCHER] Monitoring: {INBOX_PATH}")
        print(f"[WATCHER] Telegram alerts: {'ENABLED' if TELEGRAM_BOT_TOKEN else 'DISABLED'}")
    
    def ensure_directories(self):
        """Ensure log directory exists"""
        WATCHER_LOG.parent.mkdir(parents=True, exist_ok=True)
        
    def log_event(self, event: str, details: dict):
        """Log watcher events"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "details": details
        }
        
        with open(WATCHER_LOG, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {event}: {json.dumps(details)[:100]}...")
    
    def load_existing_tasks(self):
        """Load existing tasks from inbox on startup"""
        if not INBOX_PATH.exists():
            return
        
        content = INBOX_PATH.read_text()
        
        # Find all NEXUS tasks
        nexus_pattern = r'NEXUS:\s*(.+?)\s*(?=(?:NEXUS:|$))'
        tasks = re.findall(nexus_pattern, content, re.DOTNAME | re.IGNORECASE)
        
        for task_text in tasks:
            task_id = f"WATCHER-{hash(task_text) % 10000:04d}"
            if "ETC:" in task_text and "NLT:" in task_text:
                # Parse task details
                description_match = re.search(r'NEXUS:\s*(.+?)\s+ETC:', task_text, re.DOTNAME)
                etc_match = re.search(r'ETC:\s*(\d+)\s*[mM]', task_text)
                nlt_match = re.search(r'NLT:\s*([\d:]+\s*[A-Z]+)', task_text)
                
                if description_match and etc_match and nlt_match:
                    description = description_match.group(1).strip()
                    etc_minutes = int(etc_match.group(1))
                    nlt = nlt_match.group(1).strip()
                    
                    # Register with verification system
                    self.register_task(task_id, description, etc_minutes, nlt)
        
        self.log_event("STARTUP_LOAD", {"tasks_found": len(tasks)})
    
    def register_task(self, task_id: str, description: str, etc_minutes: int, nlt: str):
        """Register task with verification checkpoint"""
        try:
            cmd = [
                sys.executable, str(VERIFICATION_PATH),
                "register",
                "--task-id", task_id,
                "--description", description[:100],  # Truncate for safety
                "--assignee", "BRAVO",
                "--etc", str(etc_minutes),
                "--nlt", nlt
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log_event("TASK_REGISTERED", {
                    "task_id": task_id,
                    "description": description[:50],
                    "etc_minutes": etc_minutes,
                    "nlt": nlt
                })
                
                # Start task immediately
                self.start_task(task_id)
                
                # Send real-time alert to BRAVO
                self.alert_bravo(task_id, description, etc_minutes, nlt)
                
                return True
            else:
                self.log_event("REGISTRATION_FAILED", {
                    "task_id": task_id,
                    "error": result.stderr[:200]
                })
                return False
                
        except Exception as e:
            self.log_event("REGISTRATION_ERROR", {
                "task_id": task_id,
                "error": str(e)
            })
            return False
    
    def start_task(self, task_id: str):
        """Start task in verification system"""
        try:
            cmd = [
                sys.executable, str(VERIFICATION_PATH),
                "start",
                "--task-id", task_id
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log_event("TASK_STARTED", {"task_id": task_id})
                return True
            else:
                self.log_event("START_FAILED", {
                    "task_id": task_id,
                    "error": result.stderr[:200]
                })
                return False
                
        except Exception as e:
            self.log_event("START_ERROR", {
                "task_id": task_id,
                "error": str(e)
            })
            return False
    
    def alert_bravo(self, task_id: str, description: str, etc_minutes: int, nlt: str):
        """Send real-time alert to BRAVO via Telegram"""
        # Format alert message
        alert_message = (
            f"🦅 **NEXUS TASK ASSIGNED**\n"
            f"Task: {description[:100]}...\n"
            f"ID: `{task_id}`\n"
            f"ETC: {etc_minutes}m | NLT: {nlt}\n"
            f"Status: PENDING → IN_PROGRESS\n"
            f"Verification: Gold Standard Active\n"
            f"Timestamp: {datetime.now().strftime('%H:%M:%S MT')}"
        )
        
        # Try Telegram first
        if TELEGRAM_BOT_TOKEN:
            telegram_sent = self.send_telegram_alert(alert_message)
            if telegram_sent:
                self.log_event("TELEGRAM_ALERT_SENT", {"task_id": task_id})
            else:
                # Fallback to system alert
                self.log_event("TELEGRAM_FAILED_FALLBACK", {"task_id": task_id})
                self.system_alert(alert_message)
        else:
            # Telegram not configured, use system alert
            self.system_alert(alert_message)
            self.log_event("SYSTEM_ALERT_SENT", {"task_id": task_id})
    
    def send_telegram_alert(self, message: str) -> bool:
        """Send alert via Telegram bot"""
        try:
            import requests
            
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_notification": False
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            self.log_event("TELEGRAM_ERROR", {"error": str(e)[:100]})
            return False
    
    def system_alert(self, message: str):
        """Fallback system alert (write to alert file)"""
        alert_file = Path("/tmp/bravo_alerts.md")
        
        alert_entry = f"## ALERT {datetime.now().isoformat()}\n{message}\n\n"
        
        with open(alert_file, 'a') as f:
            f.write(alert_entry)
    
    def monitor_inbox(self):
        """Monitor inbox for new NEXUS tasks"""
        self.log_event("MONITOR_START", {"inbox_path": str(INBOX_PATH)})
        
        while self.running:
            try:
                if not INBOX_PATH.exists():
                    time.sleep(2)
                    continue
                
                # Read new content
                with open(INBOX_PATH, 'r') as f:
                    f.seek(self.last_position)
                    new_content = f.read()
                    self.last_position = f.tell()
                
                # Look for new NEXUS tasks
                nexus_pattern = r'NEXUS:\s*(.+?)(?=(?:NEXUS:|$))'
                tasks = re.findall(nexus_pattern, new_content, re.DOTNAME | re.IGNORECASE)
                
                for task_text in tasks:
                    # Skip if doesn't have required fields
                    if "ETC:" not in task_text or "NLT:" not in task_text:
                        continue
                    
                    # Parse task
                    description_match = re.search(r'NEXUS:\s*(.+?)\s+ETC:', task_text, re.DOTNAME)
                    etc_match = re.search(r'ETC:\s*(\d+)\s*[mM]', task_text)
                    nlt_match = re.search(r'NLT:\s*([\d:]+\s*[A-Z]+)', task_text)
                    
                    if not (description_match and etc_match and nlt_match):
                        continue
                    
                    description = description_match.group(1).strip()
                    etc_minutes = int(etc_match.group(1))
                    nlt = nlt_match.group(1).strip()
                    
                    # Generate task ID
                    task_id = f"NEXUS-{int(time.time())}-{hash(description) % 1000:03d}"
                    
                    self.log_event("NEW_NEXUS_TASK", {
                        "task_id": task_id,
                        "description": description[:50],
                        "etc_minutes": etc_minutes,
                        "nlt": nlt
                    })
                    
                    # Register and alert
                    self.register_task(task_id, description, etc_minutes, nlt)
                
                # Check for task timeouts (every 30 seconds)
                if int(time.time()) % 30 == 0:
                    self.check_timeouts()
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                self.log_event("MONITOR_ERROR", {"error": str(e)})
                time.sleep(5)
    
    def check_timeouts(self):
        """Check for tasks exceeding ETC and escalate"""
        try:
            # Use verification system to get active tasks
            cmd = [sys.executable, str(VERIFICATION_PATH), "health"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return
            
            health_data = json.loads(result.stdout)
            
            for task in health_data.get("active_tasks", []):
                task_id = task.get("task_id")
                status = task.get("status")
                etc_minutes = task.get("etc_minutes", 5)
                escalation_level = task.get("escalation_level", 0)
                
                # Check if task is stuck
                if status in ["IN_PROGRESS", "AWAITING_VERIFICATION"]:
                    # Get task details from registry
                    if TASK_REGISTRY.exists():
                        with open(TASK_REGISTRY, 'r') as f:
                            registry = json.load(f)
                        
                        task_data = registry.get("tasks", {}).get(task_id)
                        if task_data:
                            created_at = datetime.fromisoformat(task_data.get("created_at", datetime.now().isoformat()))
                            elapsed = (datetime.now() - created_at).total_seconds() / 60
                            
                            # Escalate based on time
                            if elapsed > etc_minutes + 1:  # 1 minute grace
                                self.escalate_task(task_id, escalation_level, elapsed, etc_minutes)
            
        except Exception as e:
            self.log_event("TIMEOUT_CHECK_ERROR", {"error": str(e)})
    
    def escalate_task(self, task_id: str, current_level: int, elapsed: float, etc: int):
        """Escalate task according to escalation matrix"""
        if current_level == 0:
            # Level 1: Internal polling alert
            alert_msg = f"⚠️ Task {task_id} approaching ETC ({elapsed:.1f}m > {etc}m)"
            self.log_event("ESCALATION_LEVEL_1", {
                "task_id": task_id,
                "elapsed_minutes": elapsed,
                "etc_minutes": etc
            })
            
        elif current_level == 1:
            # Level 2: Partner escalation (ALPHA→BRAVO or vice versa)
            alert_msg = f"🚨 Task {task_id} exceeded ETC ({elapsed:.1f}m > {etc}m) - Escalating to partner persona"
            self.log_event("ESCALATION_LEVEL_2", {
                "task_id": task_id,
                "elapsed_minutes": elapsed,
                "etc_minutes": etc
            })
            
            # Use verification system to escalate
            cmd = [
                sys.executable, str(VERIFICATION_PATH),
                "escalate",
                "--task-id", task_id,
                "--reason", f"ETC exceeded: {elapsed:.1f}m > {etc}m"
            ]
            subprocess.run(cmd, capture_output=True)
            
        elif current_level >= 2:
            # Level 3+: Commander alert
            alert_msg = (
                f"🔴 CRITICAL: Task {task_id} failed escalation "
                f"({elapsed:.1f}m > {etc}m ETC)\n"
                f"Current level: {current_level}\n"
                f"Immediate Commander intervention required"
            )
            
            self.log_event("ESCALATION_LEVEL_3+", {
                "task_id": task_id,
                "elapsed_minutes": elapsed,
                "etc_minutes": etc,
                "current_level": current_level
            })
            
            # Send critical Telegram alert
            if TELEGRAM_BOT_TOKEN:
                self.send_telegram_alert(alert_msg)
        
        # Log escalation
        print(f"[ESCALATION] {alert_msg}")
    
    def run(self):
        """Main watcher loop"""
        monitor_thread = threading.Thread(target=self.monitor_inbox, daemon=True)
        monitor_thread.start()
        
        self.log_event("WATCHER_STARTED", {
            "pid": os.getpid(),
            "inbox_path": str(INBOX_PATH),
            "timestamp": datetime.now().isoformat()
        })
        
        print("\n" + "="*60)
        print("🦅 PERSONA TASK WATCHER — GOLD STANDARD ACTIVE")
        print("="*60)
        print(f"• Monitoring: {INBOX_PATH}")
        print(f"• Verification: {VERIFICATION_PATH}")
        print(f"• Telegram alerts: {'ENABLED' if TELEGRAM_BOT_TOKEN else 'DISABLED (fallback active)'}")
        print(f"• Started: {datetime.now().strftime('%H:%M:%S MT')}")
        print("="*60)
        print("Waiting for NEXUS tasks... (Ctrl+C to stop)")
        print("\nTo task BRAVO:")
        print('  echo "NEXUS: <task> ETC: <minutes> NLT: <timestamp>" >> opencode_inbox.md')
        print("="*60 + "\n")
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            self.log_event("WATCHER_STOPPED", {"reason": "KeyboardInterrupt"})
            print("\n[WATCHER] Stopping...")
        
        monitor_thread.join(timeout=5)

def main():
    """Main entry point"""
    watcher = PersonaTaskWatcher()
    watcher.run()

if __name__ == "__main__":
    main()