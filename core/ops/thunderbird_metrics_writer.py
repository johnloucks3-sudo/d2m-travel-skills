#!/usr/bin/env python3
"""
thunderbird_metrics_writer.py — Append-only JSONL metrics for Thunderbird OS
Owner: A7 Sterling (primary) + Hale (JET) infra
Schema v1.0 per Lifecycle Automation Compact Annex
"""

import json
from datetime import datetime, timezone
from pathlib import Path

METRICS_FILE = Path("/home/john/Thunderbird/metrics/metrics.jsonl")
METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)

def write_metric(metric_name: str, value, source: str, confidence: str = "HIGH"):
    """Append one metric line. Never overwrites."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "metric_name": metric_name,
        "schema_version": "1.0",
        "value": value,
        "source": source,
        "confidence": confidence
    }
    with open(METRICS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

if __name__ == "__main__":
    write_metric("test_metric", 42, "hale_jet", "HIGH")
    print(f"Metrics writer smoke test written to {METRICS_FILE}")
