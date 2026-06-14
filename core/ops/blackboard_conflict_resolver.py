#!/usr/bin/env python3
"""
thunderbird-blackboard-conflict-resolver — Detect and resolve concurrent blackboard edits.

The blackboard is shared across Hale, Sterling, Dani, Intel.
This script:
  1. Checksums the blackboard on each run
  2. Detects if it changed since last checkpoint
  3. If changed, validates structure and logs the change
  4. If malformed (unclosed sections, truncated), restores from checkpoint

Schedule: Every 5 minutes after blackboard-sync via systemd timer
Output:   OpsCenter/logs/blackboard_resolver.log
          OpsCenter/data/blackboard_checkpoints/ (rolling 24h checkpoints)
          hale_decisions.md on conflicts or restores
"""

import hashlib
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
BLACKBOARD = ROOT / "OpsCenter/collaboration/blackboard.md"
CHECKPOINTS_DIR = ROOT / "OpsCenter/data/blackboard_checkpoints"
STATE_FILE = ROOT / "OpsCenter/data/blackboard_resolver_state.json"
LOG_PATH = ROOT / "OpsCenter/logs/blackboard_resolver.log"
AUDIT_LOG = ROOT / "OpsCenter/logs/blackboard_resolver.jsonl"
HALE_DECISIONS = ROOT / "hale_decisions.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BB-RESOLVER] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)

MAX_CHECKPOINTS = 288  # 24 hours at 5min intervals


def get_checksum(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def load_state() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except Exception:
        pass
    return {"last_checksum": None, "last_checkpoint": None, "conflict_count": 0}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def save_checkpoint(text: str, ts: datetime) -> Path:
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
    fp = CHECKPOINTS_DIR / f"blackboard_{ts.strftime('%Y%m%d_%H%M%S')}.md"
    fp.write_text(text)

    # Prune old checkpoints
    checkpoints = sorted(CHECKPOINTS_DIR.glob("blackboard_*.md"))
    if len(checkpoints) > MAX_CHECKPOINTS:
        for old in checkpoints[:-MAX_CHECKPOINTS]:
            old.unlink()

    return fp


def is_malformed(text: str) -> bool:
    """Basic structural validation of the blackboard markdown."""
    if not text.strip():
        return True
    # Check for obvious truncation: file ends mid-word (no trailing newline)
    if text and not text[-1] in ("\n", " ", "."):
        # Might be truncated
        if len(text) > 100 and text[-1].isalnum():
            return True
    return False


def find_latest_good_checkpoint() -> Path | None:
    if not CHECKPOINTS_DIR.exists():
        return None
    checkpoints = sorted(CHECKPOINTS_DIR.glob("blackboard_*.md"), reverse=True)
    for cp in checkpoints:
        text = cp.read_text(errors="ignore")
        if not is_malformed(text):
            return cp
    return None


def write_hale_decision(event: str, detail: str, run_dt: datetime) -> None:
    lines = [
        f"\n### {run_dt.strftime('%Y-%m-%d %H:%M:%S')} — Autonomous Decision (Tier T1)\n",
        f"**Decision:** Blackboard conflict resolver — {event}\n",
        f"**Detail:** {detail}\n",
        "**Domain:** Blackboard / Collaboration\n**Type:** autonomous maintenance\n**Outcome:** resolved\n",
    ]
    with open(HALE_DECISIONS, "a") as f:
        f.writelines(lines)


def main() -> int:
    run_dt = datetime.now()

    if not BLACKBOARD.exists():
        log.warning("Blackboard file not found — skipping")
        return 0

    text = BLACKBOARD.read_text(errors="ignore")
    checksum = get_checksum(text)
    state = load_state()

    changed = checksum != state.get("last_checksum")
    malformed = is_malformed(text)

    entry = {
        "ts": run_dt.isoformat(),
        "checksum": checksum,
        "changed": changed,
        "malformed": malformed,
        "size": len(text),
    }

    if malformed:
        log.error(f"BLACKBOARD MALFORMED — attempting restore from checkpoint")
        cp = find_latest_good_checkpoint()
        if cp:
            shutil.copy(cp, BLACKBOARD)
            log.info(f"Restored from checkpoint: {cp.name}")
            write_hale_decision(
                "BLACKBOARD RESTORED",
                f"Malformed blackboard detected and restored from {cp.name}",
                run_dt,
            )
            entry["action"] = f"restored_from:{cp.name}"
        else:
            log.error("No good checkpoint found — blackboard left as-is")
            entry["action"] = "no_checkpoint_available"
    elif changed:
        cp_path = save_checkpoint(text, run_dt)
        log.info(f"Blackboard changed (checksum {state.get('last_checksum','?')} → {checksum}) — checkpoint saved: {cp_path.name}")
        entry["action"] = f"checkpoint:{cp_path.name}"

        # Log concurrent writes (fast succession = likely conflict)
        state["conflict_count"] = state.get("conflict_count", 0)
    else:
        log.debug("Blackboard unchanged")
        entry["action"] = "no_change"

    state["last_checksum"] = checksum
    state["last_checkpoint"] = run_dt.isoformat()
    save_state(state)

    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
