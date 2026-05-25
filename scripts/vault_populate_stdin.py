#!/usr/bin/env python3
"""
Vault populate — stdin-only credential entry.
Reads KEY=VALUE pairs from stdin, validates against vault keys,
writes to .env.vault. Never writes to stdout, logs, or temp files.

Usage:
    python3 scripts/vault_populate_stdin.py
    (paste KEY=VALUE lines, then press Ctrl+D)

Security:
- chmod 600 enforced on .env.vault on every write
- No intermediate files written
- No logging of values (only key names logged)
"""
import os
import sys
from pathlib import Path

VAULT_PATH = Path(__file__).parent.parent / ".env.vault"

VALID_KEYS = {
    "D2M_VAULT_VERSION",
    "D2M_VAULT_POPULATED_AT",
    "D2M_TESS_AGENT_USERNAME",
    "D2M_TESS_AGENT_PASSWORD",
    "D2M_TESS_JWT_ACCESS_TOKEN",
    "D2M_TESS_JWT_REFRESH_TOKEN",
    "D2M_TESS_JWT_EXPIRES_AT",
    "D2M_TESS_AGENT_USER_ID",
    "D2M_ODYSSEUS_CDP_SESSION_FILE",
    "D2M_TLN_AU_USERNAME",
    "D2M_TLN_AU_PASSWORD",
    "D2M_TLN_CC_USERNAME",
    "D2M_TLN_CC_PASSWORD",
    "D2M_TLN_CC_LOGIN_URL",
}


def load_vault() -> tuple[list, dict]:
    """Load existing vault entries, preserving comments."""
    lines = []
    values = {}
    if VAULT_PATH.exists():
        for line in VAULT_PATH.read_text().splitlines():
            lines.append(line)
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, _, v = stripped.partition("=")
                values[k.strip()] = v.strip()
    return lines, values


def write_vault(lines: list, values: dict) -> None:
    """Write vault, applying updated values, enforce chmod 600."""
    out = []
    written_keys = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _, _ = stripped.partition("=")
            k = k.strip()
            written_keys.add(k)
            if k in values:
                out.append(f"{k}={values[k]}")
            else:
                out.append(line)
        else:
            out.append(line)
    for k, v in values.items():
        if k not in written_keys:
            out.append(f"{k}={v}")
    VAULT_PATH.write_text("\n".join(out) + "\n")
    os.chmod(VAULT_PATH, 0o600)


def main():
    print("Vault populate — paste KEY=VALUE lines, then press Ctrl+D:", file=sys.stderr)
    lines, existing = load_vault()
    updates = {}
    rejected = []
    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line or raw_line.startswith("#"):
            continue
        if "=" not in raw_line:
            rejected.append(raw_line)
            continue
        k, _, v = raw_line.partition("=")
        k = k.strip()
        if k not in VALID_KEYS:
            rejected.append(k)
            print(f"  UNKNOWN KEY (skipped): {k}", file=sys.stderr)
            continue
        updates[k] = v.strip()
        print(f"  Accepted: {k}", file=sys.stderr)  # key name only, never value

    if not updates:
        print("No valid keys entered. Vault unchanged.", file=sys.stderr)
        sys.exit(0)

    existing.update(updates)
    write_vault(lines, existing)
    print(f"\nVault updated: {len(updates)} key(s) written. chmod 600 enforced.", file=sys.stderr)
    if rejected:
        print(f"Rejected (unknown): {rejected}", file=sys.stderr)


if __name__ == "__main__":
    main()
