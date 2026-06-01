---
name: email-draft
description: "Draft a client-facing email using the Dani 6-step creative chain. Full Wing procedure — experience check, narrative, brand, voice, facts verification, WF-17 gate. Triggers on: email draft, client email, lifecycle email, draft email, write email, Dani, validation email, lifecycle touchpoint, welcome email, payment reminder, specialty dining, ARC email"
---

# /email-draft — Dani 6-Step Client Email Chain

You execute this procedure yourself. This is a Wing procedure, not a handoff.
Use /ask-opus only if you hit a judgment call requiring Opus-level reasoning.

## Prerequisites — Gather Before Writing

```bash
# 1. Find client dossier
ls /home/john/Thunderbird/dossiers/ | grep -i "[client-name]"

# 2. Check TESS booking
python3 /home/john/Thunderbird/itinerary/validate_dossier.py

# 3. Read dossier — know: client names, ship, departure date, cabin, FPD, special requests
cat /home/john/Thunderbird/dossiers/[DOSSIER_FILE]
```

## The 6-Step Chain (mandatory — zero steps skipped)

### Step 1 — Experience Layer (Reyes)
Check the dossier for:
- Excursion interests / adventure level
- Dining preferences / dietary restrictions
- Accessibility needs
- Prior cruises / loyalty status
- What makes THIS client's trip unique

Output: 3-5 bullet notes to weave into the email.

### Step 2 — Narrative Draft (Luna)
Write evocative port/ship/destination copy:
- Lead with the experience, not the logistics
- Port descriptions: sensory, specific, aspirational
- Ship descriptions: use actual ship name, specific amenities
- No generic travel brochure language

### Step 3 — Brand Pass (Naia)
Apply D2M voice standards:
- USAFA colors: background #f7f3ea · text #0000ff · accent navy #003087
- Font: Georgia
- Tone: warm expert, never salesy, never generic
- D2M logo in header (banner at `storage/output/images/`)
- Sign-off: "Thanks" — NEVER "Best"

### Step 4 — Client Voice (Dani)
Final tone adjustment for THIS client's relationship:
- Personal opening paragraph — reference something specific to them
- Match energy level (formal vs warm vs casual — read the dossier)
- One clear call to action only
- Length: enough to be warm, short enough to be read

### Step 5 — Facts + $$ Verification
Before finalizing, verify against primary sources:
- Every $ figure → matches portal/TESS/dossier EXACTLY
- FPD → confirmed from portal, not memory
- Ship name, departure date, cabin category → confirmed
- Any claim not in a primary source → REMOVE IT (Negative-Space Rule)
- Tag uncertain items: CONFIRMED / INFERRED / UNKNOWN

If any $ figure present → Harlan 6-step sign-off required:
1. Portal balance 2. Portal FPD 3. Compare vs dossier 4. Root cause any delta
5. Credits verified 6. Sign-off: "Confirmed: $X as of [date], source: [portal/TESS/dossier]"

### Step 6 — WF-17 Gate
Create draft and surface to Commander. NEVER send directly.

```python
# Pre-process HTML (inline CSS, convert divs→tables):
# python3 /home/john/Thunderbird/scripts/gmail_template_stripper.py input.html output.html

# Create draft in d2mconcierge (auto-labels THUNDERBIRD-Commander-Review):
import sys; sys.path.insert(0, '/home/john/Thunderbird')
from core.email.thunderbird_gmail import gmail_create_draft_sync
result = gmail_create_draft_sync(
    to="client@email.com",
    subject="Subject line",
    body=html_body,          # full HTML string
    persona_id="CONCIERGE"   # always CONCIERGE — uses d2mconcierge
)
print(result)
```

**Account:** d2mconcierge ONLY — NEVER johnloucks3
**Label:** THUNDERBIRD-Commander-Review (auto-applied by gmail_create_draft_sync)
**Notify Commander:** "Draft ready in d2mconcierge for [client] — [TP description]. Awaiting your review."

## HTML Email Format

```html
<!-- Minimum structure for Gmail-safe HTML -->
<table width="600" style="background-color:#f7f3ea;font-family:Georgia,serif;color:#0000ff;">
  <tr><td style="padding:20px;">
    <!-- D2M banner header -->
    <!-- Email body — all inline CSS -->
    <!-- Signature block with persona avatar if available -->
  </td></tr>
</table>
```

Colors hardcoded inline on every element: bg=#f7f3ea · text=#0000ff · accent=#003087

## Routing Rules

| Email type | Account | Label |
|---|---|---|
| Client products (validation, proposals, itineraries) | d2mconcierge | THUNDERBIRD-Commander-Review |
| Personal/non-D2M | johnloucks3 | WING-PERSONAL-DRAFT |
| Internal briefs/reports | d2mconcierge → FULL SEND to johnloucks3 | none |

## Step Completion Checklist (attach to WF-17 surface)

- [ ] Step 1: Experience notes gathered from dossier
- [ ] Step 2: Narrative — port/ship copy written
- [ ] Step 3: Brand — USAFA colors, Georgia, D2M voice
- [ ] Step 4: Client voice — personal opening, correct register
- [ ] Step 5: Facts verified vs primary sources / Harlan sign-off if $ present
- [ ] Step 6: Draft in d2mconcierge, labeled, Commander notified
