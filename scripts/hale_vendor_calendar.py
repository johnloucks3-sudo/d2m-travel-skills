#!/usr/bin/env python3
"""
HALE Vendor Calendar — Contract renewals, commission changes, intel windows
"""

import json, sys
from datetime import datetime, date, timedelta
from pathlib import Path

CAL_FILE = Path.home() / "Thunderbird" / "hale_vendor_calendar.json"

# Known vendor contracts and renewal windows
VENDORS = {
    "silversea": {
        "commission": {"rate": 0.16, "last_known": "2026-01-01", "change_date": None},
        "contract_renewal": "2026-12-31",
        "intel_windows": [
            {"name": "Summer 2027 itineraries", "expected": "2026-09-01"},
            {"name": "Wave season promos", "expected": "2027-01-15"}
        ]
    },
    "regent": {
        "commission": {"rate": 0.70, "note": "via Nexion, D2M keeps 70%", "last_known": "2026-01-01"},
        "contract_renewal": "2026-12-31",
        "intel_windows": [
            {"name": "2027-2028 itineraries", "expected": "2026-10-01"},
            {"name": "Savings events", "expected": "2026-11-01"}
        ]
    },
    "viking": {
        "commission": {"rate": 0.80, "note": "via Outside Agents, D2M keeps 80%", "last_known": "2026-01-01"},
        "contract_renewal": "2026-12-31",
        "intel_windows": [
            {"name": "2027 ocean itineraries", "expected": "2026-08-01"},
            {"name": "2027 river itineraries", "expected": "2026-09-01"}
        ]
    },
    "celebritiy": {
        "commission": {"rate": 0.10, "note": "standard", "last_known": "2026-01-01"},
        "contract_renewal": None,
        "intel_windows": []
    },
    "princess": {
        "commission": {"rate": 0.10, "note": "standard", "last_known": "2026-01-01"},
        "contract_renewal": None,
        "intel_windows": []
    },
    "ponant": {
        "commission": {"rate": 0.10, "note": "standard", "last_known": "2026-01-01"},
        "contract_renewal": None,
        "intel_windows": []
    }
}

def check_alerts():
    """Return alerts for upcoming renewals and intel windows"""
    today = date.today()
    alerts = []
    
    for name, data in VENDORS.items():
        # Contract renewal within 90 days
        if data.get("contract_renewal"):
            renew = date.fromisoformat(data["contract_renewal"])
            days_out = (renew - today).days
            if 0 < days_out <= 90:
                alerts.append({
                    "type": "contract_renewal",
                    "vendor": name,
                    "date": data["contract_renewal"],
                    "days_out": days_out,
                    "severity": "HIGH" if days_out <= 30 else "MEDIUM"
                })
        
        # Intel windows approaching
        for window in data.get("intel_windows", []):
            if window.get("expected"):
                exp = date.fromisoformat(window["expected"])
                days_out = (exp - today).days
                if 0 < days_out <= 60:
                    alerts.append({
                        "type": "intel_window",
                        "vendor": name,
                        "window": window["name"],
                        "expected": window["expected"],
                        "days_out": days_out,
                        "severity": "HIGH" if days_out <= 14 else "LOW"
                    })
    
    return alerts

def build():
    cal = {
        "last_updated": datetime.now().isoformat(),
        "vendors": VENDORS,
        "alerts": check_alerts()
    }
    CAL_FILE.write_text(json.dumps(cal, indent=2))
    print(f"[VENDOR CAL] {len(cal["alerts"])} alerts active. Written to {CAL_FILE}")

if __name__ == "__main__":
    build()
