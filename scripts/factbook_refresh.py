#!/usr/bin/env python3
"""
factbook_refresh.py — Operational continuity factbook (Claude headless dispatch).
Spawns Claude Code to synthesize destination operational intelligence from local intel.
Focuses on continuity gaps: itinerary blockers, supplier status, contingency routing.
Output: OpsCenter/state/factbook_latest.json
"""
import json
import sys
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
REPORT = ROOT / "OpsCenter/state/factbook_latest.json"

DESTINATIONS = ["Norway", "Iceland", "Denmark", "Finland", "Japan", "Hawaii", "Greece"]


def spawn_claude_factbook() -> dict:
    """Spawn headless Claude to synthesize operational continuity factbook."""
    prompt = """TASK: Build operational continuity factbook for Dreams2Memories Travel.

Destinations: """ + ', '.join(DESTINATIONS) + """

For EACH destination, analyze these dimensions:
1. CONTINUITY BLOCKERS — What could break a trip? (visa changes, port strikes, supplier outages, weather windows)
2. CONTINGENCY ROUTES — If primary routing fails, what's the alternative? (flight reroutes, port changes, hotel alternates)
3. SUPPLIER STATUS — Which vendors are P0 for this destination? (airlines, hotels, tour operators, transfers)
4. REGULATORY ALERTS — Visa, vaccination, customs, entry permit changes in the last 30 days

Sources: dossiers/*, intel/*, OpsCenter/state/*.

WRITE full JSON factbook to /tmp/factbook_working.json with this structure:
{
  "generated": "ISO datetime",
  "destinations": [
    {
      "name": "Norway",
      "continuity_blockers": ["...", "..."],
      "contingency_routing": {
        "primary": "...",
        "alternate_1": "...",
        "alternate_2": "..."
      },
      "critical_suppliers": ["supplier1 (type)", "supplier2 (type)"],
      "regulatory_alerts": ["...", "..."],
      "last_updated": "ISO datetime"
    },
    ...
  ],
  "metadata": {
    "coverage": "Destinations analyzed",
    "confidence": "Data freshness",
    "source": "Local dossier + intel scan"
  }
}

Output ONLY valid JSON. No preamble, no explanation."""

    from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude

    working_file = "/tmp/factbook_working.json"
    result = spawn_headless_claude(
        prompt=prompt,
        output_file=working_file,
        model="claude-haiku-4-5-20251001",
        task_name="factbook-refresh",
        background=False,
        # FIXED 2026-07-16 (CI remediation): starting at opus broke the
        # haiku->sonnet->opus escalation chain — opus has no tier above it,
        # so all 3 retries ran at opus × 280s = 840s total, always exceeding
        # TimeoutStartSec=300. Restored to haiku (chain origin) with 120s
        # per-attempt timeout. TimeoutStartSec raised to 900s via drop-in
        # (/home/john/.config/systemd/user/d2m-factbook-refresh.service.d/
        # timeout-override.conf) to accommodate 3×120s + startup overhead.
        # Haiku is sufficient for local dossier synthesis (no live API calls).
        timeout=120,
    )

    if result.get("status") != "COMPLETED":
        print(f"ERROR: headless spawn failed: {result}", file=sys.stderr)
        return {"error": result.get("error", "spawn_failed"), "log": result.get("log_file")}

    try:
        return json.loads(Path(working_file).read_text())
    except Exception as e:
        print(f"WARNING: Claude output not valid JSON: {e}", file=sys.stderr)
        return {"error": "parse_failed", "log": result.get("log_file")}


def main() -> int:
    print("factbook_refresh: Spawning Claude Haiku for continuity analysis...", file=sys.stderr)
    factbook = spawn_claude_factbook()

    if "error" in factbook:
        # Non-mission-critical (ELON 2026-07-18): exit 0 so the unit never
        # enters failed state and the OnFailure remediation cascade cannot fire.
        # The spawn timeout is the expected failure mode when Claude OAuth is
        # temporarily unavailable; crashing the unit only burns swap and CPU.
        print(f"WARNING: factbook skipped this cycle — {factbook['error']}", file=sys.stderr)
        return 0

    REPORT.write_text(json.dumps(factbook, indent=2))
    dest_count = len(factbook.get("destinations", []))
    print(f"factbook_refresh: {dest_count} destinations analyzed → {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
