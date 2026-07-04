"""
Thunderbird Nomination Ping — 2x/day, 12h apart, half the sector list each time
Dreams2Memories Travel, LLC · A7 Sterling build · 2026-06-10, split 2026-07-04

Fires TWICE daily, 12h apart (0530 and 1730 MT) via two systemd timers. Each
fire covers HALF of rotation_sectors — together the two halves give total
daily coverage of every rotation sector, instead of the old slow multi-night
rotation (3/night out of 7 took days to cycle through). permanent_sectors
run on every fire regardless of half (unchanged — they're not part of the split).

Commander directive 2026-07-04: "I want 2 a day 12 hours apart firing 1/2 the
list each time so we get total coverage."

Send-only design: does NOT poll getUpdates (Telegram gateway is running
and owns the polling loop). This script writes to eod_incubator_config.json
to record the plan (sectors + gate tracking); the 1800 EOD brief reads
that config so the pings and the EOD brief stay coherent. sectors_tonight
accumulates across the day: after the AM half fires it holds half 1 only;
after the PM half fires it holds both halves — full coverage, verifiable by
the 1800 EOD brief.

Per-day-per-half send-lock: OpsCenter/nomination_sent_YYYYMMDD_half{N}.lock —
each half sends at most once per calendar day (edge-triggered), but the day
now allows 2 sends total (one per half), not 1.

Usage:
  python3 agents/thunderbird_1730_nomination.py --half 1       # AM half (0530)
  python3 agents/thunderbird_1730_nomination.py --half 2       # PM half (1730)
  python3 agents/thunderbird_1730_nomination.py --half 1 --dry-run
  python3 agents/thunderbird_1730_nomination.py --half 1 --force  # ignore lock

Systemd timers: thunderbird-nomination-half1.timer (0530 MT),
                thunderbird-nomination-half2.timer (1730 MT)
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# BOOTSTRAP
# ---------------------------------------------------------------------------
THUNDERBIRD_DIR = Path(__file__).parent.parent

for _p in [THUNDERBIRD_DIR, THUNDERBIRD_DIR / "OpsCenter"]:
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
EOD_CONFIG_PATH = THUNDERBIRD_DIR / "OpsCenter" / "eod_incubator_config.json"
LOCK_DIR = THUNDERBIRD_DIR / "OpsCenter"
LOG_PATH = THUNDERBIRD_DIR / "logs" / "1730_nomination.log"

TG_BASE = "https://api.telegram.org/bot{token}/{method}"
COMMANDER_ID = 7554895206

# SUPERSEDED 2026-07-04: old doctrine was "10 sectors A-J ... Rotate 3/night"
# (slow multi-night cycle). Commander directive 2026-07-04 replaces this with
# 2 fires/day, 12h apart, half the rotation_sectors list each — see
# split_sectors() / select_sectors_for_half() below. Total daily coverage,
# not a rotating sample.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOG_PATH), mode="a"),
    ],
)
logger = logging.getLogger("thunderbird_1730_nomination")


# ---------------------------------------------------------------------------
# ENV LOADER (replicates gateway pattern to ensure token is available)
# ---------------------------------------------------------------------------

def _load_env_file(path: str) -> None:
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
    except FileNotFoundError:
        pass


_load_env_file(str(THUNDERBIRD_DIR / ".env"))
_load_env_file(str(THUNDERBIRD_DIR / "config" / "telegram_gw.env"))

TOKEN_D2MC2C = os.environ.get("TELEGRAM_D2MC2C_TOKEN", "")


# ---------------------------------------------------------------------------
# TIMEZONE + DATE HELPERS (mirror thunderbird_eod_brief.py)
# ---------------------------------------------------------------------------

def _mt_now() -> datetime:
    try:
        import zoneinfo
        return datetime.now(tz=zoneinfo.ZoneInfo("America/Denver"))
    except Exception:
        return datetime.utcnow().replace(tzinfo=timezone.utc)


def _mt_date_str() -> str:
    return _mt_now().strftime("%Y-%m-%d")


def _days_between(d1_str: str, d2_str: str) -> int:
    """Absolute whole-day gap between two YYYY-MM-DD(...) strings. 0 on parse error."""
    try:
        d1 = datetime.strptime(str(d1_str)[:10], "%Y-%m-%d").date()
        d2 = datetime.strptime(str(d2_str)[:10], "%Y-%m-%d").date()
        return abs((d2 - d1).days)
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# SEND LOCK — OpsCenter/nomination_sent_YYYYMMDD_half{N}.lock (per half, per day)
# ---------------------------------------------------------------------------

def _lock_path(date_str: str, half: int) -> Path:
    return LOCK_DIR / f"nomination_sent_{date_str.replace('-', '')}_half{half}.lock"


def _lock_exists(date_str: str, half: int) -> bool:
    return _lock_path(date_str, half).exists()


def _write_lock(date_str: str, half: int) -> None:
    p = _lock_path(date_str, half)
    p.write_text(json.dumps({"date": date_str, "half": half, "sent_at": datetime.utcnow().isoformat()}))
    logger.info(f"Nomination send-lock written: {p}")


# ---------------------------------------------------------------------------
# CONFIG I/O
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    try:
        if EOD_CONFIG_PATH.exists():
            return json.loads(EOD_CONFIG_PATH.read_text())
    except Exception as e:
        logger.warning(f"eod_incubator_config read failed (using defaults): {e}")
    return {}


def _write_config(cfg: dict) -> None:
    try:
        EOD_CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    except Exception as e:
        logger.warning(f"eod_incubator_config write failed: {e}")


# ---------------------------------------------------------------------------
# SECTOR SPLIT — half the rotation_sectors list per fire, full coverage per day
# ---------------------------------------------------------------------------

def split_sectors(cfg: dict) -> tuple[list, list]:
    """Fixed halving of rotation_sectors — half 1 (first ceil(n/2)), half 2
    (remainder). Not date-rotating: the point of 2 fires/day 12h apart is
    that BOTH halves run every single day, giving total coverage of every
    rotation sector daily rather than a slow multi-night cycle."""
    rotation = cfg.get("rotation_sectors", [])
    if not rotation:
        return [], []
    mid = -(-len(rotation) // 2)  # ceil division
    return rotation[:mid], rotation[mid:]


def select_sectors_for_half(cfg: dict, half: int) -> list:
    """Return the sector list for this fire's half (1 = AM/0530, 2 = PM/1730)."""
    half1, half2 = split_sectors(cfg)
    return half1 if half == 1 else half2


# ---------------------------------------------------------------------------
# GATE CANDIDATE STALENESS — edge-triggered (fire once when it changes)
# ---------------------------------------------------------------------------

def _gate_fingerprint(gate: dict) -> str:
    return f"{gate.get('name','')}|{gate.get('owner','')}|{gate.get('status','')}"


def evaluate_gate(cfg: dict, today_str: str):
    """Decide whether tonight's gate_candidate is *fresh* enough to surface.

    A gate is surfaced only when it is genuinely new (its fingerprint changed)
    or first seen within the last day. Once it has sat unchanged for >1 day it
    stops re-appearing in the ping as if it were new (the 2026-06-19 frozen-gate
    bug). Non-destructive: the gate_candidate itself is never cleared here — it is
    consumed by the 1800 EOD brief, so nulling it at 1730 would drop an approved,
    un-built gate.

    Returns (is_fresh: bool, tracking_updates: dict) — the updates persist the
    fingerprint + first-seen date so the edge-trigger holds across runs.
    """
    gate = cfg.get("gate_candidate")
    if not gate:
        return False, {}

    fp = _gate_fingerprint(gate)
    tracked_fp = cfg.get("_gate_fingerprint")

    if fp != tracked_fp:
        # Never tracked before: seed first_seen from last_updated so a pre-existing
        # frozen gate ages correctly instead of looking brand-new. Otherwise the
        # fingerprint genuinely changed → it's new tonight.
        first_seen = cfg.get("last_updated", today_str) if tracked_fp is None else today_str
    else:
        first_seen = cfg.get("_gate_first_seen") or cfg.get("last_updated", today_str)

    is_fresh = _days_between(first_seen, today_str) <= 1
    return is_fresh, {"_gate_fingerprint": fp, "_gate_first_seen": first_seen}


# ---------------------------------------------------------------------------
# TELEGRAM SEND (send-only — no getUpdates poll; gateway owns that loop)
# ---------------------------------------------------------------------------

def tg_send(token: str, chat_id: int, text: str) -> bool:
    """Send a single Telegram message. Returns True on success."""
    if not token:
        logger.error("TELEGRAM_D2MC2C_TOKEN not set — cannot send nomination ping")
        return False
    if len(text) > 4096:
        text = text[:4090] + "\n..."
    url = TG_BASE.format(token=token, method="sendMessage")
    try:
        r = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=20,
        )
        data = r.json()
        if data.get("ok"):
            return True
        else:
            logger.warning(f"Telegram sendMessage error: {data.get('description','?')}")
            return False
    except Exception as e:
        logger.error(f"Telegram send exception: {e}")
        return False


# ---------------------------------------------------------------------------
# BUILD NOMINATION MESSAGE
# ---------------------------------------------------------------------------

def build_nomination_message(sectors: list, gate, gate_fresh: bool, half: int,
                             full_day_sectors: list, execute_window: int = 5) -> str:
    sector_str = " &middot; ".join(sectors) if sectors else "TBD"
    slot_label = "0530 (half 1/2)" if half == 1 else "1730 (half 2/2)"

    if gate and gate_fresh:
        gate_line = (
            f"\nGate candidate: <b>{gate.get('name','?')}</b> "
            f"&rarr; {gate.get('owner','?')} build"
        )
    else:
        gate_line = "\nGate: No new candidate tonight"

    coverage_line = ""
    if half == 2:
        coverage_line = f"\nToday's full coverage (both halves): {' &middot; '.join(full_day_sectors)}"

    msg = (
        f"&#x1F985; <b>{slot_label}</b> &mdash; This slot's sectors: {sector_str}"
        f"{coverage_line}"
        f"{gate_line}\n"
        f"Executing in {execute_window} min unless redirected."
    )
    return msg


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Thunderbird Nomination Ping (half-split, 2x/day)")
    parser.add_argument("--half", type=int, choices=[1, 2], required=True,
                        help="Which half of rotation_sectors this fire covers (1=0530, 2=1730)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print message to stdout only, do not send")
    parser.add_argument("--force", action="store_true",
                        help="Ignore per-day-per-half send-lock (testing only)")
    args = parser.parse_args()

    (THUNDERBIRD_DIR / "logs").mkdir(exist_ok=True)

    date_str = _mt_date_str()

    cfg = _load_config()
    execute_window = cfg.get("execute_window_minutes", 5)

    # ── This slot's sectors + gate tracking ──────────────────────────────────
    # Written to config regardless of send so the 1800 EOD brief, which reads the
    # same file, stays coherent. sectors_tonight ACCUMULATES across the day:
    # half 1 (0530) sets it to half 1 only; half 2 (1730) unions in half 2, so by
    # EOD-brief time (1800) it reflects verified full-day coverage of both halves.
    sectors = select_sectors_for_half(cfg, args.half)
    gate_fresh, gate_updates = evaluate_gate(cfg, date_str)
    gate = cfg.get("gate_candidate")

    prior_tonight = cfg.get("sectors_tonight", []) if cfg.get("sectors_tonight_date") == date_str else []
    full_day_sectors = list(dict.fromkeys(prior_tonight + sectors))  # union, order-preserving

    cfg["sectors_tonight"] = full_day_sectors
    cfg["sectors_tonight_date"] = date_str
    cfg[f"sectors_half{args.half}_sent_date"] = date_str
    cfg.update(gate_updates)
    if not args.dry_run:
        _write_config(cfg)

    # ── Build message ────────────────────────────────────────────────────────
    msg = build_nomination_message(sectors, gate, gate_fresh, args.half, full_day_sectors, execute_window)
    logger.info(f"Nomination message (half {args.half}): {msg[:200]}")

    if args.dry_run:
        print("=== DRY RUN — would send to Commander ===")
        import re
        plain = (re.sub(r"<[^>]+>", "", msg)
                 .replace("&middot;", "·").replace("&rarr;", "→"))
        print(plain)
        print(f"\n[half={args.half} sectors={sectors} | full_day_sectors={full_day_sectors} | gate_fresh={gate_fresh}]")
        return

    # ── Per-day-per-half send-lock ───────────────────────────────────────────
    if not args.force and _lock_exists(date_str, args.half):
        logger.info(f"Nomination send-lock exists for {date_str} half {args.half} — already sent. Exiting.")
        return

    if not TOKEN_D2MC2C:
        logger.error("TELEGRAM_D2MC2C_TOKEN not available. Nomination not sent.")
        sys.exit(1)

    success = tg_send(TOKEN_D2MC2C, COMMANDER_ID, msg)
    if success:
        logger.info(f"Nomination ping (half {args.half}) sent to Commander")
        cfg["last_nomination_sent"] = datetime.utcnow().isoformat()
        _write_config(cfg)
        _write_lock(date_str, args.half)
    else:
        logger.error(f"Nomination ping (half {args.half}) FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
