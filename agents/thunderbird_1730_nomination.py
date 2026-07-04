"""
Thunderbird 1730 Nomination Ping
Dreams2Memories Travel, LLC · A7 Sterling build · 2026-06-10

Fires at 1730 MT via systemd timer. Sends a Telegram message to Commander
notifying tonight's incubator sectors and gate candidate. Commander can
redirect or cancel via Telegram before 1800 EOD brief fires.

Send-only design: does NOT poll getUpdates (Telegram gateway is running
and owns the polling loop). This script writes to eod_incubator_config.json
to record tonight's plan (sectors + gate tracking); the 1800 EOD brief reads
that config so the ping and the EOD brief stay coherent.

Per-day send-lock: OpsCenter/nomination_sent_YYYYMMDD.lock (MT date) — mirrors
thunderbird_eod_brief.py. Sends at most once per calendar day (edge-triggered,
not level-triggered — the message no longer re-fires on catch-up/off-schedule runs).

Usage:
  python3 agents/thunderbird_1730_nomination.py          # Normal send
  python3 agents/thunderbird_1730_nomination.py --dry-run # Print message, no send
  python3 agents/thunderbird_1730_nomination.py --force   # Ignore send-lock

Systemd timer: thunderbird-1730-nomination.timer (1730 MT daily)
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

# CLAUDE.md EOD doctrine: "10 sectors A–J ... Rotate 3/night". This overrides the
# config's stale rotation_count_per_night (2) — doctrine is the source of truth.
NIGHTLY_SECTOR_COUNT = 3

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
# SEND LOCK — OpsCenter/nomination_sent_YYYYMMDD.lock
# ---------------------------------------------------------------------------

def _lock_path(date_str: str) -> Path:
    return LOCK_DIR / f"nomination_sent_{date_str.replace('-', '')}.lock"


def _lock_exists(date_str: str) -> bool:
    return _lock_path(date_str).exists()


def _write_lock(date_str: str) -> None:
    p = _lock_path(date_str)
    p.write_text(json.dumps({"date": date_str, "sent_at": datetime.utcnow().isoformat()}))
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
# TONIGHT'S SECTORS — deterministic daily rotation over rotation_sectors
# ---------------------------------------------------------------------------

def select_tonight_sectors(cfg: dict, ref_date) -> list:
    """Pick NIGHTLY_SECTOR_COUNT sectors from rotation_sectors.

    Deterministic daily-advancing window: same set for a given date, advances
    each night, cycles through the whole pool. Draws only from rotation_sectors
    (the two permanent_sectors — LLM & AI APIs, Agentic Apps — run every night
    per config posture and are not part of the nightly *nomination* rotation).
    """
    rotation = cfg.get("rotation_sectors", [])
    if not rotation:
        return []
    count = min(NIGHTLY_SECTOR_COUNT, len(rotation))
    doy = ref_date.timetuple().tm_yday
    start = (doy * count) % len(rotation)
    return [rotation[(start + i) % len(rotation)] for i in range(count)]


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

def build_nomination_message(sectors: list, gate, gate_fresh: bool,
                             execute_window: int = 5) -> str:
    sector_str = " &middot; ".join(sectors) if sectors else "TBD"

    if gate and gate_fresh:
        gate_line = (
            f"\nGate candidate: <b>{gate.get('name','?')}</b> "
            f"&rarr; {gate.get('owner','?')} build"
        )
    else:
        gate_line = "\nGate: No new candidate tonight"

    msg = (
        f"&#x1F985; <b>1730</b> &mdash; Tonight's sectors: {sector_str}"
        f"{gate_line}\n"
        f"Executing in {execute_window} min unless redirected."
    )
    return msg


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Thunderbird 1730 Nomination Ping")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print message to stdout only, do not send")
    parser.add_argument("--force", action="store_true",
                        help="Ignore per-day send-lock (testing only)")
    args = parser.parse_args()

    (THUNDERBIRD_DIR / "logs").mkdir(exist_ok=True)

    date_str = _mt_date_str()
    ref_date = _mt_now().date()

    cfg = _load_config()
    execute_window = cfg.get("execute_window_minutes", 5)

    # ── Tonight's plan of record (sectors + gate tracking) ───────────────────
    # Written to config regardless of send so the 1800 EOD brief, which reads the
    # same file, stays coherent with this ping. Idempotent for a given date.
    sectors = select_tonight_sectors(cfg, ref_date)
    gate_fresh, gate_updates = evaluate_gate(cfg, date_str)
    gate = cfg.get("gate_candidate")

    cfg["sectors_tonight"] = sectors
    cfg.update(gate_updates)
    if not args.dry_run:
        _write_config(cfg)

    # ── Build message ────────────────────────────────────────────────────────
    msg = build_nomination_message(sectors, gate, gate_fresh, execute_window)
    logger.info(f"Nomination message: {msg[:200]}")

    if args.dry_run:
        print("=== DRY RUN — would send to Commander ===")
        import re
        plain = (re.sub(r"<[^>]+>", "", msg)
                 .replace("&middot;", "·").replace("&rarr;", "→"))
        print(plain)
        print(f"\n[sectors_tonight={sectors} | gate_fresh={gate_fresh}]")
        return

    # ── Per-day send-lock ────────────────────────────────────────────────────
    if not args.force and _lock_exists(date_str):
        logger.info(f"Nomination send-lock exists for {date_str} — already sent today. Exiting.")
        return

    if not TOKEN_D2MC2C:
        logger.error("TELEGRAM_D2MC2C_TOKEN not available. Nomination not sent.")
        sys.exit(1)

    success = tg_send(TOKEN_D2MC2C, COMMANDER_ID, msg)
    if success:
        logger.info("1730 nomination ping sent to Commander")
        cfg["last_nomination_sent"] = datetime.utcnow().isoformat()
        _write_config(cfg)
        _write_lock(date_str)
    else:
        logger.error("1730 nomination ping FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
