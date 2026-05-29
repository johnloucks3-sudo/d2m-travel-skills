#!/usr/bin/env python3
"""
Cloudflare Zero Trust Access — itinerary.d2mluxury.quest
Creates Access Application + Policy requiring johnloucks3@gmail.com login.

Usage:
    python3 scripts/cloudflare_access_itinerary.py <CF_API_TOKEN>

Get token at: dash.cloudflare.com → My Profile → API Tokens
Required permissions: Account > Access: Apps and Policies > Edit
"""

import sys
import json
import urllib.request
import urllib.error

ACCOUNT_ID = "86ad4247d8ea3f48f8545c2f05024787"
HOSTNAME   = "itinerary.d2mluxury.quest"
APP_NAME   = "D2M Itinerary — Commander Access"
ALLOWED_EMAIL = "johnloucks3@gmail.com"

def cf_request(token, method, path, data=None):
    url = f"https://api.cloudflare.com/client/v4{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        url, data=body, method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/cloudflare_access_itinerary.py <CF_API_TOKEN>")
        sys.exit(1)

    token = sys.argv[1]
    print(f"Account: {ACCOUNT_ID}")
    print(f"Protecting: {HOSTNAME}")
    print(f"Allowed: {ALLOWED_EMAIL}")
    print()

    # Check for existing application
    print("Checking for existing Access application...")
    existing = cf_request(token, "GET", f"/accounts/{ACCOUNT_ID}/access/apps")
    if existing.get("success"):
        for app in existing.get("result", []):
            if app.get("domain") == HOSTNAME:
                print(f"Found existing app: {app['id']} — deleting to recreate cleanly")
                cf_request(token, "DELETE", f"/accounts/{ACCOUNT_ID}/access/apps/{app['id']}")
                print("  Deleted.")
                break

    # Create Access Application
    print("Creating Access application...")
    app_payload = {
        "name": APP_NAME,
        "domain": HOSTNAME,
        "type": "self_hosted",
        "session_duration": "24h",
        "auto_redirect_to_identity": True,
        "allowed_idps": [],   # Uses all configured IdPs
        "skip_interstitial": True,
    }
    resp = cf_request(token, "POST", f"/accounts/{ACCOUNT_ID}/access/apps", app_payload)
    if not resp.get("success"):
        print(f"ERROR creating app: {resp}")
        sys.exit(1)

    app_id = resp["result"]["uid"]
    print(f"  App created: {app_id}")

    # Create Access Policy — allow only Commander email
    print(f"Creating policy — allow {ALLOWED_EMAIL}...")
    policy_payload = {
        "name": "Commander Only",
        "decision": "allow",
        "precedence": 1,
        "include": [
            {"email": {"email": ALLOWED_EMAIL}}
        ],
        "require": [],
        "exclude": [],
    }
    resp = cf_request(token, "POST",
                      f"/accounts/{ACCOUNT_ID}/access/apps/{app_id}/policies",
                      policy_payload)
    if not resp.get("success"):
        print(f"ERROR creating policy: {resp}")
        sys.exit(1)

    policy_id = resp["result"]["uid"]
    print(f"  Policy created: {policy_id}")

    print()
    print("=" * 60)
    print(f"DONE — Cloudflare Access is active on {HOSTNAME}")
    print(f"  Only {ALLOWED_EMAIL} may access this domain.")
    print(f"  Auth method: Google (Cloudflare will prompt for Google login)")
    print()
    print("Next: run the following to switch server to /Thunderbird root:")
    print()
    print("  ssh yoga 'sed -i \\'s|--directory /home/john/Thunderbird/output/|--directory /home/john/Thunderbird/|\\' ~/.config/systemd/user/itinerary-server.service && systemctl --user daemon-reload && systemctl --user restart itinerary-server.service'")
    print("=" * 60)

if __name__ == "__main__":
    main()
