#!/usr/bin/env python3
"""
M-292 — Cloudflare Agent-Identity Monitor.

Daily Anansi scan of Cloudflare's developer/blog surface for signals that
CF has shipped (beta/GA) an ephemeral-identity / agent-identity capability
that could replace Imperva (~$3.6K/yr saving per Harlan). Fires a Telegram
page to the Commander on a fresh hit, and gates the Imperva spend decision
until CF ships.

Trigger keywords (case-insensitive):
  - "agent identity"
  - "ephemeral credential" / "ephemeral credentials"
  - "zero trust agent"
  - "agent credentials"
  - "service token" + "agent"   (co-occurrence)

Dedup: hits are fingerprinted (url + matched-keyword) and stored in
OpsCenter/.cf_agent_identity_dedup.json — a keyword already paged on a page
is not re-paged.

Usage:
  python3 scripts/cf_agent_identity_monitor.py            # scan + page on new hit
  python3 scripts/cf_agent_identity_monitor.py --dry-run  # scan, print, no page
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ANANSI = str(ROOT / ".venv" / "bin" / "anansi")
DEDUP_PATH = ROOT / "OpsCenter" / ".cf_agent_identity_dedup.json"
LOG_PATH = ROOT / "logs" / "cf_agent_identity_monitor.log"

# CF surfaces to scan — blog index + developer-platform changelog
SCAN_URLS = [
    "https://blog.cloudflare.com/tag/zero-trust/",
    "https://blog.cloudflare.com/tag/ai/",
    "https://developers.cloudflare.com/changelog/",
]

KEYWORDS = [
    r"agent identit",          # agent identity / identities
    r"ephemeral credential",   # singular/plural
    r"zero[- ]trust agent",
    r"agent credential",
]
# Co-occurrence signal: service token discussed in an agent context
COOCCUR = (r"service token", r"agent")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(f"{_now()} {msg}\n")
    print(msg, flush=True)


def fetch(url: str) -> str:
    """Fetch a URL as markdown via Anansi. Returns '' on failure (logged)."""
    try:
        res = subprocess.run(
            [ANANSI, "fetch", "--output", "markdown", url],
            capture_output=True, text=True, timeout=120,
        )
        if res.returncode != 0:
            _log(f"[fetch] non-zero rc {res.returncode} for {url}: {res.stderr[:160]}")
            return ""
        return res.stdout or ""
    except Exception as e:
        _log(f"[fetch] error for {url}: {e}")
        return ""


def scan_text(url: str, text: str) -> list[dict]:
    """Return list of {url, keyword, excerpt} hits."""
    hits = []
    low = text.lower()
    for kw in KEYWORDS:
        for m in re.finditer(kw, low):
            start = max(0, m.start() - 80)
            end = min(len(text), m.end() + 80)
            hits.append({
                "url": url,
                "keyword": kw,
                "excerpt": text[start:end].replace("\n", " ").strip(),
            })
            break  # one hit per keyword per page is enough to page
    # co-occurrence
    if re.search(COOCCUR[0], low) and re.search(COOCCUR[1], low):
        hits.append({
            "url": url,
            "keyword": "service token + agent (co-occurrence)",
            "excerpt": "",
        })
    return hits


def fingerprint(hit: dict) -> str:
    return hashlib.sha256(f"{hit['url']}|{hit['keyword']}".encode()).hexdigest()[:16]


def load_dedup() -> set:
    if DEDUP_PATH.exists():
        try:
            return set(json.loads(DEDUP_PATH.read_text()).get("seen", []))
        except Exception:
            return set()
    return set()


def save_dedup(seen: set) -> None:
    DEDUP_PATH.write_text(json.dumps({"seen": sorted(seen), "updated": _now()}, indent=2))


def page_commander(new_hits: list[dict]) -> bool:
    from OpsCenter.thunderbird_telegram_gw import TOKEN_D2MC2C, COMMANDER_ID, tg_send
    lines = [
        "⚡ <b>CF AGENT-IDENTITY SIGNAL</b>",
        "",
        "Cloudflare may have shipped ephemeral/agent identity — could replace Imperva (~$3.6K/yr per Harlan).",
        "",
    ]
    for h in new_hits[:6]:
        kw = h["keyword"]
        lines.append(f"• <b>{kw}</b>\n  {h['url']}")
        if h.get("excerpt"):
            lines.append(f"  <i>…{h['excerpt'][:140]}…</i>")
    lines.append("")
    lines.append("<b>Action:</b> Verify beta/GA → Sterling eval vs Imperva spend gate.")
    text = "\n".join(lines)
    try:
        return tg_send(TOKEN_D2MC2C, COMMANDER_ID, text, parse_mode="HTML")
    except Exception as e:
        _log(f"[page] send failed: {e}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Scan + print, no Telegram page, no dedup write")
    args = ap.parse_args()

    _log(f"=== CF agent-identity scan start ({'DRY' if args.dry_run else 'LIVE'}) ===")
    all_hits = []
    for url in SCAN_URLS:
        text = fetch(url)
        if not text:
            continue
        page_hits = scan_text(url, text)
        all_hits.extend(page_hits)
        _log(f"[scan] {url} -> {len(page_hits)} hit(s)")

    if not all_hits:
        _log("No keyword hits. Imperva spend gate stays closed (CF not shipped).")
        return 0

    seen = load_dedup()
    new_hits = [h for h in all_hits if fingerprint(h) not in seen]

    if args.dry_run:
        _log(f"DRY: {len(all_hits)} total hits, {len(new_hits)} new (would page if live):")
        for h in new_hits:
            _log(f"  NEW {h['keyword']} @ {h['url']}")
        return 0

    if not new_hits:
        _log(f"{len(all_hits)} hit(s) but all previously paged — no new signal.")
        return 0

    ok = page_commander(new_hits)
    if ok:
        for h in new_hits:
            seen.add(fingerprint(h))
        save_dedup(seen)
        _log(f"PAGED Commander on {len(new_hits)} new hit(s); dedup updated.")
    else:
        _log("Page failed — NOT updating dedup so next run retries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
