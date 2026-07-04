#!/usr/bin/env python3
"""
triage_client_inquiry_noise.py — clean newsletter/promo/self-send pollution
from the mission board's "Client inquiry" backlog.

Root problem (2026-07-01): the inbox classifier tagged newsletters, promos,
political blasts, and the Commander's OWN self-sent briefings as
"client_inquiry", flooding the board (326 open) and feeding the 4h mission
executor, which auto-drafted junk "seek clarification" replies while genuine
client emails went unanswered.

CONSERVATIVE by design:
  - Archives ONLY definitive non-client mail:
      (a) sender matches the canonical _NOISE_PATTERNS from
          core/email/thunderbird_commander_inbox.py, OR
      (b) sender domain/handle is in EXTENDED_PROMO (obvious newsletters/promos
          the narrow regex missed), OR
      (c) sender is johnloucks3@gmail.com (self-send / internal brief — never a
          client inquiry by definition).
  - KEEPS everything else (personal gmail/yahoo, unknown senders) for human
    review — so real, unanswered client emails are never lost.

Reversible: sets status -> "archived_noise" (does not delete). A timestamped
board backup is expected to be taken by the caller before --apply.

Usage:
  python3 scripts/triage_client_inquiry_noise.py            # dry-run (default)
  python3 scripts/triage_client_inquiry_noise.py --apply    # mutate the board
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "OpsCenter" / "mission_board.json"
sys.path.insert(0, str(ROOT / "core" / "email"))
from thunderbird_commander_inbox import _NOISE_PATTERNS  # canonical filter

# Obvious newsletter/promo/political senders the narrow regex missed.
EXTENDED_PROMO = re.compile(
    r"(newsmax|dunkin|arbys|@costco|\.costco\.|anytimefitness|condenast|"
    r"rocketmoney|allrecipes|pointsguy|cruisecritic|teapartypatriots|"
    r"claremont\.org|spacewarfare|pwrmobile|exploringtwdc|justthenews|"
    r"jacquielawson|@apify\.com|wellamoon\.com|"
    r"@campaigns\.|@emails?\.|@email\.|@eml\.|@latest\.|@digital\.|"
    r"@emailinfo\.|@info\.)",
    re.IGNORECASE,
)
SELF_SENDS = {"johnloucks3@gmail.com"}

DONE = {"done", "complete", "completed", "closed", "cancelled",
        "archived_noise", "closed_noise"}


def sender_of(m: dict) -> str:
    txt = str(m.get("description", "")) + " " + str(m.get("title", ""))
    mm = re.search(r"<([^>]+@[^>]+)>", txt)
    return mm.group(1).lower() if mm else ""


def reason(sender: str) -> str | None:
    if not sender:
        return None
    if sender in SELF_SENDS:
        return "self_send_internal"
    if _NOISE_PATTERNS.search(sender):
        return "canonical_noise"
    if EXTENDED_PROMO.search(sender):
        return "extended_promo"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="mutate the board")
    args = ap.parse_args()

    board = json.loads(BOARD.read_text())
    missions = board.get("missions", []) if isinstance(board, dict) else board

    archive, keep = [], []
    for m in missions:
        if not isinstance(m, dict):
            continue
        if "client inquiry" not in str(m.get("title", "")).lower():
            continue
        if str(m.get("status", "")).lower() in DONE:
            continue
        s = sender_of(m)
        why = reason(s)
        if why:
            archive.append((m, s, why))
        else:
            keep.append((m, s))

    print(f"OPEN client-inquiry missions: {len(archive) + len(keep)}")
    print(f"  -> ARCHIVE (definitive non-client): {len(archive)}")
    print(f"  -> KEEP for human review: {len(keep)}")
    print("\n=== KEPT (candidate REAL client / unknown — review these) ===")
    for m, s in keep:
        print(f"  {m.get('id'):<14} {s or '(no sender)':<42} {str(m.get('title',''))[:50]}")

    if not args.apply:
        print("\n[DRY-RUN] no changes written. Re-run with --apply to archive.")
        return

    ts = datetime.now(timezone.utc).isoformat()
    ids = set()
    for m, s, why in archive:
        m["status"] = "archived_noise"
        m.setdefault("notes", [])
        if isinstance(m["notes"], list):
            m["notes"].append(f"[{ts}] archived_noise ({why}, sender={s}) — "
                              f"triage_client_inquiry_noise.py")
        ids.add(m.get("id"))
    BOARD.write_text(json.dumps(board, indent=2, ensure_ascii=False))
    print(f"\n[APPLIED] {len(ids)} missions -> archived_noise. "
          f"{len(keep)} kept for review.")


if __name__ == "__main__":
    main()
