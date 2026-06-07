---
name: cruise-cost-compare
description: >
  Pull cabin prices from multiple cruise lines, compare amenities side-by-side,
  and flag best-value options for client presentation. Works with Silversea, Regent,
  Seabourn, Cunard, Oceania, Viking, and Ponant. Use when asked to compare cruise
  prices, show cabin options, or identify best-value sailings for a client.
license: MIT
compatibility: Claude Code 2.0+, Claude Cowork, Cursor, Gemini CLI, Goose
metadata:
  author: Dreams2Memories Travel, LLC
  version: 0.1.0
  category: travel-operations
  vertical: luxury-cruise-travel
allowed-tools:
  - Bash
  - Read
  - Write
---

# Cruise Cost Compare — D2M Travel Operations

Side-by-side cabin price and amenity comparison across luxury cruise lines.

## Supported Lines

| Line | Tier | Data Source |
|------|------|-------------|
| Silversea | Ultra-luxury | TA portal / rssc_targeted_scrape.py |
| Regent Seven Seas | Ultra-luxury / all-inclusive | TA portal |
| Seabourn | Ultra-luxury | Manual / phone quote |
| Cunard | Premium / iconic | Web scrape |
| Oceania | Premium / culinary | Web scrape |
| Viking | Premium / cultural | Web scrape |
| Ponant | Expedition / boutique | Manual |

## Inputs Required

- Voyage dates (or sailing name)
- Ports/itinerary preference
- Number of travelers
- Cabin category preference (suite, veranda, etc.)
- Budget range (optional)

## Output

- Side-by-side comparison table (line, cabin, price, inclusions, availability)
- Best-value flag with D2M commission estimate
- Branded PDF quote ready for WF-17

## Process

1. Query available lines for the voyage window
2. Normalize pricing to per-person based on double occupancy
3. Compare inclusions (air credit, drinks, gratuities, shore excursions)
4. Apply D2M markup/commission calculation
5. Flag best value and Hale recommendation
6. Route to WF-17 for Commander review before client delivery

## Hard Rules

- ❌ NEVER quote a price without confirming availability
- ❌ NEVER omit inclusions — all-inclusive vs à la carte changes the true cost dramatically
- ❌ NEVER send to client without WF-17 gate

## scripts/

- `query_cruise_prices.py` — dispatches to line-specific scrapers
- `normalize_inclusions.py` — converts inclusions to $ equivalent for fair comparison
- `build_comparison_pdf.py` — D2M-stationery comparison table PDF
