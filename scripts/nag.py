#!/usr/bin/env python3
"""
nag.py — Nag queue CLI for Commander.

Usage:
    python3 scripts/nag.py list
    python3 scripts/nag.py clear <id_or_client>        e.g. clear NAG-001 | clear McLeod
    python3 scripts/nag.py add <client> <embark_date> [order_deadline] [label] [note]
    python3 scripts/nag.py status                      # one-line summary for AM brief
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

TB = Path("/home/john/Thunderbird")
NAG_FILE = TB / "OpsCenter" / "nag_queue.json"


def load():
    try:
        return json.loads(NAG_FILE.read_text())
    except Exception:
        return {"nags": []}


def save(data):
    NAG_FILE.parent.mkdir(parents=True, exist_ok=True)
    NAG_FILE.write_text(json.dumps(data, indent=2))


def next_id(data):
    ids = [n.get("id", "NAG-000") for n in data.get("nags", [])]
    nums = [int(i.split("-")[1]) for i in ids if i.startswith("NAG-")]
    return f"NAG-{(max(nums) + 1):03d}" if nums else "NAG-001"


def urgency_label(days: int) -> str:
    if days < 0:   return f"🔴🔴 OVERDUE {abs(days)}d"
    if days == 0:  return "🔴🔴 DUE TODAY"
    if days <= 2:  return f"🔴 T-{days} CRITICAL"
    if days <= 7:  return f"🟠 T-{days} URGENT"
    if days <= 14: return f"🟡 T-{days}"
    return             f"🔵 T-{days}"


def cmd_list(data):
    nags = data.get("nags", [])
    if not nags:
        print("Nag queue: empty")
        return
    today = date.today()
    print(f"\n{'ID':<10} {'STATUS':<10} {'CLIENT':<12} {'LABEL':<30} {'URGENCY'}")
    print("─" * 90)
    for n in nags:
        dl = n.get("order_deadline") or n.get("embark_date", "")
        try:
            days = (date.fromisoformat(dl) - today).days
            urg = urgency_label(days) if n.get("status") != "CLEARED" else "✅ CLEARED"
        except Exception:
            urg = "?"
        print(f"{n.get('id','?'):<10} {n.get('status','?'):<10} {n.get('client','?'):<12} "
              f"{n.get('label','?')[:30]:<30} {urg}")
    print()


def cmd_clear(data, target: str):
    target_lower = target.lower()
    matched = []
    for n in data.get("nags", []):
        if (n.get("id", "").lower() == target_lower or
                target_lower in n.get("client", "").lower() or
                target_lower in n.get("label", "").lower()):
            matched.append(n)

    if not matched:
        print(f"No nag found matching '{target}'. Use 'list' to see IDs.")
        return

    for n in matched:
        if n.get("status") == "CLEARED":
            print(f"  {n['id']} ({n['client']}) — already CLEARED")
        else:
            n["status"] = "CLEARED"
            n["cleared_date"] = date.today().isoformat()
            print(f"  ✅ CLEARED: {n['id']} — {n['label']} ({n['client']})")

    save(data)


def cmd_add(args):
    # args: client embark_date [order_deadline] [label] [note]
    if len(args) < 2:
        print("Usage: nag add <client> <embark_date_YYYY-MM-DD> [order_deadline] [label] [note]")
        return
    data = load()
    client = args[0]
    embark_str = args[1]
    try:
        embark = date.fromisoformat(embark_str)
    except ValueError:
        print(f"Invalid date: {embark_str} — use YYYY-MM-DD")
        return

    # Default order deadline = E-30
    if len(args) >= 3 and "-" in args[2]:
        try:
            deadline_str = date.fromisoformat(args[2]).isoformat()
        except Exception:
            deadline_str = (embark - timedelta(days=30)).isoformat()
    else:
        deadline_str = (embark - timedelta(days=30)).isoformat()

    label = args[3] if len(args) >= 4 else f"{client} Embarkation Gift"
    note  = args[4] if len(args) >= 5 else "Arrange in-suite amenity or gift by order deadline."

    nag = {
        "id": next_id(data),
        "client": client,
        "type": "embarkation_gift",
        "label": label,
        "embark_date": embark_str,
        "order_deadline": deadline_str,
        "mission_id": "",
        "status": "OPEN",
        "note": note,
        "created": date.today().isoformat(),
        "cleared_date": None,
    }
    data.setdefault("nags", []).append(nag)
    save(data)
    print(f"✅ Added {nag['id']}: {label}")
    print(f"   Client: {client} | Embark: {embark_str} | Order by: {deadline_str}")


def cmd_status(data):
    """One-line summary for AM brief injection."""
    today = date.today()
    open_nags = [n for n in data.get("nags", []) if n.get("status") != "CLEARED"]
    if not open_nags:
        print("NAG QUEUE: clear")
        return
    for n in open_nags:
        dl = n.get("order_deadline") or n.get("embark_date", "")
        try:
            days = (date.fromisoformat(dl) - today).days
            urg = urgency_label(days)
        except Exception:
            urg = "?"
        print(f"{urg} — {n['client']}: {n['label']} | order by {dl} | {n.get('note','')[:60]}")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("list", "ls"):
        cmd_list(load())
    elif args[0] == "clear" and len(args) >= 2:
        cmd_clear(load(), " ".join(args[1:]))
    elif args[0] == "add" and len(args) >= 3:
        cmd_add(args[1:])
    elif args[0] == "status":
        cmd_status(load())
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
