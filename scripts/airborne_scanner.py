#!/usr/bin/env python3
"""
AIRBORNE SCANNER — the collection deck (rides on Phase-0 guards)
===============================================================
Dreams2Memories Travel · built 2026-06-21 (MISSION-325 · wing-designed)

The wing turned "always-on satellite bird" into a heartbeat-monitored daily
PULSE with a three-gate pipe. This is that pulse — lethal-and-small:

  COLLECT (dumb, cheap, free)  — 3 rotating sectors of our 10; reuse the proven
      harvester fetch (real sources, $0, no LLM). Every lead → holding queue,
      tagged WATCH/UNKNOWN. Cheap NEVER promotes its own findings.
  TRIAGE (mechanical rule, no model) — a lead survives only if it hits a sector
      keyword AND clears materiality AND is NEW (dedup vs seen-set). Hype dies here.
  ADJUDICATE — NOT done here. Survivors sit in the holding queue as WATCH for
      HALE (the strong reasoner + designated consumer: "all inputs to YOU") to
      adversarially kill/confirm in her loop, then promote to the bus. Cheap
      collects, strong kills.

Every pulse: cost-checked PRE-call ($5/day kill) + heartbeats the dead-man's
switch (zero/frozen = ALARM). A pulse that dies can't hide as "quiet."

State: state/scanner_holding.jsonl · state/scanner_rotation.json · state/scanner.enabled
Run:   python3 scripts/airborne_scanner.py pulse
       python3 scripts/airborne_scanner.py holding   # what's waiting for Hale
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))
HOLDING = ROOT / "state" / "scanner_holding.jsonl"
ROTATION = ROOT / "state" / "scanner_rotation.json"
SEEN = ROOT / "state" / "scanner_seen.json"
ENABLED = ROOT / "state" / "scanner.enabled"

# The 10 capability / search areas + the keywords that say a lead is IN that area.
SECTORS = [
    ("claude-code",   ["claude code", "cc skill", "hook", "subagent", "slash command", "output style", "plugin"]),
    ("agentic",       ["agent", "multi-agent", "orchestrat", "swarm", "harness", "autonomous", "loop"]),
    ("mcp",           ["mcp", "model context protocol", "mcp server"]),
    ("ai-writing",    ["writing", "copy", "tone", "brand voice", "ghostwrit", "style transfer"]),
    ("travel-b2b",    ["travel", "cruise", "fare", "itinerary", "gds", "booking", "hotel", "airfare"]),
    ("competitor",    ["concierge", "travel agenc", "advisor", "luxury travel", "ai travel"]),
    ("automation",    ["automation", "n8n", "workflow", "no-code", "scheduler", "zapier", "cron"]),
    ("llm",           ["model", "llm", "gpt", "gemini", "claude", "deepseek", "qwen", "context window", "tokens"]),
    ("browser",       ["scrap", "browser", "anti-bot", "playwright", "camoufox", "stealth", "captcha", "imperva"]),
    ("voice",         ["voice", "speech", "tts", "stt", "phone", "telephony", "sms", "whatsapp", "telegram"]),
]
MATERIALITY_MINLEN = 18   # a title shorter than this is noise


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_sectors(n: int = 3) -> list[tuple[str, list[str]]]:
    idx = 0
    if ROTATION.exists():
        try:
            idx = json.loads(ROTATION.read_text()).get("idx", 0)
        except Exception:
            idx = 0
    picked = [SECTORS[(idx + i) % len(SECTORS)] for i in range(n)]
    ROTATION.parent.mkdir(parents=True, exist_ok=True)
    ROTATION.write_text(json.dumps({"idx": (idx + n) % len(SECTORS), "ts": _now()}))
    return picked


def _seen() -> set:
    if SEEN.exists():
        try:
            return set(json.loads(SEEN.read_text()))
        except Exception:
            return set()
    return set()


def _save_seen(s: set) -> None:
    SEEN.write_text(json.dumps(sorted(s)[-5000:]))  # cap memory


def _collect() -> list[dict]:
    """Reuse the proven harvester fetch — real sources, $0, no LLM. Returns leads."""
    import api.thunderbird_power_harvest as h
    leads = []
    for src in h.SOURCES:
        content = h._fetch_url(src["url"]) if src["type"] == "url" else h._fetch_feed(src)
        if not content:
            continue
        # feed content is already newline 'Title — url' lines; url content is raw text
        for line in content.splitlines():
            line = line.strip()
            if line:
                leads.append({"source": src["name"], "text": line[:240]})
    return leads


def _triage(leads: list[dict], sectors: list[tuple[str, list[str]]], seen: set) -> list[dict]:
    survivors = []
    for ld in leads:
        low = ld["text"].lower()
        if len(ld["text"]) < MATERIALITY_MINLEN:
            continue
        for name, kws in sectors:
            if any(k in low for k in kws):
                key = hashlib.sha1((name + "|" + low[:120]).encode()).hexdigest()[:16]
                if key in seen:
                    break
                seen.add(key)
                survivors.append({"sector": name, "text": ld["text"], "source": ld["source"],
                                  "key": key, "status": "WATCH", "confidence": "UNKNOWN", "ts": _now()})
                break
    return survivors


def pulse() -> dict:
    from core.ai_infra import scanner_guards as g
    # PRE-call cost kill (free fetch ~ $0, but enforce the gate as the standing pattern)
    ok, detail = g.can_spend("free-fetch", 0.0)
    if not ok:
        print("ABORT — " + detail)
        return {"aborted": True, "reason": detail}

    sectors = _next_sectors(3)
    seen = _seen()
    leads = _collect()
    survivors = _triage(leads, sectors, seen)
    _save_seen(seen)

    # holding queue (WATCH/UNKNOWN) — for Hale to adjudicate
    HOLDING.parent.mkdir(parents=True, exist_ok=True)
    with open(HOLDING, "a", encoding="utf-8") as fh:
        for s in survivors:
            fh.write(json.dumps(s) + "\n")

    # heartbeat (dead-man's switch) + spend record
    content_hash = hashlib.sha1("|".join(sorted(s["key"] for s in survivors)).encode()).hexdigest()
    g.record_pulse(len(survivors), content_hash, sectors=[n for n, _ in sectors])
    g.record_spend("free-fetch", 0.0, tokens=0)

    print(f"PULSE {_now()}: sectors={[n for n,_ in sectors]} | leads={len(leads)} | "
          f"NEW survivors→holding={len(survivors)} (WATCH/UNKNOWN, awaiting Hale adjudication)")
    return {"sectors": [n for n, _ in sectors], "leads": len(leads), "survivors": len(survivors)}


def holding() -> None:
    if not HOLDING.exists():
        print("holding queue empty"); return
    rows = [json.loads(l) for l in HOLDING.read_text().splitlines() if l.strip()]
    watch = [r for r in rows if r.get("status") == "WATCH"]
    print(f"HOLDING QUEUE — {len(watch)} WATCH item(s) awaiting Hale adjudication:")
    for r in watch[-30:]:
        print(f"  [{r['sector']:11}] {r['text'][:90]}  ({r['source']})")


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pulse")
    sub.add_parser("holding")
    sub.add_parser("arm")  # write the scanner.enabled marker (arms the watchdog)
    args = ap.parse_args()
    if args.cmd == "pulse":
        pulse()
    elif args.cmd == "holding":
        holding()
    elif args.cmd == "arm":
        ENABLED.parent.mkdir(parents=True, exist_ok=True)
        ENABLED.write_text(f"armed {_now()}\n")
        print(f"ARMED — {ENABLED} written; dead-man's switch now enforces liveness")
    return 0


if __name__ == "__main__":
    sys.exit(main())
