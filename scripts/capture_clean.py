"""Clean re-pull: proper JSON parse (fixes UTF-8) for excursions + port descriptions from itinerary."""
import asyncio, json, re
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path('/home/john/Thunderbird')
COOKIE_FILE = ROOT / 'creds' / 'regent_cookies_oa.json'
BOOKING_URL = 'https://www.rssc.com/agent/myaccount/bookedcruise.aspx?EUQc5OJShNzRnf6WDNdRorwtMN96BHdNAoCRU76%2bXT%2fsOWFoWGyj%2fal2KN%2bqYiHit2tgnul78coeYRaj31f8gA%3d%3d'
OUT = ROOT / 'validations' / 'rssc_scrape'
BOOKED = ['GCM-021','CTG-021','PNT-012','QUZ-006','ACA-009','CSL-017','SAN-005']

def load_rssc_cookies(path):
    raw = json.loads(path.read_text()); out=[]
    for c in raw:
        if 'rssc.com' not in c.get('domain',''): continue
        nc={k:v for k,v in c.items() if k!='sameSite'}
        if c.get('sameSite') in ('Strict','Lax','None'): nc['sameSite']=c['sameSite']
        out.append(nc)
    return out

def clean_html(s):
    if not s: return ''
    s = re.sub(r'</li>', '', s)
    s = re.sub(r'<li>', '\n• ', s)
    s = re.sub(r'</?(ul|ol|p|br|div|span|strong|em)[^>]*>', '\n', s, flags=re.I)
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('&nbsp;',' ').replace('&amp;','&').replace('&#39;',"'").replace('&rsquo;',"'").replace('&ldquo;','"').replace('&rdquo;','"')
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n[ \t]+', '\n', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()

async def main():
    uv_raw = []
    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(viewport={'width':1440,'height':900})
        await ctx.add_cookies(load_rssc_cookies(COOKIE_FILE))
        page = await ctx.new_page()
        async def grab(resp):
            if 'UpdateVoyage' in resp.url:
                try: uv_raw.append(await resp.text())
                except Exception: pass
        page.on('response', lambda r: asyncio.create_task(grab(r)))
        await page.goto(BOOKING_URL, wait_until='domcontentloaded', timeout=45000)
        await page.wait_for_timeout(3500)

        # Port descriptions: open itinerary and pull each day's description.
        # The booking page renders an itinerary; capture full HTML + structured day blocks.
        await page.evaluate("() => { try { ShowItinView(); } catch(e){} }")
        await page.wait_for_timeout(2500)
        itin_html = await page.evaluate("() => document.body.innerHTML")
        # also trigger excursion customize for full UpdateVoyage
        for sel in ['text=SHORE','text=CUSTOMIZE']:
            try:
                for el in (await page.query_selector_all(sel))[:1]:
                    await el.click(); await page.wait_for_timeout(4000)
            except Exception: pass
        await page.wait_for_timeout(2000)
        await ctx.close(); await b.close()

    # Parse excursions cleanly from UpdateVoyage JSON
    excursions = {}
    ports = {}
    uv = max(uv_raw, key=len) if uv_raw else ''
    try:
        data = json.loads(uv)
        for port in data.get('ports', []):
            pname = port.get('name')
            ports[pname] = {'daysAtPort': port.get('daysAtPort'), 'hasReservation': port.get('hasSomeReservation'),
                            'description': clean_html(port.get('description','') or port.get('portDescription','') or '')}
            for e in port.get('excursions', []):
                code = (e.get('tourCode') or '').upper()
                if code in BOOKED:
                    excursions[code] = {
                        'title': e.get('title'),
                        'port': pname,
                        'duration': e.get('durations'),
                        'price': e.get('price'),
                        'highlights': clean_html(e.get('highlights','')),
                        'description': clean_html(e.get('description','')),
                    }
        parse_ok = True
    except Exception as ex:
        parse_ok = False
        print('JSON parse failed:', ex)

    # Port descriptions from itinerary HTML — Regent embeds them in day blocks
    port_descs = {}
    # match patterns like >Cabo San Lucas Details ... <description>
    for pname in ['George Town','Cartagena','Puntarenas','Puerto Quetzal','Acapulco','Cabo San Lucas','San Diego','Miami','Los Angeles']:
        # find "PNAME Details" or "PNAME" followed by a long descriptive paragraph
        m = re.search(re.escape(pname) + r'\s*Details?\s*</?\w*>?\s*(.{120,1400}?)(?:</|VIEW|DAY \d|<h)', itin_html, re.I|re.S)
        if not m:
            m = re.search(re.escape(pname) + r'.{0,40}?<[^>]*>\s*(This [^<]{120,1400})', itin_html, re.I|re.S)
        if m:
            port_descs[pname] = clean_html(m.group(1))

    result = {'excursions': excursions, 'ports_from_uv': ports, 'port_descriptions': port_descs}
    (OUT/'3122006_itinerary_background_clean.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))
    (OUT/'3122006_itinerary_raw.html').write_text(itin_html)

    print(f'UpdateVoyage parsed OK: {parse_ok} | excursions: {len(excursions)}/7')
    for code in BOOKED:
        e = excursions.get(code)
        if e:
            print(f'\n=== {code}: {e["title"]} ({e["duration"]}) ===')
            print('  HL:', (e["highlights"][:120].replace(chr(10),' / ')))
    print(f'\nPort descriptions extracted: {len(port_descs)}')
    for p, d in port_descs.items():
        print(f'  {p}: {d[:100]}')
    print(f'\nPort objects from UV (w/ desc): {sum(1 for v in ports.values() if v["description"])}/{len(ports)}')
    print('Saved clean JSON + raw itinerary HTML.')

if __name__ == '__main__':
    asyncio.run(main())
