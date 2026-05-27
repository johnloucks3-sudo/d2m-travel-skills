#!/bin/bash
# Wave 4 CruiseMapper expansion — run new lines and merge into base output
# Usage: ./run_wave4_merge.sh
# Prereq: base T2_CRUISEMAPPER.json already exists with Wave 3 data

set -e
cd /home/john/Thunderbird

BASE_JSON="output/T2_CRUISEMAPPER.json"
WAVE4_JSON="output/T2_CRUISEMAPPER_WAVE4.json"
WAVE4_LINES="Windstar Azamara StarClippers SwanHellenic Hurtigruten FredOlsen Celestyal Emerald Ambassador HapagLloyd Aurora Quark Saga"

echo "[wave4] Checking base file..."
BASE_COUNT=$(python3 -c "import json; print(len(json.load(open('$BASE_JSON'))))" 2>/dev/null || echo "0")
if [ "$BASE_COUNT" -lt 100 ]; then
    echo "[wave4] ERROR: base file has only $BASE_COUNT records — Wave 3 scrape may not be done yet"
    exit 1
fi
echo "[wave4] Base file OK: $BASE_COUNT records"

echo "[wave4] Scraping Wave 4 lines: $WAVE4_LINES"
python3 scripts/cruise_intel/scrape_cruisemapper.py \
    --year 2026 --months 10 11 \
    --lines $WAVE4_LINES \
    --output "$WAVE4_JSON" \
    --verbose

WAVE4_COUNT=$(python3 -c "import json; print(len(json.load(open('$WAVE4_JSON'))))" 2>/dev/null || echo "0")
echo "[wave4] Wave 4 scraped: $WAVE4_COUNT new records"

echo "[wave4] Merging and deduplicating..."
python3 - << 'PYEOF'
import json
from pathlib import Path

base_path = Path('output/T2_CRUISEMAPPER.json')
wave4_path = Path('output/T2_CRUISEMAPPER_WAVE4.json')

base = json.loads(base_path.read_text())
wave4 = json.loads(wave4_path.read_text())

# Dedup key: ship name + departure date
seen = {(v['ship_name'], v['departure_date']) for v in base}
added = [v for v in wave4 if (v['ship_name'], v['departure_date']) not in seen]

merged = sorted(base + added, key=lambda v: v['departure_date'])
base_path.write_text(json.dumps(merged, indent=2))

print(f'  Base: {len(base)} | Wave4 new: {len(added)} | Total: {len(merged)}')
PYEOF

FINAL_COUNT=$(python3 -c "import json; print(len(json.load(open('$BASE_JSON'))))" 2>/dev/null || echo "0")
echo "[wave4] Final T2_CRUISEMAPPER.json: $FINAL_COUNT records"
echo "[wave4] Done."
