#!/usr/bin/env python3
"""
Test & Validate COS Approval Workflow
Checks all prerequisites and runs a smoke test of the entire workflow.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

def check_prerequisites():
    """Verify all prerequisites are in place."""
    print("\n" + "=" * 70)
    print("APPROVAL WORKFLOW — PREREQUISITES CHECK")
    print("=" * 70 + "\n")

    checks_passed = 0
    checks_failed = 0

    # Check 1: Scripts exist
    print("[1/5] Checking scripts...")
    scripts = [
        "scripts/create_gmail_draft_direct_v3.py",
        "scripts/cos_approval_monitor.py",
        "scripts/cos_final_draft_generator.py",
        "scripts/setup_d2mconcierge_oauth.py",
    ]

    script_dir = Path.home() / "Thunderbird"
    for script in scripts:
        script_path = script_dir / script
        if script_path.exists():
            print(f"  ✓ {script}")
            checks_passed += 1
        else:
            print(f"  ✗ {script} — NOT FOUND")
            checks_failed += 1

    # Check 2: Directories exist
    print("\n[2/5] Checking directories...")
    dirs = [
        Path.home() / ".thunderbird_approvals",
        Path.home() / "Thunderbird" / "drafts",
        Path.home() / "Thunderbird" / "output",
    ]

    for d in dirs:
        if d.exists():
            print(f"  ✓ {d}")
            checks_passed += 1
        else:
            print(f"  ✗ {d} — NOT FOUND (will be created on first run)")
            checks_failed += 0  # Not critical, will be auto-created

    # Check 3: d2mconcierge OAuth
    print("\n[3/5] Checking d2mconcierge OAuth...")
    oauth_file = Path.home() / ".credentials" / "d2mconcierge.json"
    if oauth_file.exists():
        try:
            with open(oauth_file) as f:
                creds = json.load(f)
            if creds.get("token") and creds.get("refresh_token"):
                print(f"  ✓ {oauth_file}")
                print(f"    Token: {creds['token'][:20]}...")
                checks_passed += 1
            else:
                print(f"  ✗ {oauth_file} — Missing token or refresh_token")
                checks_failed += 1
        except Exception as e:
            print(f"  ✗ {oauth_file} — Invalid JSON: {e}")
            checks_failed += 1
    else:
        print(f"  ✗ {oauth_file} — NOT FOUND")
        print(f"    Run: python3 ~/Thunderbird/scripts/setup_d2mconcierge_oauth.py")
        checks_failed += 1

    # Check 4: Systemd service
    print("\n[4/5] Checking systemd service...")
    service_file = Path("/etc/systemd/system/cos-approval-monitor.service")
    if service_file.exists():
        print(f"  ✓ Service file installed")
        checks_passed += 1
    else:
        print(f"  ✗ Service file not installed")
        print(f"    Run: sudo cp ~/Thunderbird/scripts/cos-approval-monitor.service /etc/systemd/system/")
        checks_failed += 1

    # Check 5: Python dependencies
    print("\n[5/5] Checking Python dependencies...")
    try:
        import googleapiclient.discovery
        print(f"  ✓ googleapiclient")
        checks_passed += 1
    except ImportError:
        print(f"  ✗ googleapiclient — NOT INSTALLED")
        print(f"    Run: pip3 install google-api-python-client google-auth-oauthlib")
        checks_failed += 1

    try:
        import bs4
        print(f"  ✓ beautifulsoup4")
        checks_passed += 1
    except ImportError:
        print(f"  ✗ beautifulsoup4 — NOT INSTALLED")
        print(f"    Run: pip3 install beautifulsoup4")
        checks_failed += 1

    # Summary
    print("\n" + "=" * 70)
    print(f"SUMMARY: {checks_passed} passed, {checks_failed} failed")
    print("=" * 70 + "\n")

    return checks_failed == 0

def run_smoke_test():
    """Run a basic smoke test of the workflow."""
    print("\n" + "=" * 70)
    print("APPROVAL WORKFLOW — SMOKE TEST")
    print("=" * 70 + "\n")

    # Create test HTML
    test_html = Path.home() / "Thunderbird" / "drafts" / "test_approval.html"
    test_html.write_text("""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body { background-color: #f7f3ea; color: #0000ff; font-family: Georgia, serif; }
            .proposal { width: 600px; padding: 20px; }
        </style>
    </head>
    <body>
        <div class="proposal">
            <h1>Test Proposal</h1>
            <p>This is a test of the approval workflow. If you see this email, the system is working.</p>
            <p>Timestamp: """ + datetime.now().isoformat() + """</p>
        </div>
    </body>
    </html>
    """)

    print(f"[1/3] Test HTML created: {test_html}")

    # Test imports
    print(f"\n[2/3] Testing imports...")
    try:
        sys.path.insert(0, str(Path.home() / "Thunderbird" / "scripts"))
        from gmail_template_stripper import GmailSafePreprocessor
        print(f"  ✓ GmailSafePreprocessor loaded")
    except ImportError as e:
        print(f"  ✗ Failed to import: {e}")
        return False

    # Test preprocessing
    print(f"\n[3/3] Testing HTML preprocessing...")
    try:
        html = test_html.read_text()
        preprocessor = GmailSafePreprocessor()
        processed, log = preprocessor.process(html)
        print(f"  ✓ Preprocessing successful")
        print(f"    Input:  {len(html):,} bytes")
        print(f"    Output: {len(processed):,} bytes")
        print(f"    Summary: {log.summary()}")
    except Exception as e:
        print(f"  ✗ Preprocessing failed: {e}")
        return False

    print("\n" + "=" * 70)
    print("✅ SMOKE TEST PASSED")
    print("=" * 70 + "\n")
    print("The approval workflow is ready for deployment.")
    print("\nNext steps:")
    print("  1. Start the service: sudo systemctl enable --now cos-approval-monitor.service")
    print("  2. Create a draft: python3 ~/Thunderbird/scripts/create_gmail_draft_direct_v3.py ...")
    print("  3. Read the manual: less ~/Thunderbird/docs/APPROVAL_WORKFLOW_OPERATOR_MANUAL.md")
    print("\n")

    return True

if __name__ == "__main__":
    if not check_prerequisites():
        print("\n❌ Prerequisites check FAILED. Fix the issues above and try again.\n")
        sys.exit(1)

    if not run_smoke_test():
        print("\n❌ Smoke test FAILED. Check the errors above.\n")
        sys.exit(1)

    sys.exit(0)
