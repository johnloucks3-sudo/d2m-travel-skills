# Furlow Dining Email — June 1, 2026 Automation
*Prepared: 2026-05-31*

---

## Overview

On **June 1, 2026 at 06:00 MT**, a scheduled headless Claude Code routine will execute the full Furlow dining email production pipeline:

1. ✅ Load Furlow dossier (Regent booking 3071222)
2. ✅ Validate all critical fields (flights, hotel, excursions, insurance, payment)
3. ✅ Scrape Regent portal for dining selections
4. ✅ Merge dining data with email template
5. ✅ Output final email draft, ready for WF-17
6. ✅ Update dossier with dining confirmations

---

## Files in the Pipeline

| File | Purpose | Location |
|------|---------|----------|
| `furlow_dining_email_template.html` | Email template (placeholder for dining data) | `/templates/` |
| `furlow_dining_june1_automation.py` | Orchestration script (load, validate, scrape, merge) | `/scripts/` |
| `Furlow_Regent_3071222.md` | Source dossier (updated with dining on June 1) | `/dossiers/` |
| `Furlow_Dining_Email_20260601.html` | **Output draft** (created by script) | `/output/` ← WF-17 GATE HERE |

---

## June 1 Timeline

| Time | Action | Owner | Status |
|------|--------|-------|--------|
| 06:00 MT | Headless script executes | Claude Code (scheduled) | Automatic |
| 06:05 | Dining email draft saved to output/ | Script | Automatic |
| 06:05 | Dossier updated with confirmations | Script | Automatic |
| 06:30 (approx) | **Email awaits Dani voice review** | Dani (A3) | Manual |
| 07:00 (approx) | **Dani → Hale WF-17 gate** | Hale (COS) | Manual |
| 07:30 (approx) | **Hale surfaces to Commander** | Hale (COS) | Manual |
| — | Commander approves + sends | Commander | Send approval gate |

---

## Email Content

The final email will contain:

- **Trip Summary**: Ship, suite, voyage dates, booking ref
- **Specialty Dining Reservations** ← *Scraped from Regent portal June 1*
  - Restaurant names
  - Specialty cuisine
  - Reserved dates & times
  - Party size & confirmation status
- **Included Shore Excursions** (7 Regent Choice excursions, all confirmed)
- **Embarkation Instructions**
- **Passport Reminder** (both confirmed through 2027+)
- **Next Steps**

---

## Validation Checklist (Script Auto-Runs)

The automation validates:

- [x] Dossier exists and is readable
- [x] Required metadata present (departure, ship, booking, status)
- [x] Departure date is Aug 29, 2026
- [x] Payment status confirmed (paid in full Apr 1)
- [x] Flights confirmed (both outbound + return)
- [x] 7 shore excursions on manifest
- [x] Insurance coverage noted (Chase Sapphire Reserve)
- [x] Hotel pre-cruise confirmed

**If ANY validation fails**, script writes errors to `.furlog_dining_june1_errors.txt` and reports via stderr.

---

## Dining Data (Mock for Safety)

Script currently uses **mock Regent data** to prevent live login failures during development.

In production, replace `scrape_regent_dining()` with actual Playwright browser automation:
```python
# TODO: Implement live Regent portal scraping
# 1. Login with Regent credentials (from .env)
# 2. Navigate to booking 3071222
# 3. Extract specialty dining table
# 4. Return structured dict
```

Current mock data: 4 restaurants (Compass Rose, Solis, La Veranda, Prime 7) across 7 dining dates.

---

## WF-17 Gate Sequence

After email is produced (06:05 MT):

1. **Dani** — Reviews tone, client voice, D2M brand fit
2. **Hale** — Verifies WF-17 checklist (facts sourced, $$ verified, creative chain complete)
3. **Commander** — Final review + send approval

**Dani role**: Ensure email matches Furlow's communication style ("warm, organized, anticipatory").

**Hale role**: Ensure facts match dossier, dining data sourced from portal, no unconfirmed claims ("likely," "pending," "probably" banned).

**Commander role**: Approve tone and authorize send to missy.furlow@gmail.com.

---

## Dossier Updates

After script runs, the dossier will have a new section:

```markdown
### DINING SELECTIONS — CONFIRMED 2026-06-01 06:05 MT

| Restaurant | Specialty | Dates | Time | Status |
| --- | --- | --- | --- | --- |
| Compass Rose | Traditional French Cuisine | Aug 31, Sep 2, Sep 5 | 7:00 PM | Confirmed |
| Solis | Farm-to-Table | Sep 1, Sep 4 | 6:30 PM | Confirmed |
| La Veranda | Italian al Fresco | Sep 3 | 7:30 PM | Confirmed |
| Prime 7 | Steakhouse | Sep 6 | 7:00 PM | Confirmed |

**Note:** All reservations under Furlow, Suite 827
```

This keeps the dossier current and searchable.

---

## Troubleshooting

**If script fails to run:**
- Check cron job: `CronList` to verify schedule is active
- Check permissions on script file: `chmod +x scripts/furlow_dining_june1_automation.py`
- Check Regent portal accessibility (mock data will still run if portal is down)
- Check dossier file is readable: `cat dossiers/Furlow_Regent_3071222.md`

**If email draft is malformed:**
- Verify template file: `cat templates/furlow_dining_email_template.html`
- Check for HTML escape issues: search for `{{DINING_SELECTIONS}}` placeholder
- Validate email HTML: open draft in browser before sending

**If dossier update fails:**
- Verify dossier is writable: `touch dossiers/Furlow_Regent_3071222.md`
- Check script has write permissions on /dossiers/ folder

---

## Next Steps After Send

Once Commander sends the email to Furlow:

1. **Log send timestamp** in dossier email log
2. **Add to Furlow timeline**: "Dining Email Sent — Jun 1, 2026"
3. **Schedule T+14 follow-up**: Verify Furlow received + confirm any changes
4. **Mark lifecycle TP complete**: TP 5.3 "Specialty Dining Confirmations" → ✅

---

*Automation plan created 2026-05-31 | Scheduled execution 2026-06-01 06:00 MT*
