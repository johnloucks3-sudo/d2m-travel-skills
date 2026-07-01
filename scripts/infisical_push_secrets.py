#!/usr/bin/env python3
"""
infisical_push_secrets.py — migrate Wing secrets from .env into self-hosted Infisical.
M5 / SO_TOTAL_CI. Non-client by default; --include-client after Commander canary waiver.

Bootstrap (one-time, at a browser — Infisical is UI-first):
  1. http://localhost:8899  → create admin account (first visit).
  2. Create a project (e.g. "thunderbird"), note its Project ID (Settings).
  3. Create a Machine Identity (or Service Token) with write access → copy the token.

Run:
  .venv/bin/python scripts/infisical_push_secrets.py --token <TOKEN> --project-id <ID> --env prod
  # add --include-client to also push the 4 client-path secrets (canary WAIVED 2026-07-01)
  # --dry-run to preview classification without pushing

Safety: this only WRITES secrets into Infisical. It does NOT repoint any code away
from .env — file-based creds remain the live source until repoint is done separately
and verified (so nothing breaks mid-migration).
"""
from __future__ import annotations
import argparse, json, sys, urllib.request
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
ENV = ROOT / ".env"
INF_BASE = "http://localhost:8899"

CLIENT_MARKERS = ("GMAIL", "TESS", "CENTRAV", "REGENT", "RSSC", "JOHNLOUCKS", "CONCIERGE",
                  "PERX", "ROOM_RES", "AMADEUS", "LYONS", "CLIENT", "BOOKING")
# Non-secret config noise to skip entirely.
SKIP = ("PATH", "DIR", "URL", "HOST", "PORT", "ENABLED", "MODE", "DEBUG", "COLORTERM",
        "PROXY", "NO_PROXY", "CA_BUNDLE", "CERT_FILE", "ROUTE_ALL", "DISABLE_AUTH",
        "APPLICATION_CREDENTIALS")


def classify() -> tuple[dict, dict]:
    non_client, client = {}, {}
    for line in ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if not k or not v or any(s in k.upper() for s in SKIP):
            continue
        (client if any(m in k.upper() for m in CLIENT_MARKERS) else non_client)[k] = v
    return non_client, client


def push(token: str, project_id: str, env_slug: str, secrets: dict) -> int:
    ok = 0
    for k, v in secrets.items():
        try:
            body = {"secretValue": v, "secretComment": "migrated from .env by Wing M5",
                    "type": "shared", "workspaceId": project_id, "environment": env_slug}
            req = urllib.request.Request(
                f"{INF_BASE}/api/v3/secrets/raw/{k}",
                data=json.dumps(body).encode(), method="POST",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=15)
            ok += 1
            print(f"[push] {k}")
        except Exception as e:
            print(f"[push] {k}: FAILED {str(e)[:80]}", file=sys.stderr)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token"); ap.add_argument("--project-id")
    ap.add_argument("--env", default="prod", help="Infisical environment slug")
    ap.add_argument("--include-client", action="store_true", help="Also push client-path secrets (canary waived)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    non_client, client = classify()
    print(f"NON-CLIENT: {len(non_client)}  |  CLIENT-PATH: {len(client)}")
    if args.dry_run:
        print("\nNON-CLIENT keys:", ", ".join(sorted(non_client)))
        print("\nCLIENT-PATH keys:", ", ".join(sorted(client)))
        print("\n(dry-run — nothing pushed)")
        return

    if not args.token or not args.project_id:
        print("Provide --token and --project-id (see docstring for bootstrap).", file=sys.stderr)
        sys.exit(2)

    batch = dict(non_client)
    if args.include_client:
        batch.update(client)
        print(f"[canary WAIVED] including {len(client)} client-path secrets")

    pushed = push(args.token, args.project_id, args.env, batch)
    print(f"\nDONE — {pushed}/{len(batch)} secrets in Infisical. .env remains live source until repoint+verify.")


if __name__ == "__main__":
    main()
