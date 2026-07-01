#!/usr/bin/env python3
"""CI probe — Tailscale mesh VPN.
Efficacy check: tailscaled.service active (system unit) + tailscale CLI reports
BackendState=Running with at least 1 peer connected.
Exit 0 = GREEN, exit 1 = RED.
"""
import subprocess
import sys
import json
import shutil

ID = "tailscale"
MIN_PEERS = 1
TAILSCALE_BIN = "/usr/bin/tailscale"


def fail(m):
    print(f"RED {ID}: {m}")
    sys.exit(1)


def check_daemon():
    """Verify tailscaled.service (system unit) is active — no --user flag."""
    r = subprocess.run(
        ["systemctl", "is-active", "tailscaled.service"],
        capture_output=True, text=True, timeout=10
    )
    if r.stdout.strip() != "active":
        fail(f"tailscaled.service not active (state={r.stdout.strip()!r})")


def check_status():
    """Verify BackendState=Running and peer count >= MIN_PEERS."""
    binary = TAILSCALE_BIN if shutil.which(TAILSCALE_BIN) else shutil.which("tailscale")
    if not binary:
        fail("tailscale CLI binary not found")

    r = subprocess.run(
        [binary, "status", "--json"],
        capture_output=True, text=True, timeout=15
    )
    if r.returncode != 0:
        fail(f"tailscale status --json failed (rc={r.returncode}): {r.stderr.strip()}")

    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError as e:
        fail(f"Could not parse tailscale status JSON: {e}")

    backend = data.get("BackendState", "")
    if backend != "Running":
        fail(f"BackendState={backend!r} (expected 'Running')")

    peers = data.get("Peer", {})
    peer_count = len(peers)
    if peer_count < MIN_PEERS:
        fail(f"Only {peer_count} peer(s) connected (need >= {MIN_PEERS})")

    self_hostname = data.get("Self", {}).get("HostName", "unknown")
    return backend, peer_count, self_hostname


def main():
    check_daemon()
    backend, peer_count, hostname = check_status()
    print(f"GREEN {ID}: tailscaled active, BackendState={backend}, {peer_count} peer(s), self={hostname}")
    sys.exit(0)


if __name__ == "__main__":
    main()
