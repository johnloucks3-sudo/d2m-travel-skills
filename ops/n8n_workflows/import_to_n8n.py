#!/usr/bin/env python3
"""
Direct n8n workflow import via SQLite database.
n8n uses SQLite database at ~/.n8n/database.sqlite
"""

import json
import os
import sqlite3
from pathlib import Path

# n8n database location
N8N_DB_PATH = Path.home() / ".n8n" / "database.sqlite"
WORKFLOW_FILE = Path(__file__).parent / "touchpoint_draft_engine.json"


def import_workflow():
    """Import workflow into n8n database directly"""

    if not N8N_DB_PATH.exists():
        print(f"n8n database not found at {N8N_DB_PATH}")
        return False

    if not WORKFLOW_FILE.exists():
        print(f"Workflow file not found: {WORKFLOW_FILE}")
        return False

    # Read workflow JSON
    with open(WORKFLOW_FILE, "r") as f:
        workflow_data = json.load(f)

    # Connect to n8n database
    conn = sqlite3.connect(N8N_DB_PATH)
    cursor = conn.cursor()

    try:
        # Insert workflow
        cursor.execute(
            """
            INSERT INTO workflow_entity (name, active, nodes, connections, staticData, settings, tags, triggerCount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                workflow_data["name"],
                False,  # inactive until tested
                json.dumps(workflow_data["nodes"]),
                json.dumps(workflow_data["connections"]),
                json.dumps(workflow_data.get("staticData", {})),
                json.dumps(workflow_data.get("settings", {})),
                json.dumps(workflow_data.get("tags", [])),
                workflow_data.get("triggerCount", 1),
            ),
        )

        workflow_id = cursor.lastrowid
        conn.commit()
        print(f"✅ Workflow imported with ID: {workflow_id}")

        # Create webhook entry if needed
        # (n8n auto-creates webhooks based on trigger nodes)

        return True

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = import_workflow()
    exit(0 if success else 1)
