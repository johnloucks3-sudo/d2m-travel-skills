---
name: fare-watch
description: "Active client fare monitoring for all current bookings. Read watch list, run price checks, record history, trigger alerts on drops or spikes, surface to Commander. Triggers on: fare watch, price watch, fare check, price check, check fares, monitor fares, fare alert, price alert, fare drop, price drop, cruise price, flight price watch, watch price, check prices, price history, fare history, booking prices, are prices down, has the price changed, flight alert, cruise alert, watch list"
---

# /fare-watch — Active Client Fare Monitoring

You execute this procedure yourself. This is Wing-owned monitoring — not a handoff to Claude Code.
PII fence: never send client names, booking refs, or prices to DeepSeek/external LLMs.
Use /ask-opus only if you need Opus-level judgment on a complex alert decision.

## Usage

```
/fare-watch                     # Full daily check — all active watches
/fare-watch list                # Show all active watches + current prices
/fare-watch check [watch_id]    # Check one specific watch
/fare-watch history [watch_id]  # Price history for one watch
/fare-watch add                 # Add a new watch (see Step 6)
/fare-watch alerts              # Show watches with active alerts (vs baseline)
```

---

## Step 1 — Read the Watch List

```python
import sys
sys.path.insert(0, '/home/john/Thunderbird/core/travel')
from thunderbird_fare_watch import list_watches
import json

result = list_watches(active_only=True)
print(json.dumps(result, indent=2))
```

Or read the raw JSON directly:
```bash
cat /home/john/Thunderbird/core/travel/data/fare_watches.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
active = {k: v for k, v in d.items() if v.get('active')}
print(f'Active watches: {len(active)}')
for k, w in active.items():
    chg = ((w['current_price_pp'] - w['baseline_price_pp']) / w['baseline_price_pp'] * 100) if w['baseline_price_pp'] else 0
    print(f'  {k}: {w[\"label\"]} | \${w[\"current_price_pp\"]:,.0f}/pp | vs baseline {chg:+.1f}%')
"
```

Extract from result:
- `count` — total active watches (currently 23)
- Each watch: `id`, `label`, `type` (flight/cruise), `provider`, `travel_date`, `price_pp`, `total`, `vs_baseline`, `last_checked`
- Watches with `vs_baseline` significantly positive/negative → flag for investigation

### Current Active Watches (as of 2026-06-01)

| Watch ID | Client | Type | Travel Date | Passengers |
|---|---|---|---|---|
| furlow-grandeur-scandinavia-cruise | Furlow | cruise | 2026-08-29 | 2 |
| nichols-grandeur-scandinavia-cruise | Nichols | cruise | 2026-08-29 | 2 |
| ely-darrow-grandeur-scandinavia-cruise | Ely/Darrow | cruise | 2026-08-29 | 2 |
| kuklinski-viking-panama-dv1 | Kuklinski (4 pax) | cruise | 2026-12-17 | 4 |
| kuklinski-viking-panama-v1 | Morton/Dodge | cruise | 2026-12-17 | 2 |
| kuklinski-flights-ric-pty | Kuklinski Group | flight | 2026-12-17 | 4 |
| morton-dodge-flights-rsw-pty | Morton/Dodge | flight | 2026-12-17 | 2 |
| lyons-splendor-athens-ny-cruise | Lyons | cruise | varies | 2 |
| mcleod-silver-muse-med-jun2026 | McLeod/McGlasson | cruise | 2026-06-18 | 2 |
| mcleod-regent-grandeur-dec2026 | McLeod/McGlasson | cruise | 2026-12-19 | 2 |
| mcleod-flights-den-fco-jun2026 | McLeod/McGlasson | flight | 2026-06-18 | 2 |
| mcleod-flights-vce-den-jul2026 | McLeod/McGlasson | flight | 2026-07-06 | 2 |
| loucks-regent-grandeur-panama-dec2026 | Loucks | cruise | 2026-12-29 | 2 |
| viking-kuklinski-panama-2026-12-17 | Kuklinski/Morton group | cruise | 2026-12-17 | varies |
| flight-kuklinski-cos-fll-2026-12-15 | Kuklinski/Morton | flight | 2026-12-15 | varies |
| grandeur-scandinavia-group-flights | Grandeur Scandinavia Group | flight | 2026-08-29 | varies |
| ely-flights | Ely | flight | 2026-08-29 | 2 |
| furlow-flights | Furlow | flight | 2026-08-29 | 2 |
| kuklinski-flights | Kuklinski | flight | 2026-12-17 | varies |
| loucks-personal-flights | Loucks Personal | flight | varies | 2 |
| mcleod-mcglasson---silver-muse-flights | McLeod McGlasson | flight | 2026-06-18 | 2 |
| morton-flights | Morton | flight | 2026-12-17 | 2 |
| nichols-flights | Nichols | flight | 2026-08-29 | 2 |

---

## Step 2 — Check Current Prices (Cruise Watches)

For cruise watches, check the cruise line's booking portal directly.

### Silversea (Silver Muse, Silver Nova)
```bash
# Browse to Silversea to find current pricing
# URL pattern: https://www.silversea.com/cruises/[route]/[voyage-code].html
# Look for "per person" pricing on the specific voyage + cabin category
```

### Regent Seven Seas (Grandeur, Splendor)
```bash
# Browse to Regent portal
# URL pattern: https://www.rssc.com/voyages/[voyage-code]
# Match cabin category to client's booking: Suite vs Veranda vs Penthouse
```

### Viking (Viking Mars)
```bash
# Browse to Viking portal
# URL pattern: https://www.vikingcruises.com/[voyage-code]
# Match: DV1 (Deluxe Veranda) vs V1 (Standard Veranda)
```

For each cruise watch, collect:
- Current price per person for the client's cabin category
- Any fare code or promotion active
- Availability status (open/waitlist/closed)

---

## Step 3 — Check Current Prices (Flight Watches)

For unbooked flight watches, use the flight price skill or run Centrav:

```bash
# Centrav B2B search (preferred for quotes)
python3 /home/john/Thunderbird/scripts/centrav_flights.py \
  --origin RIC --dest PTY \
  --date 2026-12-17 --passengers 4 --cabin economy

# Kayak consumer sanity check
# Use /flight-price skill for multi-source lookup
```

### Key Unbooked Flight Watches
| Watch ID | Route | Date | Pax | Alert Below |
|---|---|---|---|---|
| kuklinski-flights-ric-pty | RIC → PTY | 2026-12-17 | 4 | $425/pp |
| morton-dodge-flights-rsw-pty | RSW → PTY | 2026-12-17 | 2 | $320/pp |

**Centrav auth failure fix:**
```bash
python3 /home/john/Thunderbird/scripts/centrav_flights.py --centrav-login --headless false
# Manual login required when session expires (~weekly)
```

For booked flight watches (monitoring for fare drops that could trigger rebooking):
- Check same route/dates on Centrav + Kayak
- Compare to `baseline_price_pp` in the watch record
- Drops > 10% or below `alert_below` threshold → surface to Commander

---

## Step 4 — Record the Price Check

For each watch where you obtained a current price:

```python
import sys
sys.path.insert(0, '/home/john/Thunderbird/core/travel')
from thunderbird_fare_watch import check_fare
import json

# Record a price check and get alert analysis
result = check_fare(
    watch_id="kuklinski-viking-panama-dv1",
    new_price_pp=7999.0   # current price per person
)
print(json.dumps(result, indent=2))
```

`check_fare()` returns:
- `status`: "checked"
- `price_pp`: formatted current price
- `total`: total for all passengers
- `baseline_pp`: original baseline price
- `change_from_baseline`: percentage change from first recorded price
- `change_from_last`: dollar/direction change since last check
- `direction`: "up" / "down" / "unchanged"
- `alert`: populated if price crossed `alert_below` or `alert_above` threshold
- `recent_prices`: last 5 check dates + prices (if history exists)

The function automatically:
- Logs to `/home/john/Thunderbird/core/travel/data/fare_history.json`
- Updates `current_price_pp` and `last_checked` in `fare_watches.json`
- Sets `alert_triggered` in history entry if threshold crossed

---

## Step 5 — Evaluate Alerts

### Alert Threshold Reference (Active Watches)
| Watch ID | Current | Baseline | Alert Below | Status |
|---|---|---|---|---|
| furlow-grandeur-scandinavia-cruise | $16,499/pp | $9,618/pp | $8,656/pp | +71.5% above baseline |
| nichols-grandeur-scandinavia-cruise | $15,299/pp | $9,448/pp | $8,503/pp | +61.9% above baseline |
| ely-darrow-grandeur-scandinavia-cruise | $18,499/pp | $10,320/pp | $9,288/pp | +79.3% above baseline |
| kuklinski-viking-panama-dv1 | $7,999/pp | $3,799/pp | $3,419/pp | +110.6% above baseline |
| kuklinski-flights-ric-pty | $852/pp | $550/pp | $425/pp | +55.0% above baseline |
| morton-dodge-flights-rsw-pty | $867/pp | $420/pp | $320/pp | +106.4% above baseline |
| mcleod-flights-vce-den-jul2026 | $2,635/pp | $3,200/pp | $2,880/pp | BELOW alert threshold |
| loucks-regent-grandeur-panama-dec2026 | $12,949/pp | $12,899/pp | $11,609/pp | monitoring |
| flight-kuklinski-cos-fll-2026-12-15 | $290/pp | $450/pp | $350/pp | BELOW alert threshold |

### Alert Triage
- **`alert` field populated** → confirmed threshold crossing → Commander notification required
- **`vs_baseline` > +30%** → market has moved significantly; note in summary but no alert unless below threshold
- **`vs_baseline` negative** → price dropped below original booking price → flag to Commander for potential rebooking
- **Booked client + price drop > 10%** → research cancellation/rebook option before surfacing

**Harlan financial sign-off required** before surfacing any $ recommendation to Commander:
1. Portal balance for client
2. Portal FPD confirmed
3. Dossier vs portal delta check
4. Root cause any delta
5. Credits/deposit verified
6. Sign-off: "Confirmed: $X as of [date], source: [portal/TESS]"

---

## Step 6 — Get Price History for a Watch

```python
import sys
sys.path.insert(0, '/home/john/Thunderbird/core/travel')
from thunderbird_fare_watch import get_fare_history
import json

result = get_fare_history(
    watch_id="mcleod-silver-muse-med-jun2026",
    limit=30  # max entries to return
)
print(json.dumps(result, indent=2))
```

Returns:
- `summary`: min, max, avg, latest price, data_points count
- `history`: list of {date, price_pp, total, change, alert} entries

Raw history file: `/home/john/Thunderbird/core/travel/data/fare_history.json`

---

## Step 7 — Add a New Watch

```python
import sys
sys.path.insert(0, '/home/john/Thunderbird/core/travel')
from thunderbird_fare_watch import add_watch
import json

result = add_watch(
    watch_id="new-client-cruise-2026",          # unique slug, lowercase, hyphens
    watch_type="cruise",                         # "flight", "cruise", or "hotel"
    label="Client Name — Ship Route (Booking #)", # human-readable
    provider="Regent Seven Seas",
    route="Lisbon to Barcelona",
    travel_date="2026-09-05",                    # YYYY-MM-DD
    current_price_pp=9500.0,                     # price per person USD
    passengers=2,
    alert_below=8550.0,                          # 90% of baseline = good alert trigger
    alert_above=None,                            # optional: alert if price spikes
    notes="Booking ref 12345. Suite category. FPD 2026-07-01."
)
print(json.dumps(result, indent=2))
```

Conventions:
- `watch_id`: `[client-slug]-[ship]-[route]-[type]` — lowercase, hyphens only
- `alert_below`: typically 90% of baseline (10% drop triggers alert)
- Set `alert_above` for unbooked watches where you want to know if price spikes before client decides
- `notes`: include booking ref, cabin category, FPD, insurance status, key flags

---

## Step 8 — Deactivate a Watch

```python
import sys
sys.path.insert(0, '/home/john/Thunderbird/core/travel')
from thunderbird_fare_watch import remove_watch
import json

# Deactivate (keeps history, marks inactive)
result = remove_watch(watch_id="westbrook-silver-nova-pacific", hard_delete=False)

# Hard delete (removes entry entirely — use only if watch was added in error)
result = remove_watch(watch_id="bad-watch-id", hard_delete=True)

print(json.dumps(result, indent=2))
```

Deactivate (not delete) when:
- Booking has departed
- Client cancelled
- Watch is superseded by a more specific watch

---

## Step 9 — Write Summary and Surface to Commander

After completing all checks, write the summary:

```bash
# Update the last_check.json
python3 -c "
import json
from datetime import datetime
from pathlib import Path

summary = {
    'status': 'complete',
    'completed_at': datetime.now().isoformat(),
    'watches_total': 23,
    'watches_checked': 0,   # fill in
    'alerts': [],            # fill in triggered alerts
    'warnings': [],          # fill in auth failures or skipped watches
    'errors': [],            # fill in
}
Path('/home/john/Thunderbird/OpsCenter/fare_watches/last_check.json').write_text(
    json.dumps(summary, indent=2)
)
print('Summary written.')
"

# Append one line to fare_watch.log
echo "$(date '+%Y-%m-%d %H:%M') — Checked X watches. Alerts: Y. Notes: [summary]" \
  >> /home/john/Thunderbird/OpsCenter/fare_watches/fare_watch.log
```

### Commander Notification — Alert Triggered
If any `alert` field was populated in Step 4, surface to Commander via draft in d2mconcierge:

```python
import sys
sys.path.insert(0, '/home/john/Thunderbird')
from core.email.thunderbird_gmail import gmail_create_draft_sync

# Harlan sign-off must be complete before this draft is created
body = """
<html><body style="background:#f7f3ea;font-family:Georgia,serif;color:#0000ff;">
<h2>Fare Watch Alert — [Watch Label]</h2>
<p><strong>Alert:</strong> [alert text from check_fare result]</p>
<p><strong>Current price:</strong> [price_pp] / [total]</p>
<p><strong>Baseline:</strong> [baseline_pp]</p>
<p><strong>Change:</strong> [change_from_baseline]</p>
<p><strong>Harlan confirmed:</strong> $X as of [date], source: [portal/TESS]</p>
<p><strong>Recommended action:</strong> [Hale recommendation]</p>
<p>— V. Hale, VCS</p>
</body></html>
"""

result = gmail_create_draft_sync(
    to="johnloucks3@gmail.com",
    subject="Fare Alert — [Client] [Watch Label]",
    body=body,
)
print(result)
```

**Note:** Internal fare alerts go to `johnloucks3@gmail.com` directly — this is within-wing communication. No WF-17 gate required for the alert itself.

**WF-17 gate applies** only if the alert triggers a recommended action that would result in a client-facing communication (rebooking notice, price match email, etc.).

---

## Step 10 — Run Integration Check (All Watches at Once)

The integration module checks all active cruise watches via the price monitor:

```python
import sys
sys.path.insert(0, '/home/john/Thunderbird/core/travel')
from fare_watch_integration import check_all_fare_watch_prices, check_all_fare_watch_prices
import json

# Check all active cruise watches via price monitor
result = check_all_fare_watch_prices()
print(json.dumps(result, indent=2))
# Returns: status, checked, updated, alerts, timestamp

# Get current alerts only (no live check — reads existing data)
from fare_watch_integration import register_fare_watch_integration_tools
# fare_watch_get_alerts() → returns watches with non-zero vs_baseline
```

Note: `check_all_fare_watch_prices()` requires `thunderbird_price_monitor` to be functional. If it fails, fall back to per-watch manual checks in Steps 2–4.

---

## Storage Files

| File | Purpose |
|---|---|
| `/home/john/Thunderbird/core/travel/data/fare_watches.json` | All watch records (active + inactive) |
| `/home/john/Thunderbird/core/travel/data/fare_history.json` | All price check history entries |
| `/home/john/Thunderbird/OpsCenter/fare_watches/last_check.json` | Latest daily check summary |
| `/home/john/Thunderbird/OpsCenter/fare_watches/fare_watch.log` | Append-only log of all check runs |
| `/home/john/Thunderbird/OpsCenter/fare_watches/current_task.md` | One-line human summary of last run |

---

## Quality Checklist

- [ ] `list_watches(active_only=True)` returned current 23 watches without error
- [ ] All cruise watches checked against live portal pricing
- [ ] All unbooked flight watches checked (RIC→PTY, RSW→PTY)
- [ ] `check_fare(watch_id, new_price_pp)` called for every watch with a current price
- [ ] History file updated (`fare_history.json` has new entries with today's timestamp)
- [ ] Any `alert` fields populated → Harlan 6-step sign-off completed
- [ ] Centrav auth failure logged if session expired (fix: `--centrav-login --headless false`)
- [ ] `last_check.json` written to `/home/john/Thunderbird/OpsCenter/fare_watches/`
- [ ] Summary appended to `fare_watch.log`
- [ ] Commander notified (johnloucks3@gmail.com) if any alert triggered
- [ ] WF-17 draft staged in d2mconcierge if alert requires client-facing action

---

## Common Issues + Fixes

| Issue | Symptom | Fix |
|---|---|---|
| Centrav session expired | `auth_error` in `last_check.json`, `kuklinski-flights-ric-pty` error | Run `python3 scripts/centrav_flights.py --centrav-login --headless false` — manual login required |
| `fare_watch_list` returns 0 watches | count=0 | Check `fare_watches.json` exists: `ls /home/john/Thunderbird/core/travel/data/` |
| `check_fare` returns "Watch not found" | `status: error` | Verify watch_id exactly matches key in `fare_watches.json` — IDs are case-sensitive |
| Module import fails | `ModuleNotFoundError: thunderbird_fare_watch` | Add `sys.path.insert(0, '/home/john/Thunderbird/core/travel')` before import |
| `fare_history.json` not updating | check_fare succeeds but history empty | Verify DATA_DIR is writable: `ls -la /home/john/Thunderbird/core/travel/data/` |
| Price monitor integration fails | `check_all_fare_watch_prices()` returns 0 updated | Fall back to per-watch manual checks (Steps 2–4). Log the failure in `last_check.json` warnings. |
| Gmail draft creation fails | `invalid_grant` or token error | OAuth token expired — refresh before retry: check `hale_state.json` wing_health.oauth_token |
| Alert fires on already-known spike | `alert_above` triggered on booked cruise where fare rose post-booking | These are informational only for booked cruises — note for Commander but no rebooking possible without cancellation penalty |

---

## Wing Authority Notes

- **Fare monitoring is Hale-owned.** No Commander approval needed to run checks or update history.
- **Alert surfacing to Commander** (johnloucks3@gmail.com) is pre-authorized — within-wing communication.
- **Any $ recommendation to Commander** (rebooking, price match, fare adjustment) requires Harlan 6-step sign-off before surfacing.
- **Client-facing communication** triggered by a fare alert (e.g., "great news, your cabin price dropped") requires the full 6-step creative chain + WF-17 gate. Commander sends. Wing does not.
- **Centrav B2B prices** contain wholesale rates — never share Centrav pricing directly with clients. Convert to retail or quote-inclusive only.
