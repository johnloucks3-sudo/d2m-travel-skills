#!/usr/bin/env python3
"""
Commission Audit — Headless Opus Spawn
"""
import sys
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "core" / "ai_infra"))

from thunderbird_headless_spawn import spawn_headless_claude

OUTPUT = str(_ROOT / "output" / "commission_audit_opus.md")
Path(OUTPUT).parent.mkdir(exist_ok=True)

PROMPT = """
You are performing a financial audit for Dreams2Memories Travel, LLC on behalf of COS Col Victoria Hale.
Commander John Loucks ("Yoda") needs a definitive, PDF-sourced D2M commission register.

## YOUR TOOLS
You have MCP access to Google Drive and Google Sheets. Use these to read PDFs and the Booking Master sheet.

## CONTEXT — WHAT WE KNOW SO FAR

Partial audit complete — 11 PDFs read from Drive folder 1iYKKZEEh6R3zih7JGNe2ezYP4KlRULU_

### PDF-CONFIRMED commission figures:
1. McLeod June (Silver Muse Jun 23-Jul 3 2026, BN 298475-25): Gross $25,896, Commission $2,594.54 (Silversea 16%+1% on NCF), D2M 70% = $1,816.18
2. Ely/Darrow (SS Grandeur Scandinavia Aug 29-Sep 8 2026, BN 3096289): Gross $20,640, Commission $2,685.90 (RSSC 15% Nexion on $8,953x2), D2M 70% = $1,880.13
3. Furlow (SS Grandeur Scandinavia Aug 29-Sep 8 2026, BN 3071222): Gross $18,120, Commission $2,287.90 (RSSC 15% Nexion on $7,593x2), D2M 70% = $1,601.53
4. Nichols (SS Grandeur Scandinavia Aug 29-Sep 8 2026, BN 3078056): Gross $18,896, Commission $2,287.90 (RSSC 15% Nexion same as Furlow), D2M 70% = $1,601.53
5. Loucks Dec 2026 (SS Grandeur Panama Canal Dec 29-Jan 14 2027, BN 3122006): Gross $25,798, Commission $3,775.02 (RSSC 17% Cruises and Tours Unlimited on $11,103x2), D2M 80% = $3,020.02
6. Kuklinski Kyle+Rosalie (Viking Mars Panama Canal Dec 17-27 2026, BN 9593880): Gross $7,598, Commission $1,291.66 (Viking 17% on $3,799x2), D2M 80% = $1,033.33
7. Kuklinski Roger+Nicholas (Viking Mars Panama Canal Dec 17-27 2026, BN 9593873): Gross $7,598, Commission $1,291.66 (Viking 17% on $3,799x2), D2M 80% = $1,033.33
8. Morton/Dodge (Viking Mars Panama Canal Dec 17-27 2026, BN 9595029): Gross $6,198, Commission $1,053.66 (Viking 17% on $3,099x2), D2M 80% = $842.93 -- NEW, not previously tracked
9. McLeod/McGlasson Princess Mar 2027 (Discovery Princess Mexico Riviera Mar 13-20 2027, BN 8X6PGQ): Gross $6,462, PASSENGER COPY ONLY -- no TA commission shown, D2M 70%, commission UNKNOWN
10. McLeod Dec 2027 (SS Prestige Season to Cheer Dec 18-28 2027, BN 3114500 CONFIRMED): Gross $15,098, Commission $2,179.96 (RSSC 17% C&TU on $6,344x2 commissionable + hotel), D2M 80% = $1,743.97
11. Loucks Silver Nova PERSONAL (Silver Nova Tokyo-Seattle Apr 23-May 11 2026, BN 566910-25): $10,800 PAID -- agent is "Interline Travel & Tour" NOT D2M. ZERO D2M commission.

### CRITICAL GAP -- McLeod Dec 2026 PDF MISSING:
TESS BN 2984034: RSSC Seven Seas Grandeur Lesser Antilles Journey Dec 18-28 2026, guests Erik McLeod + Melissa McGlasson. NO PDF found in TA invoices folder. Split UNKNOWN. Need to find this PDF.

### D2M Split Rules confirmed by Commander:
- 70%: Ely/Darrow, Nichols, Furlow, McLeod June, McLeod Mar 2027 Princess
- 80%: Kuklinski (all 3 Viking), Loucks Dec 2026, McLeod Dec 2027
- McLeod Dec 2026: UNKNOWN -- needs doc verification

### Booking Master Sheet Issues:
The "Commission" column contains DEPOSIT AMOUNTS not actual TA commission.
D2M splits wrong for 4 bookings (sheet used 80%, correct is 70% for Ely, Furlow, Nichols, McLeod June).
Sheet has 34 rows total -- many we have not seen PDFs for.

---

## YOUR TASKS

### TASK 1: Read the Booking Master Google Sheet
Read ALL rows from Sheet ID 1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU tab "Booking Master".
List every row with all columns. Flag missing booking numbers or suspicious data.

### TASK 2: Search Drive Folders for ALL PDFs
Search these folders and list every file found:

a) 00_INCOMING_BOOKINGS:
   - Folder 1hJ4WAgqEZUV0j5ctc6GE7jeEQAjMQWY9
   - Folder 1l4yseWU2JD5fQs_P7ZNq2vWE-ySdK25b

b) 01_PROCESSED_BOOKINGS:
   - Folder 1N4EDLSeYq_uv2E9LwkolUbNoCurK1Mcf

c) TA Invoices (already partially read):
   - Folder 1iYKKZEEh6R3zih7JGNe2ezYP4KlRULU_

For any NEW PDFs (not listed in the context above), read them and extract: client name, booking number, ship, sail dates, gross total, commissionable fare, commission rate and amount, host agency, final payment date, payment status.

HIGHEST PRIORITY: Find a PDF for McLeod Dec 2026 RSSC Lesser Antilles BN 2984034.

### TASK 3: Complete Commission Register
Produce a complete register of ALL D2M bookings combining sheet + PDF data:
- Client, Ship, Dates, Booking Number, Gross Total, TA Commission, Rate, Host Agency, D2M Split, D2M Share, Final Payment Date, Payment Status, Source (PDF vs Sheet vs Estimated)

### TASK 4: Sheet Correction Table
For every booking where PDF commission differs from sheet, document: current sheet value, PDF-correct value, delta, corrected D2M share, delta.

### TASK 5: Flag Anomalies
Note: bookings in sheet with no BN, PDFs for bookings not in sheet, unusual rates, overdue balances, the Loucks Silver Nova personal trip (should it be in D2M register?), any other surprises.

---

## OUTPUT

WRITE your complete audit to """ + OUTPUT + """

Structure:
# D2M Commission Audit -- Opus Analysis
*Generated: [date]*

## Section 1: Booking Master Sheet -- All Rows
[Full table of all rows as found]

## Section 2: Drive Folder Inventory
[Files found in each folder by name and ID]

## Section 3: New PDFs Extracted
[Any PDFs from 00_INCOMING or 01_PROCESSED not previously reviewed]

## Section 4: McLeod Dec 2026 Finding
[What you found or did not find for BN 2984034]

## Section 5: Complete Commission Register -- PDF-Sourced
[Full table with all bookings, PDF figures where available, clearly flagged where estimated]

## Section 6: Sheet Correction Table
[What needs to change in Booking Master]

## Section 7: Totals and Anomaly Flags
[Grand totals, D2M pipeline total, flags, surprises]

All dollar amounts as $X,XXX.XX. Be precise -- this is financial data.
Do NOT output to stdout. ALL output goes to the file path above.
"""

print("Spawning headless Opus commission audit...")
print(f"Output: {OUTPUT}")

result = spawn_headless_claude(
    prompt=PROMPT,
    output_file=OUTPUT,
    model="opus",
    task_name="commission_audit_opus",
    background=True,
)

print(f"Status: {result.get('status')}")
print(f"PID: {result.get('pid')}")
print(f"Log: {result.get('log_file')}")
if result.get("error"):
    print(f"ERROR: {result.get('error')}")
if result.get("errors"):
    print(f"ERRORS: {result.get('errors')}")
