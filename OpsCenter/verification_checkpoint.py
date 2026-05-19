#!/usr/bin/env python3
"""
verification_checkpoint.py — Gold Standard Verification System
HALE Persona-to-Persona Task Coordination
Dreams2Memories Travel, LLC

Mandatory verification checkpoint for all task completions.
Prevents silent failures by requiring independent validation.
"""

import json
import sys
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Paths
TASK_REGISTRY = Path("/home/john/Thunderbird/OpsCenter/task_registry.json")
AUDIT_LOG = Path("/home/john/Thunderbird/logs/persona_handoff_audit.jsonl")
ESCALATION_MATRIX = Path("/home/john/Thunderbird/OpsCenter/escalation_matrix.json")

class VerificationCheckpoint:
    """Gold standard verification system for task completion"""
    
    def __init__(self):
        self.ensure_directories()
        self.load_registry()
        
    def ensure_directories(self):
        """Ensure all required directories exist"""
        TASK_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        ESCALATION_MATRIX.parent.mkdir(parents=True, exist_ok=True)
        
    def load_registry(self):
        """Load or create task registry"""
        if TASK_REGISTRY.exists():
            with open(TASK_REGISTRY, 'r') as f:
                self.registry = json.load(f)
        else:
            self.registry = {
                "version": "1.0",
                "tasks": {},
                "metadata": {
                    "last_updated": datetime.now().isoformat(),
                    "total_tasks": 0,
                    "completion_rate": 0.0
                }
            }
            self.save_registry()
    
    def save_registry(self):
        """Save task registry"""
        self.registry["metadata"]["last_updated"] = datetime.now().isoformat()
        with open(TASK_REGISTRY, 'w') as f:
            json.dump(self.registry, f, indent=2)
    
    def log_audit(self, task_id: str, event: str, details: Dict):
        """Log audit trail entry"""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "event": event,
            "details": details
        }
        
        with open(AUDIT_LOG, 'a') as f:
            f.write(json.dumps(audit_entry) + '\n')
    
    def register_task(self, task_id: str, description: str, assignee: str, 
                     etc_minutes: int, nlt: str):
        """Register a new task"""
        task = {
            "task_id": task_id,
            "description": description,
            "assignee": assignee,
            "status": "PENDING",
            "etc_minutes": etc_minutes,
            "nlt": nlt,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "verification_passed": False,
            "verification_artifacts": [],
            "escalation_level": 0
        }
        
        self.registry["tasks"][task_id] = task
        self.registry["metadata"]["total_tasks"] += 1
        
        self.log_audit(task_id, "REGISTERED", {
            "description": description,
            "assignee": assignee,
            "etc_minutes": etc_minutes,
            "nlt": nlt
        })
        
        self.save_registry()
        print(f"✅ Task {task_id} registered to {assignee}")
    
    def start_task(self, task_id: str):
        """Mark task as in progress"""
        if task_id not in self.registry["tasks"]:
            print(f"❌ Task {task_id} not found")
            return False
        
        task = self.registry["tasks"][task_id]
        task["status"] = "IN_PROGRESS"
        task["started_at"] = datetime.now().isoformat()
        task["updated_at"] = datetime.now().isoformat()
        
        self.log_audit(task_id, "STARTED", {
            "timestamp": task["started_at"]
        })
        
        self.save_registry()
        print(f"▶️ Task {task_id} started")
        return True
    
    def submit_for_verification(self, task_id: str, artifacts: List[str]):
        """Submit task completion for verification"""
        if task_id not in self.registry["tasks"]:
            print(f"❌ Task {task_id} not found")
            return False
        
        task = self.registry["tasks"][task_id]
        task["status"] = "AWAITING_VERIFICATION"
        task["verification_artifacts"] = artifacts
        task["updated_at"] = datetime.now().isoformat()
        
        self.log_audit(task_id, "SUBMITTED_FOR_VERIFICATION", {
            "artifacts": artifacts
        })
        
        self.save_registry()
        print(f"📤 Task {task_id} submitted for verification with {len(artifacts)} artifacts")
        return True
    
    def verify_completion(self, task_id: str) -> Tuple[bool, List[str]]:
        """Verify task completion (gold standard verification)"""
        if task_id not in self.registry["tasks"]:
            return False, [f"Task {task_id} not found"]
        
        task = self.registry["tasks"][task_id]
        
        # Verification criteria
        issues = []
        
        # 1. Check required artifacts exist
        for artifact in task.get("verification_artifacts", []):
            artifact_path = Path(artifact)
            if not artifact_path.exists():
                issues.append(f"Missing artifact: {artifact}")
            elif artifact_path.stat().st_size == 0:
                issues.append(f"Empty artifact: {artifact}")
        
        # 2. Check recency (artifacts created within last 5 minutes)
        max_age_seconds = 300  # 5 minutes
        current_time = time.time()
        
        for artifact in task.get("verification_artifacts", []):
            artifact_path = Path(artifact)
            if artifact_path.exists():
                age = current_time - artifact_path.stat().st_mtime
                if age > max_age_seconds:
                    issues.append(f"Artifact too old ({age:.0f}s): {artifact}")
        
        # 3. Check if ETC was respected
        if task.get("started_at"):
            started = datetime.fromisoformat(task["started_at"])
            now = datetime.now()
            elapsed_minutes = (now - started).total_seconds() / 60
            
            if elapsed_minutes > task.get("etc_minutes", 5) + 1:  # 1 minute grace
                issues.append(f"ETC exceeded: {elapsed_minutes:.1f}m > {task['etc_minutes']}m")
        
        if issues:
            task["verification_passed"] = False
            task["status"] = "VERIFICATION_FAILED"
            self.log_audit(task_id, "VERIFICATION_FAILED", {"issues": issues})
            self.save_registry()
            return False, issues
        else:
            # Verification passed
            task["verification_passed"] = True
            task["status"] = "COMPLETE"
            task["completed_at"] = datetime.now().isoformat()
            
            # Update completion rate
            completed_tasks = sum(1 for t in self.registry["tasks"].values() 
                                if t.get("status") == "COMPLETE")
            total_tasks = len(self.registry["tasks"])
            self.registry["metadata"]["completion_rate"] = (
                completed_tasks / total_tasks if total_tasks > 0 else 0.0
            )
            
            self.log_audit(task_id, "VERIFICATION_PASSED", {
                "completed_at": task["completed_at"]
            })
            
            self.save_registry()
            return True, []
    
    def escalate_task(self, task_id: str, reason: str):
        """Escalate task to next level"""
        if task_id not in self.registry["tasks"]:
            print(f"❌ Task {task_id} not found")
            return False
        
        task = self.registry["tasks"][task_id]
        task["escalation_level"] = task.get("escalation_level", 0) + 1
        task["status"] = "ESCALATED"
        task["updated_at"] = datetime.now().isoformat()
        
        self.log_audit(task_id, "ESCALATED", {
            "level": task["escalation_level"],
            "reason": reason
        })
        
        self.save_registry()
        print(f"⚠️ Task {task_id} escalated to level {task['escalation_level']}: {reason}")
        return True
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get detailed task status"""
        return self.registry["tasks"].get(task_id)
    
    def list_active_tasks(self) -> List[Dict]:
        """List all active (non-complete) tasks"""
        active = []
        for task_id, task in self.registry["tasks"].items():
            if task.get("status") not in ["COMPLETE", "CANCELLED"]:
                active.append({
                    "task_id": task_id,
                    "description": task.get("description", ""),
                    "assignee": task.get("assignee", ""),
                    "status": task.get("status", "UNKNOWN"),
                    "etc_minutes": task.get("etc_minutes", 0),
                    "escalation_level": task.get("escalation_level", 0),
                    "updated_at": task.get("updated_at", "")
                })
        return active
    
    def health_check(self) -> Dict:
        """System health check"""
        active_tasks = self.list_active_tasks()
        total_tasks = len(self.registry["tasks"])
        completed_tasks = sum(1 for t in self.registry["tasks"].values() 
                            if t.get("status") == "COMPLETE")
        
        return {
            "status": "OK" if total_tasks > 0 else "NO_TASKS",
            "metrics": {
                "total_tasks": total_tasks,
                "active_tasks": len(active_tasks),
                "completed_tasks": completed_tasks,
                "completion_rate": self.registry["metadata"]["completion_rate"],
                "registry_file": str(TASK_REGISTRY),
                "registry_exists": TASK_REGISTRY.exists(),
                "audit_log_exists": AUDIT_LOG.exists(),
                "escalation_matrix_exists": ESCALATION_MATRIX.exists()
            },
            "active_tasks": active_tasks
        }

def main():
    """CLI interface for verification checkpoint"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gold Standard Verification System")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Register task
    register_parser = subparsers.add_parser("register", help="Register new task")
    register_parser.add_argument("--task-id", required=True, help="Task ID")
    register_parser.add_argument("--description", required=True, help="Task description")
    register_parser.add_argument("--assignee", required=True, help="Assignee (ALPHA/BRAVO)")
    register_parser.add_argument("--etc", type=int, required=True, help="ETC in minutes")
    register_parser.add_argument("--nlt", required=True, help="No Later Than timestamp")
    
    # Start task
    start_parser = subparsers.add_parser("start", help="Start task")
    start_parser.add_argument("--task-id", required=True, help="Task ID")
    
    # Submit for verification
    submit_parser = subparsers.add_parser("submit", help="Submit task for verification")
    submit_parser.add_argument("--task-id", required=True, help="Task ID")
    submit_parser.add_argument("--artifacts", nargs="+", required=True, help="Artifact paths")
    
    # Verify
    verify_parser = subparsers.add_parser("verify", help="Verify task completion")
    verify_parser.add_argument("--task-id", required=True, help="Task ID")
    
    # Status
    status_parser = subparsers.add_parser("status", help="Get task status")
    status_parser.add_argument("--task-id", help="Task ID (optional)")
    
    # Health
    subparsers.add_parser("health", help="System health check")
    
    # List
    subparsers.add_parser("list", help="List active tasks")
    
    # Escalate
    escalate_parser = subparsers.add_parser("escalate", help="Escalate task")
    escalate_parser.add_argument("--task-id", required=True, help="Task ID")
    escalate_parser.add_argument("--reason", required=True, help="Escalation reason")
    
    args = parser.parse_args()
    vc = VerificationCheckpoint()
    
    if args.command == "register":
        vc.register_task(args.task_id, args.description, args.assignee, args.etc, args.nlt)
    
    elif args.command == "start":
        vc.start_task(args.task_id)
    
    elif args.command == "submit":
        vc.submit_for_verification(args.task_id, args.artifacts)
    
    elif args.command == "verify":
        success, issues = vc.verify_completion(args.task_id)
        if success:
            print(f"✅ Verification PASSED for task {args.task_id}")
        else:
            print(f"❌ Verification FAILED for task {args.task_id}")
            for issue in issues:
                print(f"  - {issue}")
    
    elif args.command == "status":
        if args.task_id:
            task = vc.get_task_status(args.task_id)
            if task:
                print(json.dumps(task, indent=2))
            else:
                print(f"Task {args.task_id} not found")
        else:
            health = vc.health_check()
            print(json.dumps(health, indent=2))
    
    elif args.command == "health":
        health = vc.health_check()
        print(json.dumps(health, indent=2))
    
    elif args.command == "list":
        active_tasks = vc.list_active_tasks()
        if active_tasks:
            for task in active_tasks:
                print(f"{task['task_id']}: {task['description'][:50]}... [{task['status']}]")
        else:
            print("No active tasks")
    
    elif args.command == "escalate":
        vc.escalate_task(args.task_id, args.reason)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()