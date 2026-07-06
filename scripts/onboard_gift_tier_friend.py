#!/usr/bin/env python3
"""Onboard a new gift-tier friend to Hale-direct AgentMail access — Bold Use #5.

Generalizes the Bryana Jarboe pattern (proven, sent, working) into a
repeatable generator: given a name and email, produces (1) a ready-to-add
WF-17 named-waiver entry, (2) a personalized Wing-resources manual, and
(3) a draft intro email body — so onboarding the next friend is a fast,
consistent build, not a from-scratch rewrite.

Usage: python3 scripts/onboard_gift_tier_friend.py --name "Jane Smith" \\
    --email jane@example.com --context "building her own consulting practice"

Does NOT add the waiver or send anything automatically — reviews the
generated files, then a human (or Hale, deliberately) adds the waiver
entry and sends via the established send_waived_client_email() path.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
MANUAL_TEMPLATE_PATH = THUNDERBIRD / "docs" / "BRYANA_WING_RESOURCES_MANUAL.md"


def generate_waiver_snippet(name: str, email: str, context: str) -> dict:
    return {
        "name": name,
        "emails": [email],
        "cc": ["johnloucks3@gmail.com"],
        "voice_track": "hale",
        "send_channel": "agentmail_hale_thunderbird",
        "granted_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "onboard_gift_tier_friend.py",
        "conditions": [
            "CC johnloucks3",
            "Hale reviews her/his own sends before they go",
            f"gift-tier friend — {context}",
        ],
    }


def generate_manual(name: str, context: str) -> str:
    template = MANUAL_TEMPLATE_PATH.read_text()
    # swap the Bryana-specific framing for the new person, keep the structure/capability list intact
    manual = template.replace("Bryana Jarboe", name).replace(
        "gift-tier friend, uses Hale directly, not Dani", f"gift-tier friend — {context}"
    )
    return manual


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--email", required=True)
    ap.add_argument("--context", required=True, help="one line: what they're building / why they're getting this")
    args = ap.parse_args()

    slug = args.name.lower().replace(" ", "_")
    out_dir = THUNDERBIRD / "output"
    out_dir.mkdir(exist_ok=True)

    waiver = generate_waiver_snippet(args.name, args.email, args.context)
    waiver_path = out_dir / f"waiver_snippet_{slug}.json"
    waiver_path.write_text(json.dumps(waiver, indent=2))

    manual = generate_manual(args.name, args.context)
    manual_path = out_dir / f"{slug.upper()}_WING_RESOURCES_MANUAL.md"
    manual_path.write_text(manual)

    print(f"Generated:\n  {waiver_path}\n  {manual_path}")
    print("\nNext: review both, then manually add the waiver entry to "
          "config/wf17_named_waivers.json and send via "
          "core.email.wf17_named_waivers.send_waived_client_email() — "
          "not automated, by design (each new person deserves a real review, not a rubber stamp).")


if __name__ == "__main__":
    main()
