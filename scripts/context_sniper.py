#!/usr/bin/env python3
"""
Context Sniper — Token Budget Foreman
======================================
Builds persona-appropriate context briefs from durable external sources.
Called explicitly via MCP tool or CLI when context bloat is detected.

Architecture: Instead of compressing the conversation (which we can't intercept),
we rebuild context from ground-truth sources: mission board, blackboard, relay,
pins, fare watches, and TESS status. Each persona gets a tuned view.

Usage:
  python3 scripts/context_sniper.py brief --persona hale
  python3 scripts/context_sniper.py status
  python3 scripts/context_sniper.py pin "Current task: wire thunderbird-core" --category plan
  python3 scripts/context_sniper.py pins
  python3 scripts/context_sniper.py unpin <pin_id>
  python3 scripts/context_sniper.py calibrate  # show self-calibration stats
"""

import json
import os
import sys
import subprocess
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

BASE = Path("/home/john/Thunderbird")
CONFIG_FILE = BASE / "config/context_sniper_policies.json"
PINS_FILE = BASE / "data/context_sniper_pins.json"
CALIBRATION_FILE = BASE / "data/context_sniper_calibration.json"

# ── Utility ──────────────────────────────────────────────────────────────────

def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default if default is not None else {}

def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))

def estimate_tokens(text: str) -> int:
    # 1 token ≈ 4 chars (conservative for mixed prose/code)
    return max(1, len(text) // 4)

# ── Pin Manager ───────────────────────────────────────────────────────────────

class PinManager:
    def __init__(self):
        self.pins = load_json(PINS_FILE, {"pins": [], "next_id": 1})

    def add(self, item: str, category: str = "critical") -> dict:
        pin = {
            "id": self.pins["next_id"],
            "item": item,
            "category": category,
            "created": now_utc(),
            "active": True,
        }
        self.pins["pins"].append(pin)
        self.pins["next_id"] += 1
        save_json(PINS_FILE, self.pins)
        return pin

    def remove(self, pin_id: int) -> bool:
        for p in self.pins["pins"]:
            if p["id"] == pin_id:
                p["active"] = False
                save_json(PINS_FILE, self.pins)
                return True
        return False

    def active_pins(self, limit: int = 25) -> list:
        return [p for p in self.pins["pins"] if p["active"]][:limit]

    def format_pins(self, limit: int = 25) -> str:
        pins = self.active_pins(limit)
        if not pins:
            return ""
        lines = ["📌 PINNED (never drop):"]
        for p in pins:
            cat_tag = f"[{p['category']}]" if p["category"] != "critical" else ""
            lines.append(f"  #{p['id']} {cat_tag} {p['item']}")
        return "\n".join(lines)

# ── Source Readers ────────────────────────────────────────────────────────────

def read_mission_board(max_missions: int = 10, priority_filter: Optional[list] = None) -> str:
    import re
    title_re = re.compile(r"(🔴|🟠|🟡|🟢|✅)\s+(MISSION-\d+:.*)")
    status_re = re.compile(r"Status:\s*\S+\s*\|\s*Priority:\s*(\S+)\s*\|")
    try:
        result = subprocess.run(
            ["python3", str(BASE / "OpsCenter/mission_board_sync.py"), "list"],
            capture_output=True, text=True, cwd=str(BASE), timeout=10
        )
        if result.returncode != 0:
            return "(mission board unavailable)"
        lines = result.stdout.strip().split("\n")
        # Build list of (title_line, priority)
        missions = []
        i = 0
        while i < len(lines):
            m = title_re.search(lines[i])
            if m:
                title = f"{m.group(1)} {m.group(2)}"
                priority = "?"
                if i + 1 < len(lines):
                    sm = status_re.search(lines[i + 1])
                    if sm:
                        priority = sm.group(1).rstrip("|").strip()
                missions.append((title, priority))
            i += 1
        # Filter and limit
        kept = []
        for title, priority in missions:
            if priority_filter and not any(pf == priority for pf in priority_filter):
                continue
            kept.append(f"{title}  [{priority}]")
            if len(kept) >= max_missions:
                break
        return "\n".join(kept) if kept else "(no matching missions)"
    except Exception as e:
        return f"(mission board error: {e})"

def read_blackboard_delta(lines: int = 20) -> str:
    bb_path = BASE / "OpsCenter/collaboration/blackboard.md"
    try:
        content = bb_path.read_text()
        tail = content.strip().split("\n")[-lines:]
        return "\n".join(tail)
    except Exception:
        return "(blackboard unavailable)"

def read_relay_log(count: int = 5) -> str:
    try:
        result = subprocess.run(
            ["python3", str(BASE / "core/relay/wing_relay.py"), "read", "OC"],
            capture_output=True, text=True, cwd=str(BASE), timeout=10
        )
        if result.returncode != 0:
            return "(relay unavailable)"
        lines = result.stdout.strip().split("\n")[-count:]
        return "\n".join(lines)
    except Exception as e:
        return f"(relay error: {e})"

def read_git_status_short() -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--branch"],
            capture_output=True, text=True, cwd=str(BASE), timeout=5
        )
        lines = result.stdout.strip().split("\n")[:10]
        return "\n".join(lines)
    except Exception:
        return "(git unavailable)"

def read_financial_pulse() -> str:
    pulse_path = BASE / "OpsCenter/hale_state.json"
    try:
        data = load_json(pulse_path, {})
        fp = data.get("financial_pulse", {})
        if not fp:
            return "(financial pulse unavailable)"
        lines = ["Financial pulse:"]
        for k, v in fp.items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)
    except Exception:
        return "(financial pulse unavailable)"

def read_fare_watches() -> str:
    fw_path = BASE / "core/travel/data/fare_watches.json"  # consolidated single store (2026-06-16)
    try:
        data = load_json(fw_path, [])
        if not data:
            return "(no active fare watches)"
        lines = [f"Fare watches ({len(data)} active):"]
        for w in data[:5]:
            lines.append(f"  {w.get('id','?')}: {w.get('description','')}")
        return "\n".join(lines)
    except Exception:
        return "(fare watch unavailable)"

def read_tess_status() -> str:
    token_path = BASE / "tess_token.json"
    try:
        data = load_json(token_path, {})
        exp = data.get("expiresAt", "")
        user = data.get("userId", "")
        if not exp:
            return "TESS: no token"
        exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
        mins = int((exp_dt - datetime.now(timezone.utc)).total_seconds() / 60)
        status = "OK" if mins > 10 else "EXPIRING"
        return f"TESS: {status} ({mins} min remaining, user {user})"
    except Exception:
        return "TESS: unknown"

def read_overdue_missions() -> str:
    """Missions at WF-17 gate (pending_review status) or overdue."""
    import re
    title_re = re.compile(r"(🔴|🟠|🟡|🟢|✅)\s+(MISSION-\d+:.*)")
    try:
        result = subprocess.run(
            ["python3", str(BASE / "OpsCenter/mission_board_sync.py"), "list"],
            capture_output=True, text=True, cwd=str(BASE), timeout=10
        )
        if result.returncode != 0:
            return "(mission board unavailable)"
        lines = result.stdout.strip().split("\n")
        overdue = []
        for i, line in enumerate(lines):
            m = title_re.search(line)
            if not m:
                continue
            # Check the next line for status
            status_line = lines[i + 1] if i + 1 < len(lines) else ""
            if "pending_review" in status_line or "overdue" in status_line.lower():
                title = f"{m.group(1)} {m.group(2)}"
                # Extract priority
                pm = re.search(r"Priority:\s*(\S+)\s*\|", status_line)
                pri = pm.group(1) if pm else "?"
                overdue.append(f"{title}  [{pri}]")
        if not overdue:
            return "(no overdue items)"
        return "OVERDUE/WF-17 gate:\n" + "\n".join(overdue[:10])
    except Exception as e:
        return f"(overdue check error: {e})"

# ── Brief Builder ─────────────────────────────────────────────────────────────

class ContextSniper:
    def __init__(self):
        self.policies = load_json(CONFIG_FILE, {"personas": {}})
        self.pins = PinManager()

    def get_policy(self, persona: str) -> dict:
        return self.policies.get("personas", {}).get(persona) or self.policies["personas"]["default"]

    def build_brief(self, persona: str = "default", hint: str = "") -> str:
        policy = self.get_policy(persona)
        sections = policy.get("brief_sections", ["active_p0_p1", "pins", "blackboard_delta"])
        max_missions = policy.get("max_missions_shown", 8)
        max_relay = policy.get("max_relay_lines", 5)
        pin_limit = policy.get("pin_limit", 15)

        parts = []
        header = f"═══ CONTEXT SNIPER BRIEF — {persona.upper()} — {datetime.now().strftime('%Y-%m-%d %H:%M')} ═══"
        if hint:
            header += f"\nHint: {hint}"
        parts.append(header)

        section_map = {
            "overdue_missions": ("OVERDUE / WF-17 GATE", lambda: read_overdue_missions()),
            "active_p0_p1": (f"MISSION BOARD (P0/P1, top {max_missions})", lambda: read_mission_board(max_missions, ["P0", "P1"])),
            "active_p0_only": (f"MISSION BOARD (P0 only)", lambda: read_mission_board(max_missions, ["P0"])),
            "current_mission": ("CURRENT MISSION", lambda: read_mission_board(3, ["P0", "P1"])),
            "pending_wf17": ("PENDING WF-17", lambda: read_overdue_missions()),
            "blackboard_delta": (f"BLACKBOARD (last {min(max_relay * 2, 20)} lines)", lambda: read_blackboard_delta(min(max_relay * 2, 20))),
            "relay_last5": (f"RELAY LOG (last {max_relay})", lambda: read_relay_log(max_relay)),
            "financial_pulse": ("FINANCIAL PULSE", read_financial_pulse),
            "active_fare_watches": ("FARE WATCHES", read_fare_watches),
            "git_status_short": ("GIT STATUS", read_git_status_short),
            "tess_status": ("TESS AUTH", read_tess_status),
            "pins": ("PINNED ITEMS", lambda: self.pins.format_pins(pin_limit)),
        }

        for section_key in sections:
            if section_key not in section_map:
                continue
            title, reader = section_map[section_key]
            content = reader()
            if content and content.strip() and "(unavailable)" not in content and "(no active" not in content:
                parts.append(f"\n── {title} ──\n{content}")

        parts.append("\n════════════════════════════════════════════════")
        brief = "\n".join(parts)

        # Log calibration
        self._log_calibration(persona, estimate_tokens(brief))
        return brief

    def status(self) -> str:
        cal = load_json(CALIBRATION_FILE, {"calls": []})
        calls = cal.get("calls", [])
        lines = [f"Context Sniper Status — {now_utc()}"]
        lines.append(f"  Policy file: {CONFIG_FILE}")
        lines.append(f"  Pins active: {len(self.pins.active_pins())}")
        lines.append(f"  Calibration calls: {len(calls)}")
        if calls:
            recent = calls[-5:]
            lines.append("  Recent calls:")
            for c in recent:
                lines.append(f"    {c.get('ts','')} persona={c.get('persona','?')} brief_tokens≈{c.get('brief_tokens',0)}")

        # Persona policies available
        lines.append("\n  Available personas:")
        for name, p in self.policies.get("personas", {}).items():
            lines.append(f"    {name}: {p.get('description','')}")

        return "\n".join(lines)

    def _log_calibration(self, persona: str, brief_tokens: int):
        cal = load_json(CALIBRATION_FILE, {"calls": []})
        cal["calls"].append({
            "ts": now_utc(),
            "persona": persona,
            "brief_tokens": brief_tokens,
        })
        # Keep last 100 entries
        cal["calls"] = cal["calls"][-100:]
        save_json(CALIBRATION_FILE, cal)


# ── CLI Entry Point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Context Sniper — Token Budget Foreman")
    sub = parser.add_subparsers(dest="cmd")

    # brief
    p_brief = sub.add_parser("brief", help="Build context brief for a persona")
    p_brief.add_argument("--persona", default="default", help="hale | sterling | intel | harlan | dani | default")
    p_brief.add_argument("--hint", default="", help="Optional hint about current task")

    # status
    sub.add_parser("status", help="Show Context Sniper status and calibration stats")

    # pin
    p_pin = sub.add_parser("pin", help="Add a pin (never-drop item)")
    p_pin.add_argument("item", help="The item text to pin")
    p_pin.add_argument("--category", default="critical", help="critical | plan | instruction | fact")

    # pins
    sub.add_parser("pins", help="List active pins")

    # unpin
    p_unpin = sub.add_parser("unpin", help="Remove a pin by ID")
    p_unpin.add_argument("pin_id", type=int, help="Pin ID to remove")

    # calibrate
    sub.add_parser("calibrate", help="Show calibration stats")

    args = parser.parse_args()

    sniper = ContextSniper()

    if args.cmd == "brief":
        print(sniper.build_brief(args.persona, args.hint))
    elif args.cmd == "status":
        print(sniper.status())
    elif args.cmd == "pin":
        pin = sniper.pins.add(args.item, args.category)
        print(f"✅ Pinned #{pin['id']} [{pin['category']}]: {pin['item']}")
    elif args.cmd == "pins":
        pins = sniper.pins.active_pins()
        if not pins:
            print("No active pins.")
        else:
            print(f"{len(pins)} active pins:")
            for p in pins:
                print(f"  #{p['id']} [{p['category']}] {p['item']}")
    elif args.cmd == "unpin":
        if sniper.pins.remove(args.pin_id):
            print(f"✅ Unpinned #{args.pin_id}")
        else:
            print(f"❌ Pin #{args.pin_id} not found")
    elif args.cmd == "calibrate":
        cal = load_json(CALIBRATION_FILE, {"calls": []})
        calls = cal.get("calls", [])
        print(f"Calibration log: {len(calls)} calls")
        by_persona = {}
        for c in calls:
            p = c.get("persona", "?")
            by_persona.setdefault(p, []).append(c.get("brief_tokens", 0))
        for p, tokens in by_persona.items():
            avg = sum(tokens) // len(tokens)
            print(f"  {p}: {len(tokens)} calls, avg brief ≈ {avg} tokens")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
