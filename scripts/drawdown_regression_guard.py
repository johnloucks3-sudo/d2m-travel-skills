#!/usr/bin/env python3
"""
drawdown_regression_guard.py — "guard dog" for the Claude-MAX drawdown
containment checkpoints set 2026-08-02. See claude-drawdown skill
(~/.claude/skills/claude-drawdown/) for the general template this was
deployed from.

Checks that the 3 containment fixes (opencode.json default model,
agent_runner.py run_opencode model, Telegram C2 engine redirect) are still
in place. Alert-only — never auto-reverts.
"""
import json
import sys
from pathlib import Path

# ── CONFIG — Thunderbird deploy (restored 2026-08-05 from pyc disassembly) ─
CHECKPOINTS_FILE = Path("/home/john/Thunderbird/scripts/drawdown_checkpoints.json")
ROOT = Path("/home/john/Thunderbird")
ALERT_LOG = ROOT / "logs" / "drawdown_regression_guard.log"
TELEGRAM_TOKEN_ENV_FILE = ROOT / ".env.telegram"
TELEGRAM_TOKEN_VAR = "TELEGRAM_D2MC2C_TOKEN"
TELEGRAM_CHAT_ID_VAR = "TELEGRAM_COMMANDER_ID"
TELEGRAM_CHAT_ID_DEFAULT = "7554895206"
# ──────────────────────────────────────────────────────────────────────────


def log(msg: str) -> None:
    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ALERT_LOG.open("a") as f:
        f.write(f"{msg}\n")
    print(msg)


def send_telegram(msg: str) -> None:
    try:
        import os
        import urllib.request
        import urllib.parse

        if TELEGRAM_TOKEN_ENV_FILE.exists():
            for line in TELEGRAM_TOKEN_ENV_FILE.read_text().splitlines():
                if line.startswith(f"{TELEGRAM_TOKEN_VAR}="):
                    os.environ[TELEGRAM_TOKEN_VAR] = line.split("=", 1)[1].strip()
        token = os.environ.get(TELEGRAM_TOKEN_VAR, "")
        chat_id = os.environ.get(TELEGRAM_CHAT_ID_VAR, TELEGRAM_CHAT_ID_DEFAULT)
        if not token or not chat_id:
            log("Telegram send skipped — no token/chat_id configured")
            return
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": msg}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        log(f"Telegram send failed (non-fatal): {e!r}")


def main() -> None:
    if not CHECKPOINTS_FILE.exists():
        log(f"No checkpoints file at {CHECKPOINTS_FILE}")
        return

    checkpoints = json.loads(CHECKPOINTS_FILE.read_text())
    drifted = []
    missing_files = []

    for cp in checkpoints:
        path = Path(cp["file"])
        if not path.exists():
            missing_files.append(cp)
            continue
        content = path.read_text(errors="replace")
        if cp["must_contain"] not in content:
            drifted.append(cp)

    if not drifted and not missing_files:
        log(f"All {len(checkpoints)} containment checkpoint(s) holding.")
        return

    lines = []
    for cp in drifted:
        lines.append(f"DRIFTED: {cp['file']} — expected to still contain: "
                     f"{cp['must_contain']!r} ({cp.get('description', '')})")
    for cp in missing_files:
        lines.append(f"FILE MISSING: {cp['file']} ({cp.get('description', '')})")

    msg = ("🐕 Drawdown regression guard — containment checkpoint(s) no "
           "longer holding:\n" + "\n".join(lines) +
           "\n\nSomething reverted a drawdown fix. If intentional, that's "
           "fine — just know the Claude-MAX-default leak this drawdown "
           "fixed may be back if it wasn't.")
    log(msg)
    send_telegram(msg)


if __name__ == "__main__":
    sys.exit(main() or 0)