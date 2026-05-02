#!/usr/bin/env python3
"""
Credential Validation Suite — Test all service integrations
Purpose: Verify which credentials are valid, which need provisioning
Output: JSON status report + mission board entries
"""

import json
import os
from pathlib import Path
from datetime import datetime

CREDS_DIR = Path("/home/john/Thunderbird/creds")
OUTPUT_FILE = Path("/home/john/Thunderbird/output") / f"credential_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

def check_file_status(cred_file):
    """Check if credential file exists and has content."""
    path = CREDS_DIR / cred_file
    if not path.exists():
        return {"status": "missing", "exists": False, "size": 0, "content": None}

    try:
        content = json.loads(path.read_text())
        size = path.stat().st_size

        # Check if empty/placeholder
        has_keys = any(v for v in content.values() if isinstance(v, str) and v.strip() and not v.startswith("http") and not v.startswith("Get credentials"))

        return {
            "status": "empty" if not has_keys else "configured",
            "exists": True,
            "size": size,
            "content": content
        }
    except Exception as e:
        return {"status": "error", "exists": True, "error": str(e), "size": path.stat().st_size}

def validate_credentials():
    """Main validation loop."""

    creds_to_check = [
        # Critical Travel APIs
        ("amadeus_credentials.json", "Amadeus Flight Search (TEST)"),
        ("centrav_session.json", "Centrav B2B Flights (Live)"),
        ("hotelbeds_credentials.json", "Hotelbeds Hotels (TEST)"),
        ("expedia_credentials.json", "Expedia TAAP (Placeholder)"),

        # Transfer/Tour APIs
        ("blacklane_credentials.json", "Blacklane Transfers (Partner Program)"),
        ("mozio_credentials.json", "Mozio Transfers (Partner Program)"),
        ("getyourguide_credentials.json", "GetYourGuide Tours (Partner Program)"),
        ("viator_credentials.json", "Viator Tours (Partner Program)"),

        # Data Scraping
        ("apify_credentials.json", "Apify Web Scraping (Placeholder)"),

        # Ancillary Services
        ("opentable_credentials.json", "OpenTable Dining (Config)"),
        ("shore_excursions_credentials.json", "Shore Excursions (Config)"),
        ("welcome_pickups_credentials.json", "Welcome Pickups (Config)"),
        ("tomtom_credentials.json", "TomTom Maps (Config)"),
    ]

    results = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_checked": len(creds_to_check),
            "configured": 0,
            "empty_placeholder": 0,
            "missing": 0,
            "error": 0
        },
        "credentials": {}
    }

    for cred_file, description in creds_to_check:
        status = check_file_status(cred_file)
        results["credentials"][cred_file] = {
            "description": description,
            "file_status": status["status"],
            "exists": status["exists"],
            "size_bytes": status["size"]
        }

        if status["status"] == "configured":
            results["summary"]["configured"] += 1
        elif status["status"] == "empty":
            results["summary"]["empty_placeholder"] += 1
        elif status["status"] == "missing":
            results["summary"]["missing"] += 1
        elif status["status"] == "error":
            results["summary"]["error"] += 1

    return results

if __name__ == "__main__":
    results = validate_credentials()

    # Write output
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(results, indent=2))

    print(json.dumps(results, indent=2))
    print(f"\n✅ Validation complete. Results: {OUTPUT_FILE}")

    # Summary
    print("\n=== CREDENTIAL STATUS SUMMARY ===")
    print(f"Configured: {results['summary']['configured']}")
    print(f"Empty (need provisioning): {results['summary']['empty_placeholder']}")
    print(f"Missing: {results['summary']['missing']}")

    # List what needs immediate action
    print("\n=== ACTION ITEMS ===")
    for cred_file, info in results['credentials'].items():
        if info['file_status'] == 'empty':
            print(f"• {info['description']}: {cred_file} — needs partner program registration")
        elif info['file_status'] == 'missing':
            print(f"• {info['description']}: {cred_file} — file missing entirely")
