"""
REGENT VOYAGE PUBLIC CAPTURE — port descriptions + ship arrival/departure times.
NO LOGIN NEEDED. Works for any Regent voyage code via the public browse API.

Usage:
  python3 scripts/regent_voyage_public.py --voyage SPL260811 [--out validations/rssc_scrape]

Voyage code = {SHIP3}{YYMMDD}, found in booking page or cruise ref (e.g. SPL260811A → SPL260811).
"""
import asyncio, json, re, argparse
from pathlib import Path
from playwright.async_api import async_playwright

def clean(s):
    if not isinstance(s,str): return ''
    s = re.sub(r'<[^>]+>',' ',s)
    for a,b in [('&nbsp;',' '),('&amp;','&'),('&#39;',"'"),('&rsquo;',"'"),('&ldquo;','"'),('&rdquo;','"'),('&quot;','"'),('&ndash;','–'),('&#8217;',"'"),('&#8211;','–'),('&#8212;','—')]:
        s=s.replace(a,b)
    return re.sub(r'\s+',' ',s).strip()

async def capture(voyage, out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0')
        page = await ctx.new_page()
        r = await page.goto(f'https://www.rssc.com/cruises/{voyage}/summary', wait_until='domcontentloaded', timeout=40000)
        await page.wait_for_timeout(2500)
        if r and r.status >= 400:
            print(f'Voyage page {voyage} returned {r.status} — check voyage code.')
        async def fetch(p):
            return await page.evaluate('''async (p) => {
                try { const r = await fetch(p, {headers:{'Accept':'application/json'}}); return await r.text(); }
                catch(e){ return ''; }
            }''', p)
        summary = await fetch(f'/api/browse/v1/cruises/{voyage}/summary')
        ports_raw = await fetch('/api/browse/v1/ports')
        await ctx.close(); await b.close()

    if not summary or len(summary) < 1000:
        print(f'FAILED: summary endpoint empty for {voyage}. Voyage code wrong or not published?'); return None
    (out/f'{voyage}_summary.json').write_text(summary)
    data = json.loads(summary)

    itin = []
    for mod in data.values():
        if isinstance(mod, dict) and isinstance(mod.get('itinerary'), dict):
            for i in mod['itinerary'].get('items', []):
                itin.append({'day':i.get('day'),'date':i.get('date'),'city':i.get('city'),
                             'country':i.get('country'),'atSea':i.get('isAtSea'),
                             'arrive':i.get('arrivalTime'),'depart':i.get('departureTime')})
            break

    descs = {}
    if ports_raw and len(ports_raw) > 1000:
        try:
            cat = json.loads(ports_raw)
            def walk(o):
                if isinstance(o, dict):
                    nm = o.get('name') or o.get('portName') or o.get('title') or o.get('cityName') or o.get('displayName')
                    ds = o.get('description') or o.get('longDescription') or o.get('overview') or o.get('portDescription') or o.get('body') or o.get('copy')
                    if isinstance(nm,str) and isinstance(ds,str) and len(clean(ds))>80:
                        descs[nm.strip()] = clean(ds)
                    for v in o.values(): walk(v)
                elif isinstance(o,list):
                    for v in o: walk(v)
            walk(cat)
        except Exception as e:
            print('ports catalog parse error:', e)

    matched = {}
    for it in itin:
        if not it['atSea'] and it['city']:
            for nm, ds in descs.items():
                if it['city'].lower() in nm.lower() or nm.lower() in it['city'].lower():
                    matched[it['city']] = ds; break

    result = {'voyage':voyage,'itinerary':itin,'port_descriptions':matched,
              'header': (data.get('m54dynamic',{}) or {}).get('headerText'),
              'catalog_ports': len(descs),
              'unmatched':[it['city'] for it in itin if not it['atSea'] and it['city'] and it['city'] not in matched]}
    (out/f'{voyage}_public_itinerary_ports.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))

    print(f'=== {voyage} · {result["header"]} ===')
    print(f'{len(itin)} itinerary days | {len(matched)} port descriptions | catalog {len(descs)} ports')
    print('\n--- ITINERARY (ship times) ---')
    for it in itin:
        if it['atSea']: print(f"  Day {it['day']:>2} {it['date']:>7}  — At Sea —")
        else: print(f"  Day {it['day']:>2} {it['date']:>7}  {it['city']}, {it['country']}  arr {it['arrive'] or '—'} / dep {it['depart'] or '—'}")
    if result['unmatched']:
        print('\nUnmatched ports (no catalog desc):', result['unmatched'])
    print(f'\nSaved {out}/{voyage}_public_itinerary_ports.json')
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--voyage', required=True)
    ap.add_argument('--out', default='/home/john/Thunderbird/validations/rssc_scrape')
    a = ap.parse_args()
    asyncio.run(capture(a.voyage, a.out))

if __name__ == '__main__':
    main()
