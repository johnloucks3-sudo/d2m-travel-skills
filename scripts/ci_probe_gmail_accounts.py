#!/usr/bin/env python3
"""Gmail Accounts CI probe — closes the same comms-channel blind spot as
Telegram, for the two Gmail accounts (johnloucks3, d2mconcierge) everything
in the Wing depends on. 'email-handling' already existed in the registry
but only checked scripts/d2m_commander_digest.py — a digest-generation
script, not actual account reachability."""
import json
import sys

sys.path.insert(0, "/home/john/Thunderbird")
sys.path.insert(0, "/home/john/Thunderbird/api")


def _check(label, get_service_fn):
    try:
        svc = get_service_fn()
        profile = svc.users().getProfile(userId="me").execute()
        return {"ok": True, "email": profile.get("emailAddress")}
    except Exception as e:
        return {"ok": False, "error": str(e)[:150]}


def main() -> int:
    from thunderbird_google_auth import get_commander_gmail, get_persona_gmail

    results = {
        "johnloucks3": _check("johnloucks3", get_commander_gmail),
        "d2mconcierge": _check("d2mconcierge", get_persona_gmail),
    }
    all_ok = all(r["ok"] for r in results.values())
    print(json.dumps({"probe": "gmail-accounts", "accounts": results, "ok": all_ok}, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
