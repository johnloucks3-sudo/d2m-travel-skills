# KUKLINSKI EXCURSION PRODUCT BUILD REPORT
**Date:** 2026-06-19  
**Built by:** Hale (COS/COO)  
**Client:** Kuklinski Group — Viking Mars Panama Canal Dec 17–27, 2026

---

## BUILD STATUS SUMMARY

| Stage | Status | Output |
|-------|--------|--------|
| Stage 0 — PE Catalog Appendix | ✅ COMPLETE | Appended to excursion dossier |
| Stage 1 — Google Form | ⚠️ BLOCKED (auth) | Blocker file written; placeholder in draft |
| Stage 2 — Per-Couple Picklist Template | ✅ COMPLETE | Template created |
| Email Fix — Name correction | ✅ COMPLETE | Amy→Rosalie, Carla→Nick corrected |
| Email Preprocess (gmail_template_stripper) | ✅ COMPLETE | 7.3KB → 13.3KB, 0 errors |
| Kyle Email — Gmail Draft Staged | ✅ COMPLETE | Draft id: r7197096571161040568 |

---

## STAGE 0 — PE CATALOG APPENDIX ✅

**File:** `dossiers/Kuklinski_VikingMars_Panama_Dec2026_Excursions.md`  
**Appended:** `## APPENDIX — FULL PROJECT EXPEDITION CATALOG`

Full Easy/Moderate PE catalog for all 5 ports:
| Port | Easy | Moderate | Total |
|------|------|----------|-------|
| Colón, Panama | 23 | 17 | 40 |
| Puerto Limón, Costa Rica | 48 | 5 | 53 |
| Roatán, Honduras | 84 | 31 | 115 |
| Belize City, Belize | 20 | 28 | 48 |
| Cozumel, Mexico | 87 | 25 | 112 |
| **TOTAL** | **262** | **106** | **368** |

Each entry: tour name, price pp, duration, ★ rating + review count, back-to-ship status, PE URL.  
Source: `cache/pe_kuklinski_panama_dec2026.json` (no web scraping — cache only, per Commander standing rule).

---

## STAGE 1 — GOOGLE FORM ⚠️ BLOCKED

**Script:** `scripts/create_kuklinski_excursion_form.py`  
**Error:** `ValueError: Client secrets must be for a web or installed app.`  
**Root cause (corrected):** `~/.gmail-mcp/johnloucks3/credentials.json` is an OAuth token file (not a client secrets file). The script's `InstalledAppFlow` needs a client secrets file — confirmed at `/home/john/.credentials/client_secrets.json` (InstalledApp type, correct). Also: `~/.gmail-mcp/johnloucks3/token.json` does not yet exist (target for Forms API token).  
**Blocker file:** `cache/kuklinski_form_BLOCKER.md` — contains verified auth snippet using correct client_secrets path. Note: prior blocker had wrong diagnosis ("service account") and wrong command (`thunderbird_google_auth.py --scopes` flag doesn't exist) — both corrected.

**Draft impact:** Kyle email draft staged WITH `FORM_URL_PLACEHOLDER`. Do NOT send until form URL is inserted.

### Commander Action Required (before sending Kyle email):
```bash
# Step 1: Run OAuth flow for forms.body scope (opens browser — ~2 min)
cd /home/john/Thunderbird && python3 - <<'EOF'
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/forms.body", "https://www.googleapis.com/auth/drive.file"]
CLIENT_SECRETS = Path.home() / ".credentials" / "client_secrets.json"
TOKEN_PATH = Path.home() / ".gmail-mcp" / "johnloucks3" / "token.json"

flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
creds = flow.run_local_server(port=0)
TOKEN_PATH.write_text(creds.to_json())
print(f"Done. Token: {TOKEN_PATH}")
EOF

# Step 2: Create the form
python3 scripts/create_kuklinski_excursion_form.py
# → Saves share URL to cache/kuklinski_excursion_form.json

# Step 3: Insert URL into draft (edit draft in Gmail)
# Replace FORM_URL_PLACEHOLDER in draft r7197096571161040568 with share_url from kuklinski_excursion_form.json
```

---

## STAGE 2 — PER-COUPLE PICKLIST TEMPLATE ✅

**File:** `dossiers/Kuklinski_excursion_picklist_TEMPLATE.md`

Template structure:
- 5 ports × 3 couples = 15 recommendation rows
- Each row: survey preference field, Viking rec, PE rec, SBC math, out-of-pocket, fit note
- SBC running balance calculator per couple (all ports)
- Mobility constraints enforced throughout:
  - Josh Morton (81 as of Dec 11, 2026): Easy only
  - Erica Dodge (78): Easy only  
  - Roger Kuklinski (75): Easy only
  - Kyle/Rosalie/Nick: No constraints
- Birthday note: Joshua turns 81 on Dec 11 — 6 days before embarkation
- Booking window coordination note (Aug 2 vs Sep 23 gap risk)

**How to use:** When survey responses arrive from Kyle, fill `[PENDING SURVEY]` fields and route to Dani for TP 2.1 email build. Target: recommendations in Kyle's hands by late July, before Aug 2 booking window.

---

## KYLE EMAIL DRAFT ✅

**Draft ID:** `r7197096571161040568`  
**Message ID:** `19ee06102130605f`  
**Account:** d2mconcierge@gmail.com  
**From alias:** concierge@d2mluxury.quest  
**To:** kyle.kuklinski@gmail.com  
**Subject:** Viking Mars Panama — Let's Plan Your Excursions  
**Label:** THUNDERBIRD-Commander-Review (Label_13) — applied  

**Name correction applied:** Draft original used wrong names for Roger's wife and Josh's partner. Corrected per dossier ground truth:
- "Amy" → "Rosalie" (Kyle's wife: Rosalie Morton Kuklinski)
- "Carla" → "Nick" (Roger's husband: Dr Nicholas John Kuklinski)

**⚠️ HOLD BEFORE SEND:** `FORM_URL_PLACEHOLDER` in draft CTA button. Do not send until Commander completes Stage 1 auth and inserts real form URL. See blocker file.

**HTML preprocessing:** gmail_template_stripper.py ran clean (0 errors, 4 div→table conversions, CSS inlined). Cream (#f7f3ea) + blue (#0000ff) preserved.

---

## DOSSIER GROUND TRUTH — COUPLE NAMES (IMPORTANT)

The build prompt used incorrect names for two guests. **Dossier is authoritative:**

| Couple | Booking | Correct Names |
|--------|---------|---------------|
| Couple 1 | 9593880 | **Kyle Stanley Kuklinski + Rosalie Morton Kuklinski** |
| Couple 2 | 9593873 | **Roger David Kuklinski + Dr Nicholas John Kuklinski** |
| Couple 3 | 9595029 | **Joshua Morton + Erica Dodge** |

The hale_brief.md had "Amy, Roger, Carla" — these names are incorrect and have been noted for correction. Rosalie and Nicholas are the dossier-verified names.

---

## WHAT COMMANDER DOES NEXT

**Immediate (before sending Kyle email):**
1. Run Stage 1 auth command in `cache/kuklinski_form_BLOCKER.md`
2. Run `python3 scripts/create_kuklinski_excursion_form.py` — captures form share URL
3. Edit draft `r7197096571161040568` in Gmail to replace `FORM_URL_PLACEHOLDER` with the share URL
4. Review draft in Gmail → **Send when satisfied**

**When survey responses arrive (target: late July):**
1. Share responses with Hale
2. Hale fills `dossiers/Kuklinski_excursion_picklist_TEMPLATE.md` per couple
3. Dani builds TP 2.1 Excursion Recs email from picklist (target: before Jul 30)
4. Commander sends TP 2.1 to Kyle — ahead of Aug 2 booking window

**Aug 2, 2026:** Viking excursion booking window opens for Kyle/Rosalie + Roger/Nick (9593880 + 9593873). Book on window-open day — popular tours sell out. Josh/Erica (9595029) window opens Sep 23 — coordinate with Kyle to confirm same tours available.

---

## FILES PRODUCED

| File | Type | Status |
|------|------|--------|
| `dossiers/Kuklinski_VikingMars_Panama_Dec2026_Excursions.md` | Appendix appended | ✅ |
| `cache/kuklinski_form_BLOCKER.md` | Blocker / Commander action | ✅ |
| `dossiers/Kuklinski_excursion_picklist_TEMPLATE.md` | Stage 2 template | ✅ |
| `drafts/kuklinski_excursion_survey_intro_dani.html` | Name-corrected source | ✅ |
| `cache/kuklinski_build_report.md` | This file | ✅ |
| Gmail draft `r7197096571161040568` | Kyle email, staged | ✅ Labeled |

---

*Build log · Hale · 2026-06-19 · Model: claude-sonnet-4-6*
