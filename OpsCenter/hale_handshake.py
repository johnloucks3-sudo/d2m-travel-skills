"""HALE Handshake Protocol — shared state between ALPHA (OpenCode) and BRAVO (Claude).
Append-only JSONL. Both instances write on open, close, decision, and divergence.
Optionally notifies D2M C2 Telegram channel on open/close.

Usage:
    python3 hale_handshake.py open [--note "..."] [--notify]
    python3 hale_handshake.py close [--note "..."] [--notify]
    python3 hale_handshake.py status
    python3 hale_handshake.py divergence --question "..." --alpha-answer "..." --bravo-answer "..."
"""
import json, sys, os, time, argparse, re
from pathlib import Path
from datetime import datetime, timezone

HANDSHAKE_FILE = Path(__file__).parent / "hale_handshake.jsonl"
DIVERGENCE_FILE = Path(__file__).parent / "hale_divergence_log.jsonl"
DOTENV = Path(__file__).parent.parent / ".env"
INSTANCE = os.environ.get("HALE_INSTANCE", "alpha")
MODEL = os.environ.get("HALE_MODEL", "opencode/deepseek-v4-flash-free")


def _load_env_token():
    if DOTENV.exists():
        text = DOTENV.read_text()
        m = re.search(r'TELEGRAM_BOT_TOKEN=([^\s"\']+)', text)
        if m:
            return m.group(1).strip().strip("'\"").strip('"')
    return os.environ.get("TELEGRAM_BOT_TOKEN")


def _send_telegram(msg):
    token = _load_env_token()
    if not token:
        return False
    try:
        import requests
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": 7554895206, "text": msg, "parse_mode": "Markdown"},
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def _read_last(fpath=None):
    fpath = fpath or HANDSHAKE_FILE
    if not fpath.exists():
        return None
    with open(fpath) as f:
        lines = [l for l in f if l.strip()]
    return json.loads(lines[-1]) if lines else None


def _append(packet, fpath=None):
    fpath = fpath or HANDSHAKE_FILE
    fpath.parent.mkdir(parents=True, exist_ok=True)
    with open(fpath, "a") as f:
        f.write(json.dumps(packet, default=str) + "\n")


def _fmt_list(items):
    return "\n".join(f"• {i}" for i in (items or [])[:5])


def cmd_open(note=None, notify=False):
    last = _read_last()
    packet = {
        "protocol": "HALE-HANDSHAKE/v1",
        "instance": INSTANCE,
        "model": MODEL,
        "event": "open",
        "opened_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closed_at": None,
        "note": note,
        "previous_session": {
            "instance": last.get("instance") if last else None,
            "opened_at": last.get("opened_at") if last else None,
            "state_summary": last.get("state_summary") if last else None,
        } if last else None,
        "state_summary": {
            "decisions_made": [],
            "files_modified": [],
            "commander_data_received": [],
            "outstanding_requests": [],
        },
    }
    _append(packet)
    print(json.dumps(packet, indent=2))
    if notify:
        instance_label = "HALE ALPHA" if INSTANCE == "alpha" else "HALE BRAVO"
        msg = f"🟢 **{instance_label} ONLINE**\nModel: {MODEL}\nNote: {note or '—'}"
        if last:
            msg += f"\nPrevious: {last.get('instance','?')} — {last.get('event','?')}"
        ok = _send_telegram(msg)
        print(f"Telegram notify: {'✅' if ok else '❌'}")
    return packet


def cmd_close(note=None, decisions=None, files=None, commander_data=None, requests=None, notify=False):
    last = _read_last()
    if not (last and last.get("event") == "open" and last.get("instance") == INSTANCE):
        # Allow close even without matching open (write a close packet anyway for handoff)
        packet = {
            "protocol": "HALE-HANDSHAKE/v1",
            "instance": INSTANCE,
            "model": MODEL,
            "event": "close",
            "opened_at": None,
            "closed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "handoff_note": note,
            "state_summary": {
                "decisions_made": decisions or [],
                "files_modified": files or [],
                "commander_data_received": commander_data or [],
                "outstanding_requests": requests or [],
            },
        }
        _append(packet)
        print(json.dumps(packet, indent=2))
    else:
        last["event"] = "close"
        last["closed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        last["handoff_note"] = note
        last["state_summary"] = {
            "decisions_made": decisions or [],
            "files_modified": files or [],
            "commander_data_received": commander_data or [],
            "outstanding_requests": requests or [],
        }
        _append(last)
        print(json.dumps(last, indent=2))

    if notify:
        instance_label = "HALE ALPHA" if INSTANCE == "alpha" else "HALE BRAVO"
        msg = f"🔴 **{instance_label} EOD**\nNote: {note or '—'}"
        if decisions:
            msg += f"\n\nDecisions:\n{_fmt_list(decisions)}"
        if requests:
            msg += f"\n\nRequests:\n{_fmt_list(requests)}"
        ok = _send_telegram(msg)
        print(f"Telegram notify: {'✅' if ok else '❌'}")
    return last or packet


def cmd_divergence(question, alpha_answer, bravo_answer, notify=False):
    """Log a divergence — same question, different answers across instances."""
    packet = {
        "protocol": "HALE-HANDSHAKE/v1",
        "event": "divergence",
        "logged_by": INSTANCE,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "question": question,
        "alpha_answer": alpha_answer,
        "bravo_answer": bravo_answer,
        "resolution": None,
    }
    _append(packet, DIVERGENCE_FILE)
    # Also append to main handshake
    _append({**packet, "divergence_file": str(DIVERGENCE_FILE)})
    print(json.dumps(packet, indent=2))
    print(f"Logged to {DIVERGENCE_FILE.name} + handshake")

    if notify:
        msg = (
            f"⚡ **HALE DIVERGENCE DETECTED**\n\n"
            f"Question: {question[:100]}\n"
            f"ALPHA: {alpha_answer[:200]}\n"
            f"BRAVO: {bravo_answer[:200]}"
        )
        ok = _send_telegram(msg)
        print(f"Telegram notify: {'✅' if ok else '❌'}")
    return packet


def cmd_status():
    last = _read_last()
    if last:
        state = "open" if last.get("event") == "open" else "closed"
        print(f"Last: {last.get('instance','?')} ({last.get('model','?')}) — {state} @ {last.get('opened_at','?')}")
        print(json.dumps(last.get("state_summary", {}), indent=2))
    else:
        print("No handshake entries found.")

    divergences = 0
    if DIVERGENCE_FILE.exists():
        with open(DIVERGENCE_FILE) as f:
            divergences = sum(1 for l in f if l.strip())
    print(f"Divergences logged: {divergences}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(prog="hale_handshake")
    p.add_argument("action", choices=["open", "close", "status", "divergence"])
    p.add_argument("--note", help="Session note or handoff message")
    p.add_argument("--decisions", nargs="*", help="Decisions made this session")
    p.add_argument("--files", nargs="*", help="Files modified this session")
    p.add_argument("--commander-data", nargs="*", help="Data received from Commander")
    p.add_argument("--requests", nargs="*", help="Outstanding requests")
    p.add_argument("--notify", action="store_true", help="Send Telegram notification")
    p.add_argument("--question", help="Divergence: the question asked")
    p.add_argument("--alpha-answer", help="Divergence: ALPHA's answer")
    p.add_argument("--bravo-answer", help="Divergence: BRAVO's answer")
    args = p.parse_args()

    if args.action == "open":
        cmd_open(note=args.note, notify=args.notify)
    elif args.action == "close":
        cmd_close(note=args.note, decisions=args.decisions, files=args.files,
                  commander_data=args.commander_data, requests=args.requests,
                  notify=args.notify)
    elif args.action == "divergence":
        if not all([args.question, args.alpha_answer, args.bravo_answer]):
            print("ERROR: divergence requires --question, --alpha-answer, --bravo-answer")
            sys.exit(1)
        cmd_divergence(args.question, args.alpha_answer, args.bravo_answer, notify=args.notify)
    else:
        cmd_status()
