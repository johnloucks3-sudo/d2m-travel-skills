"""Final: itinerary (with ship port times) from m58dynamic + port descriptions from /api/browse/v1/ports."""
import asyncio, json, re
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path('/home/john/Thunderbird/validations/rssc_scrape')

def clean(s):
    if not isinstance(s,str): return ''
    s = re.sub(r'<[^>]+>',' ',s)
    for a,b in [('&nbsp;',' '),('&amp;','&'),('&#39;',"'"),('&rsquo;',"'"),('&ldquo;','"'),('&rdquo;','"'),('&quot;','"'),('&ndash;','–'),('&#8217;',"'"),('&#8211;','–')]:
        s=s.replace(a,b)
    return re.sub(r'\s+',' ',s).strip()

async def main():
    # itinerary from saved summary
    summ = json.loads((OUT/'voyage_summary_full.json').read_text())
    itin = summ.get('m58dynamic',{}).get('itinerary',{}).get('items',[])
    itinerary = [{
        'day':i.get('day'),'date':i.get('date'),'city':i.get('city'),'country':i.get('country'),
        'atSea':i.get('isAtSea'),'arrive':i.get('arrivalTime'),'depart':i.get('departureTime')
    } for i in itin]

    # fetch ports catalog
    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0')
        page = await ctx.new_page()
        await page.goto('https://www.rssc.com/cruises/GRA261229/summary', wait_until='domcontentloaded', timeout=40000)
        await page.wait_for_timeout(2500)
        ports_raw = await page.evaluate('''async () => {
            const r = await fetch('/api/browse/v1/ports', {headers:{'Accept':'application/json'}});
            return await r.text();
        }''')
        await ctx.close(); await b.close()
    (OUT/'ports_catalog_full.json').write_text(ports_raw)
    ports = json.loads(ports_raw)

    # our voyage ports (cities)
    want = {}
    for it in itinerary:
        if not it['atSea'] and it['city']:
            want[it['city']] = None
    # also map known aliases
    descs = {}
    def walk(o):
        if isinstance(o, dict):
            nm = o.get('name') or o.get('portName') or o.get('title') or o.get('cityName') or o.get('displayName')
            ds = o.get('description') or o.get('longDescription') or o.get('overview') or o.get('portDescription') or o.get('body') or o.get('copy')
            if isinstance(nm,str) and isinstance(ds,str) and len(clean(ds))>80:
                descs[nm.strip()] = clean(ds)
            for v in o.values(): walk(v)
        elif isinstance(o,list):
            for v in o: walk(v)
    walk(ports)

    # match voyage cities to catalog descriptions
    matched = {}
    for city in want:
        for nm, ds in descs.items():
            if city.lower() in nm.lower() or nm.lower() in city.lower():
                matched[city] = ds; break

    result = {'itinerary': itinerary, 'port_descriptions': matched,
              'catalog_total_ports': len(descs), 'unmatched_cities':[c for c in want if c not in matched]}
    (OUT/'3122006_itinerary_and_ports_FINAL.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))

    print('=== ITINERARY (ship port times) ===')
    for it in itinerary:
        if it['atSea']:
            print(f"  Day {it['day']:>2} {it['date']:>7}  — At Sea —")
        else:
            print(f"  Day {it['day']:>2} {it['date']:>7}  {it['city']}, {it['country']}  arr {it['arrive'] or '—'} / dep {it['depart'] or '—'}")
    print(f'\n=== PORT DESCRIPTIONS: {len(matched)}/{len(want)} matched (catalog has {len(descs)} ports) ===')
    for c,dsc in matched.items():
        print(f'\n--- {c} ---\n{dsc[:240]}')
    if result['unmatched_cities']:
        print('\nUnmatched:', result['unmatched_cities'])
        # show sample catalog names to debug
        print('Sample catalog port names:', list(descs.keys())[:15])

asyncio.run(main())
