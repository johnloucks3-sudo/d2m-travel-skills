#!/usr/bin/env python3
"""
infisical_client.py — Wing secret reader backed by self-hosted Infisical.
M5 / SO_TOTAL_CI. Kills the silent-credential-death class: secrets live in
Infisical (expiry-aware, rotatable) with .env as a safety fallback so a repoint
never breaks the Wing mid-migration.

Usage:
    from core.secrets.infisical_client import get_secret
    token = get_secret("TELEGRAM_BOT_TOKEN")        # Infisical → .env fallback

Auth: durable Universal Auth (clientId+secret) in deploy/free_tools/.infisical_runtime
(gitignored). Access tokens cached in-process for their TTL.
"""
from __future__ import annotations
import json, os, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
RUNTIME = ROOT / "deploy" / "free_tools" / ".infisical_runtime"

_cfg: dict | None = None
_token: str | None = None
_token_exp: float = 0.0
_cache: dict[str, str] = {}


def _load_cfg() -> dict:
    global _cfg
    if _cfg is None:
        _cfg = {}
        if RUNTIME.exists():
            for line in RUNTIME.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    _cfg[k.strip()] = v.strip()
    return _cfg


def _login() -> str | None:
    global _token, _token_exp
    if _token and time.time() < _token_exp - 60:
        return _token
    c = _load_cfg()
    cid, cs, base = c.get("INFISICAL_CLIENT_ID"), c.get("INFISICAL_CLIENT_SECRET"), c.get("INFISICAL_URL")
    if not (cid and cs and base):
        return None
    try:
        req = urllib.request.Request(f"{base}/api/v1/auth/universal-auth/login",
            data=json.dumps({"clientId": cid, "clientSecret": cs}).encode(),
            method="POST", headers={"Content-Type": "application/json"})
        j = json.loads(urllib.request.urlopen(req, timeout=10).read())
        _token = j.get("accessToken")
        _token_exp = time.time() + int(j.get("expiresIn", 2592000))
        return _token
    except Exception:
        return None


def get_secret(name: str, default: str | None = None, fallback_env: bool = True) -> str | None:
    """Fetch a secret from Infisical; fall back to os.environ (then default)."""
    if name in _cache:
        return _cache[name]
    c = _load_cfg()
    tok = _login()
    if tok:
        try:
            url = (f"{c['INFISICAL_URL']}/api/v3/secrets/raw/{name}"
                   f"?workspaceId={c['INFISICAL_PROJECT_ID']}&environment={c['INFISICAL_ENV']}")
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
            j = json.loads(urllib.request.urlopen(req, timeout=8).read())
            val = (j.get("secret") or {}).get("secretValue")
            if val is not None:
                _cache[name] = val
                return val
        except Exception:
            pass  # fall through to env
    if fallback_env and name in os.environ:
        return os.environ[name]
    return default


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        v = get_secret(sys.argv[1])
        print(f"{sys.argv[1]} = {'<found len %d>' % len(v) if v else '<not found>'}")
    else:
        # health: prove login + a read
        t = _login()
        print("infisical login:", "OK" if t else "FAIL (check .infisical_runtime)")
