---
name: itinerary
description: "Generate a full luxury itinerary for a client booking. Includes photo sourcing, port narratives, ship details, excursion recommendations, dining, and HTML output. Triggers on: itinerary, generate itinerary, build itinerary, create itinerary, trip itinerary, port guide, day by day, shore excursions, cruise itinerary"
---

# /itinerary — Luxury Itinerary Generation

You execute this procedure yourself. Full Wing procedure with photo sourcing.
**Photos are required. Never surface an itinerary without photos.**

## Usage

```
/itinerary [client-name]
```

## Step 1 — Source Photos FIRST (before generating)

Photos must be sourced before generation. Identify the ship, then find its image directory.

### Local ship image directories:
```bash
ls /home/john/Thunderbird/storage/output/
# Ship-specific: storage/output/[ship]_imgs/
# Example: storage/output/grandeur_imgs/
ls /home/john/Thunderbird/storage/output/grandeur_imgs/
```

### Google Drive ship photo folders (canonical archive):
| Ship | Drive Folder ID |
|---|---|
| Silver Muse | 1tzCKikPcE5s8zTpwEDKUr5ImEd9Eq8ML |
| Silver Nova | 1vrOoeIc0RObWKMhGzcdcOO_wVHWcuFaA |
| Viking Mars | 1iJSlwwk_wdOzbh9cBbbJhPPGFcV28ZYVc |
| Seven Seas Grandeur | 1e-0rbVOhvI-jB4WPwBf1DBu591s0uXJ1 |

```bash
# Download from Drive if not local:
python3 -c "
import sys; sys.path.insert(0, '/home/john/Thunderbird')
# Use MCP tool: mcp__claude_ai_Google_Drive__download_file_content
# Or: scripts/drive_upload_robust.py for upload; use MCP for reads
"
# MCP read: mcp__claude_ai_Google_Drive__list_folder_items (folder_id above)
```

Target: 3 photos per day minimum. Use ACTUAL ship photos — never generic stock.

## Step 2 — Read Client Dossier

```bash
cat /home/john/Thunderbird/dossiers/[DOSSIER_FILE]
```

Extract for itinerary:
- All port stops + dates
- Ship name + cruise line
- Cabin category
- Excursion interests (adventure level, mobility, preferences)
- Dining preferences
- Special occasions (anniversary, birthday, etc.)
- Any pre/post extensions

## Step 3 — Run the Generator

```bash
cd /home/john/Thunderbird
python3 itinerary/luxury_itinerary_generator.py
```

If the generator needs client-specific input, check its argparse:
```bash
python3 itinerary/luxury_itinerary_generator.py --help
```

Also check for client-specific generator scripts:
```bash
ls /home/john/Thunderbird/itinerary/ | grep -i "[client]"
# e.g., generate_mcleod_itinerary.py, build_westbrook_itinerary.py
```

Use the client-specific script if it exists.

## Step 4 — Port Narrative (Luna layer)

For each port, write:
- **Opening hook** — sensory, specific to this port. Not "Beautiful city of X."
- **What to do** — 2-3 curated options matching client's interests from dossier
- **D2M recommendation** — one specific, confident pick with reasoning
- **Insider detail** — one thing a first-timer wouldn't know
- **Dining** — one specific restaurant or venue name if available

Tone: warm expert. You've been there. You know them. You chose this for a reason.

## Step 5 — Ship Section

For each ship, include:
- Ship overview (tonnage, passengers, crew ratio — luxury context)
- Suite/cabin description matching their category
- Key dining venues by name (not "multiple dining options")
- Spa, pool deck, signature spaces
- What makes THIS ship different from a generic cruise ship

Use actual ship name throughout — never "the ship" or "your vessel."

## Step 6 — Excursion Recommendations

Per port, based on dossier interests:
- Adventure level match (active/moderate/relaxed)
- D2M curated pick (specific tour, not generic activity type)
- Booking timing advice (pre-purchase vs book onboard)
- Accessibility note if relevant

## Step 7 — HTML Output Format

```html
<!-- Full HTML itinerary — Gmail/print safe -->
<table width="700" cellpadding="0" cellspacing="0" 
       style="background-color:#f7f3ea;font-family:Georgia,serif;color:#0000ff;max-width:700px;margin:0 auto;">
  
  <!-- Header: D2M banner + client name + ship + dates -->
  
  <!-- Day-by-day sections with embedded photos -->
  <!-- Each day: date, port, photo, narrative, recommendations -->
  
  <!-- Ship section -->
  <!-- Excursion grid -->
  <!-- D2M contact + sig block -->
  
</table>
```

Images embedded as `<img src="[drive-url or local-path]" width="600">` — one per port minimum.

Output file: `/home/john/Thunderbird/output/[client]_itinerary_[date].html`

## Step 8 — Quality Gate Before Surfacing

- [ ] Every port has at least 1 photo
- [ ] All photos are ACTUAL ship/port photos (not stock)
- [ ] Port narratives match client's interests from dossier
- [ ] Ship section uses correct ship name throughout
- [ ] Dates and ports verified against booking
- [ ] D2M signature block present
- [ ] HTML validates (no broken tags, images load)

Then: `/email-draft` to wrap in proper email format for WF-17 gate.

## Common Issues + Fixes

| Issue | Fix |
|---|---|
| No local ship photos | Download from Drive folder IDs above via MCP |
| Generator script crashes | `cd /home/john/Thunderbird` first — path-sensitive |
| Wrong ship photos | Check ship name in dossier, match to exact folder |
| Grandeur photos sparse | Only 5 local — supplement from Drive folder + supplement with port photos |
| Photos not displaying in Gmail | Must use public URLs or base64 inline — not local file:// paths |
