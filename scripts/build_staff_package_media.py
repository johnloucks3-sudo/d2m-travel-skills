#!/usr/bin/env python3
"""
Build the SSS-004 staff package in Google Doc + Google Sheets from the master
markdown. One-off delivery helper. Prints the two URLs (created in the
authenticated account's own Drive — johnloucks3).
"""
import re
import sys

sys.path.insert(0, "/home/john/Thunderbird")
from api.thunderbird_google_auth import get_docs, get_sheets

MASTER = "/tmp/claude-1000/-home-john-Thunderbird/89f6a46a-3fac-48d0-8093-633694aebafe/scratchpad/staff_package_master.md"
TITLE = "Thunderbird Staff Package — SSS-004: USAF Staff Summary Sheet Adoption (2026-07-19)"

text = open(MASTER).read()

# ── Google Doc ──────────────────────────────────────────────────────────────
docs = get_docs()
doc = docs.documents().create(body={"title": TITLE}).execute()
doc_id = doc["documentId"]
docs.documents().batchUpdate(
    documentId=doc_id,
    body={"requests": [{"insertText": {"location": {"index": 1}, "text": text}}]},
).execute()
doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
print("DOC_URL:", doc_url)

# ── Google Sheets (7 tabs: cover + 6) ───────────────────────────────────────
# Split the master on the tab headers.
parts = re.split(r"\n(?=# (?:TAB \d|STAFF PACKAGE))", text)
tab_map = [
    ("Cover", "STAFF PACKAGE"),
    ("1-Approval", "TAB 1"),
    ("2-Position Paper", "TAB 2"),
    ("3-WBS", "TAB 3"),
    ("4-Errors", "TAB 4"),
    ("5-AAR", "TAB 5"),
    ("6-Lessons", "TAB 6"),
]
def section_for(marker):
    for p in parts:
        if p.lstrip().startswith("# " + marker):
            return p.strip()
    return ""

sheets = get_sheets()
ss = sheets.spreadsheets().create(body={
    "properties": {"title": TITLE},
    "sheets": [{"properties": {"title": name}} for name, _ in tab_map],
}).execute()
ss_id = ss["spreadsheetId"]

for name, marker in tab_map:
    body = section_for(marker)
    rows = [[line] for line in body.splitlines()] or [[""]]
    # Sheets API: write column A, one wrapped cell per source line.
    sheets.spreadsheets().values().update(
        spreadsheetId=ss_id,
        range=f"'{name}'!A1",
        valueInputOption="RAW",
        body={"values": rows},
    ).execute()

sheet_url = f"https://docs.google.com/spreadsheets/d/{ss_id}/edit"
print("SHEET_URL:", sheet_url)
