import sys, os
from tcd.collectors import collect_gmail_drafts
from tcd.mfr import describe
from core.relay.contact_ag import contact_ag
from tcd.multi_tab import collect_multi_tab

print("--- 1 & 7. Drafts ---")
drafts = collect_gmail_drafts()
print(f"Total drafts found: {len(drafts)}")
for d in drafts:
    print(f"- {d.get('title')} (To: {d.get('from')})")

print("\n--- 2. MFR describe ---")
print("Alert:", describe({"id": "alert-1", "title": "Some alert", "priority": "p1", "date": "2026-07-29", "tags": ["alert", "john"]}))
print("Mission:", describe({"id": "mission-001", "title": "Buy stuff", "stage": "T", "owner": "Dani", "date": "2026-07-31"}))
print("Keep:", describe({"id": "keep-abc", "title": "My secrets", "body": "SUPER SECRET BODY"}))

print("\n--- 4. Multi-tab dedup ---")
# Call collect_multi_tab, which prints to stderr
multi_items = collect_multi_tab()
print(f"Total multi-tab items returned: {len(multi_items)}")

print("\n--- 6. Routing log patch ---")
res = contact_ag("Test task", verdict_tag="AG-TEST-LOG", deliverable_path="/tmp/ag_test_deliv.md", timeout=5)
with open("/home/john/Thunderbird/OpsCenter/collaboration/routing_log.md") as f:
    print(f.read())
