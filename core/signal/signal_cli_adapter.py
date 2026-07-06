"""Signal CLI adapter — thin wrapper over the signal-cli JVM binary.

signal-cli links as a SECONDARY DEVICE to Commander's existing Signal account
(719-291-0742, per Personas/hale_cos.md Channel Registry — "linked to YOGA").
Once linked, this process can read every message that arrives on Commander's
Signal account and send messages that appear to come from that same number —
this is how a linked device works, not a separate bot identity.

Binary: vendor/signal-cli-0.14.5 (JVM build — no native-lib/glibc dependency,
works on any Linux with a JRE). Installed 2026-07-06, no sudo required.

Device linking is a ONE-TIME HUMAN-ONLY STEP (QR/URI scan in the Signal app) —
the only genuine wall in this integration. Every function here degrades
gracefully (returns a structured "not_linked" result) until that step is done,
per the Obstacle-Routing Protocol: build everything up to the human wall,
then surface exactly one concrete, executable ask.
"""
import json
import subprocess
from pathlib import Path
from typing import Optional

ROOT = Path("/home/john/Thunderbird")
SIGNAL_CLI_BIN = ROOT / "vendor" / "signal-cli-0.14.5" / "bin" / "signal-cli"
CONFIG_DIR = ROOT / "config" / "signal-cli"
COMMANDER_NUMBER = "+17192910742"  # 719-291-0742, per hale_cos.md Channel Registry

CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _run(args: list[str], timeout: int = 30, input_text: Optional[str] = None) -> subprocess.CompletedProcess:
    cmd = [str(SIGNAL_CLI_BIN), "--config", str(CONFIG_DIR)] + args
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, input=input_text,
    )


def is_linked() -> bool:
    """True once Commander's number is registered as a linked account locally.

    Cheapest local check: signal-cli stores per-account state under
    CONFIG_DIR/data/<number> once linking succeeds. No network call needed
    for a plain existence check.
    """
    return (CONFIG_DIR / "data" / COMMANDER_NUMBER).exists()


def link_device(device_name: str = "Hale D2M") -> dict:
    """Start the linked-device flow. Returns the tsdevice:/ URI for Commander
    to scan (Signal app -> Linked Devices -> Link New Device).

    THIS IS THE ONE HUMAN-ONLY STEP IN THE ENTIRE SIGNAL INTEGRATION.
    Everything else in this module works unattended once this completes.
    """
    if is_linked():
        return {"status": "already_linked", "number": COMMANDER_NUMBER}

    try:
        proc = subprocess.Popen(
            [str(SIGNAL_CLI_BIN), "--config", str(CONFIG_DIR), "link", "-n", device_name],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        uri = None
        for line in proc.stdout:
            line = line.strip()
            if line.startswith("sgnl://") or line.startswith("tsdevice:"):
                uri = line
                break
        return {
            "status": "link_pending",
            "uri": uri,
            "human_action_required": (
                "Open Signal on your phone -> Settings -> Linked Devices -> "
                "Link New Device -> scan the URI above (render it as a QR code, "
                "e.g. `qrencode` or any online QR generator, or open the URI "
                "directly if scanning isn't available)."
            ),
            "pid": proc.pid,
        }
    except FileNotFoundError:
        return {"status": "error", "error": f"signal-cli binary not found at {SIGNAL_CLI_BIN}"}


def send_message(to: str, message: str) -> dict:
    """Send `message` to `to` (E.164 number) as Commander's linked Signal identity."""
    if not is_linked():
        return {"status": "not_linked", "error": "Run link_device() and complete the human linking step first."}
    try:
        proc = _run(["-a", COMMANDER_NUMBER, "send", "-m", message, to], timeout=20)
        if proc.returncode == 0:
            return {"status": "sent", "to": to, "stdout": proc.stdout.strip()}
        return {"status": "error", "returncode": proc.returncode, "stderr": proc.stderr.strip()}
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "send timed out"}


def receive_messages(timeout: int = 5) -> list[dict]:
    """Poll for new incoming messages. Returns a list of
    {"source": str, "timestamp": int, "message": str} dicts (empty if none)."""
    if not is_linked():
        return []
    try:
        proc = _run(["-a", COMMANDER_NUMBER, "receive", "-t", str(timeout), "--json"], timeout=timeout + 10)
    except subprocess.TimeoutExpired:
        return []

    out = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            envelope = json.loads(line).get("envelope", {})
        except json.JSONDecodeError:
            continue
        data_msg = envelope.get("dataMessage")
        if not data_msg or not data_msg.get("message"):
            continue
        out.append({
            "source": envelope.get("sourceNumber") or envelope.get("source"),
            "timestamp": envelope.get("timestamp"),
            "message": data_msg["message"],
        })
    return out
