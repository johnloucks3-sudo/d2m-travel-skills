"""Signal <-> other-channel relay — the cross-channel exception path.

Per docs/HALE_COMMS_ARCHITECTURE_PLAN_v1.md: "If a message arrives on an
unavailable channel and requires urgent response, Hale may notify Commander
on the available channel." Signal is the newest, least-proven channel, so
this module's only job is: if Signal can't complete a send (not linked yet,
signal-cli crashes, network blip), don't lose the message — surface it on
Telegram, which is the proven bridge channel per CLAUDE.md Channel Registry.

Deliberately one-directional (Signal-failure -> Telegram) and read-only with
respect to Telegram/email internals — this module does not attempt to also
relay Telegram/email traffic onto Signal. Signal stays Commander-only,
Hale-only, no fan-out (locked Commander decision, hale_cos.md).
"""
import subprocess
from pathlib import Path

TELEGRAM_GW = Path("/home/john/Thunderbird/OpsCenter/thunderbird_telegram_gw.py")


def notify_telegram_fallback(text: str) -> dict:
    """Best-effort notification on Telegram when Signal can't be used.
    Mirrors the exact fallback pattern already used in
    core/email/agentmail_listener.py._notify_telegram — same bridge, same
    failure tolerance (best-effort, never raises).
    """
    try:
        proc = subprocess.run(
            ["python3", str(TELEGRAM_GW), "--relay", text[:3900], "--source", "Signal"],
            timeout=15, capture_output=True, text=True,
        )
        return {"status": "sent" if proc.returncode == 0 else "error", "returncode": proc.returncode}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def relay_link_pending_notice(link_result: dict) -> dict:
    """When link_device() returns a pending link (the one human-only step),
    push the exact ask to Telegram immediately rather than letting it sit in
    a log file — this is the ONE concrete, executable ask the whole
    integration produces (Obstacle-Routing Protocol)."""
    if link_result.get("status") != "link_pending":
        return {"status": "skipped", "reason": "not a link_pending result"}
    uri = link_result.get("uri", "(no URI captured)")
    text = (
        "SIGNAL LINK NEEDED — one-time human step: open Signal on your phone -> "
        "Settings -> Linked Devices -> Link New Device -> scan this URI "
        f"(render as QR if scanning text directly isn't supported): {uri}"
    )
    return notify_telegram_fallback(text)
