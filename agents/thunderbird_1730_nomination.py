"""
Thunderbird 1730 Nomination Ping
Dreams2Memories Travel, LLC · A7 Sterling build · 2026-06-10

Fires at 1730 MT via systemd timer. Sends a Telegram message to Commander
notifying tonight's incubator sectors and gate candidate. Commander can
redirect or cancel via Telegram before 1800 EOD brief fires.

Send-only design: does NOT poll getUpdates (Telegram gateway is running
and owns the polling loop). This script writes to eod_incubator_config.json
to record any pre-wired redirect, and the 1800 EOD brief reads that config.

Usage:
  python3 agents/thunderbird_1730_nomination.py          # Normal send
  python3 agents/thunderbird_1730_nomination.py --dry-run # Print message, no send

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
LOG_PATH = THUNDERBIRD_DIR / "logs" / "1730_nomination.log"

TG_BASE = "https://api.telegram.org/bot{token}/{method}"
COMMANDER_ID = 7554895206

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

def build_nomination_message(cfg: dict) -> str:
    sectors = cfg.get("sectors_tonight", [])
    gate = cfg.get("gate_candidate")
    execute_window = cfg.get("execute_window_minutes", 5)
    nomination_time = cfg.get("nomination_time", "17:30")

    sector_str = " &middot; ".join(sectors) if sectors else "TBD"

    gate_line = ""
    if gate:
        gate_line = (
            f"\nGate candidate: <b>{gate.get('name','?')}</b> "
            f"&rarr; {gate.get('owner','?')} build"
        )
    else:
        gate_line = "\nGate: No candidate nominated tonight"

    msg = (
        f"&#x1F985; <b>1730</b> &mdash; Tonight's sectors: {sector_str}"
        f"{gate_line}\n"
        f"Executing in {execute_window} unless redirected."
    )
    return msg


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Thunderbird 1730 Nomination Ping")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print message to stdout only, do not send")
    args = parser.parse_args()

    (THUNDERBIRD_DIR / "logs").mkdir(exist_ok=True)

    # Load config
    cfg = {}
    try:
        if EOD_CONFIG_PATH.exists():
            cfg = json.loads(EOD_CONFIG_PATH.read_text())
    except Exception as e:
        logger.warning(f"eod_incubator_config read failed (using defaults): {e}")

    # Build message
    msg = build_nomination_message(cfg)
    logger.info(f"Nomination message: {msg[:200]}")

    if args.dry_run:
        print("=== DRY RUN — would send to Commander ===")
        # Strip HTML for readable dry-run output
        import re
        plain = re.sub(r"<[^>]+>", "", msg).replace("&middot;", "·").replace("&rarr;", "→")
        print(plain)
        return

    if not TOKEN_D2MC2C:
        logger.error("TELEGRAM_D2MC2C_TOKEN not available. Nomination not sent.")
        sys.exit(1)

    success = tg_send(TOKEN_D2MC2C, COMMANDER_ID, msg)
    if success:
        logger.info("1730 nomination ping sent to Commander")
        # Stamp config with send time
        try:
            cfg["last_nomination_sent"] = datetime.utcnow().isoformat()
            EOD_CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
        except Exception:
            pass
    else:
        logger.error("1730 nomination ping FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
