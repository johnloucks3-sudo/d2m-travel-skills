
import sys
import json
from pathlib import Path
from core.intel.thunderbird_twitter_osint import run_twitter_osint_sweep, get_digest_json, get_digest_section

# Run the OSINT sweep
print("Running X/Twitter OSINT sweep...")
report = run_twitter_osint_sweep()

if report:
    print("\nOSINT Sweep Report (JSON):")
    print(json.dumps(report, indent=2))

    print("\nOSINT Digest Section (Markdown):")
    print(get_digest_section())

    # Get the latest JSON and MD paths
    intel_dir = Path(__file__).parent.parent.parent / "core" / "intel" / "intel"
    latest_json_path = intel_dir / "twitter_osint_latest.json"
    latest_md_path = intel_dir / "twitter_osint_latest.md"

    print(f"\nLatest JSON report saved to: {latest_json_path}")
    print(f"Latest Markdown report saved to: {latest_md_path}")

    # Read the contents for the final output
    final_json_content = ""
    final_md_content = ""
    if latest_json_path.exists() and latest_json_path.stat().st_size > 0:
        final_json_content = latest_json_path.read_text()
    if latest_md_path.exists() and latest_md_path.stat().st_size > 0:
        final_md_content = latest_md_path.read_text()

    print("\n--- Full JSON Output ---")
    if final_json_content:
        print(final_json_content)
    else:
        print("No JSON content available (sweep might have failed or produced empty output).")

    print("\n--- Full Markdown Output (Telegram Briefing) ---")
    if final_md_content:
        print(final_md_content)
    else:
        print("No Markdown content available (sweep might have failed or produced empty output).")
else:
    print("Failed to run OSINT sweep.")
    sys.exit(1)
