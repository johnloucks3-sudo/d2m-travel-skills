#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE    = Path("/home/john/Thunderbird/hale_state.json")
METRICS_FILE  = Path("/home/john/Thunderbird/OpsCenter/a7_metrics_dashboard.json")
QUALITY_LOG   = Path("/home/john/Thunderbird/OpsCenter/quality_log.json")

def calculate_metrics():
    metrics = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Automated generation by generate_a7_metrics.py",
        "process": {"open_tasks_count": 0, "system_mode": "UNKNOWN"},
        "quality": {},
        "cost_control": {},
        "exercise": {},
        "red_items": [],
    }

    # ── State metrics ───────────────────────────────────────────────────
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        tasks = state.get("open_tasks", [])
        open_tasks = sum(1 for t in tasks if t.get("status") != "COMPLETE")
        metrics["process"] = {
            "open_tasks_count": open_tasks,
            "system_mode": state.get("system_mode", "UNKNOWN"),
        }

    # ── Quality metrics ─────────────────────────────────────────────────
    exercises = []
    if QUALITY_LOG.exists():
        try:
            data = json.loads(QUALITY_LOG.read_text())
            exercises = data.get("exercises", [])
        except Exception:
            exercises = []

    if exercises:
        scores = [e.get("quality_score", 0) for e in exercises]
        qm_defined = sum(1 for e in exercises if e.get("qm_fields_defined"))
        avg_score = sum(scores) / len(scores)
        metrics["quality"] = {
            "exercise_quality_score_pct": round(avg_score, 1),
            "pre_task_qm_completion_rate": round((qm_defined / len(exercises)) * 100, 1),
            "total_exercises": len(exercises),
            "target": {"quality_score_pct": 85, "qm_completion_rate": 100},
            "red_threshold": {"quality_score_pct": 60},
        }
        if avg_score < 60:
            metrics["red_items"].append(
                f"Quality score ({avg_score:.0f}%) below red threshold (60%). "
                f"Review latest {len(exercises)} exercises."
            )
    else:
        metrics["quality"] = {
            "exercise_quality_score_pct": None,
            "pre_task_qm_completion_rate": None,
            "total_exercises": 0,
            "note": "No exercises recorded yet",
        }

    # ── Red items from process ──────────────────────────────────────────
    if metrics["process"]["open_tasks_count"] > 5:
        metrics["red_items"].append(
            f"Open tasks ({metrics['process']['open_tasks_count']}) exceeds 5."
        )

    return metrics

def generate_metrics():
    metrics = calculate_metrics()
    METRICS_FILE.write_text(json.dumps(metrics, indent=2))
    print(f"Generated metrics at {metrics['generated_at']}")
    if metrics["red_items"]:
        print(f"  Red items: {len(metrics['red_items'])}")
        for item in metrics["red_items"]:
            print(f"    ⚠️  {item[:120]}")

if __name__ == "__main__":
    generate_metrics()
