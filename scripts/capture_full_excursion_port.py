"""
Comprehensive capture for Loucks 3122006 itinerary background:
- Full highlights + description for all 7 booked excursions (from UpdateVoyage)
- Port descriptions for each stop (from itinerary day-detail + any destination API)
Saves structured JSON for dossier write.
"""
import asyncio, json, re, time
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

def strip_html(s):
    s = re.sub(r'<li>', '\n• ', s or '')
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('\r','').replace('&nbsp;',' ').replace('&amp;','&').replace('´',"'").replace('&#39;',"'")
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()

async def main():
    uv_bodies = []
    port_api = []
    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(viewport={'width':1440,'height':900})
        await ctx.add_cookies(load_rssc_cookies(COOKIE_FILE))
        page = await ctx.new_page()
        async def grab(resp):
            u = resp.url
            try:
                if 'UpdateVoyage' in u:
                    uv_bodies.append(await resp.text())
                elif any(k in u.lower() for k in ['destination','port','itinerary','daydetail','getday','geo']):
                    ct = resp.headers.get('content-type','')
                    if 'json' in ct or 'html' in ct:
                        body = await resp.text()
                        if len(body) < 50000:
                            port_api.append({'url':u,'body':body[:8000]})
            except Exception: pass
        page.on('response', lambda r: asyncio.create_task(grab(r)))

        await page.goto(BOOKING_URL, wait_until='domcontentloaded', timeout=45000)
        await page.wait_for_timeout(3500)
        for sel in ['text=SHORE','text=CUSTOMIZE']:
            try:
                for el in (await page.query_selector_all(sel))[:1]:
                    await el.click(); await page.wait_for_timeout(4000)
            except Exception: pass
        await page.wait_for_timeout(2000)

        day_desc = await page.evaluate('''() => {
            const out = [];
            // common selectors for itinerary day detail text
            document.querySelectorAll('[class*=itin], [class*=day], [class*=port], [id*=itin], [id*=day]').forEach(el => {
                const t = (el.innerText||'').trim();
                if (t.length > 120 && t.length < 2000 && /[a-z]{40}/.test(t)) out.push(t);
            });
            return out.slice(0, 40);
        }''')
        full_text = await page.evaluate('() => document.body.innerText')
        await ctx.close(); await b.close()

    uv = max(uv_bodies, key=len) if uv_bodies else ''
    excursions = {}
    for code in BOOKED:
        idx = uv.lower().find(f'"tourcode":"{code.lower()}"')
        if idx == -1: continue
        win = uv[max(0,idx-700):idx+4000]
        def grab_field(name):
            m = re.search(r'"%s":"((?:[^"\\]|\\.)*)"' % name, win)
            return m.group(1) if m else ''
        excursions[code] = {
            'title': grab_field('title'),
            'duration': grab_field('durations'),
            'price': grab_field('price'),
            'highlights': strip_html(grab_field('highlights').encode().decode('unicode_escape', errors='ignore')),
            'description': strip_html(grab_field('description').encode().decode('unicode_escape', errors='ignore')),
        }

    result = {
        'excursions': excursions,
        'port_api_captures': port_api,
        'day_descriptions_dom': day_desc,
        'full_page_text': full_text[:30000],
    }
    (OUT/'3122006_itinerary_background.json').write_text(json.dumps(result, indent=2, default=str))

    print(f'UpdateVoyage bodies: {len(uv_bodies)} (max {len(uv)} chars)')
    print(f'Excursions parsed: {len(excursions)}/7')
    for code, e in excursions.items():
        print(f'\n=== {code}: {e["title"]} ({e["duration"]}, {e["price"]}) ===')
        print('HIGHLIGHTS:', (e["highlights"][:200] or "(none)"))
        print('DESC:', (e["description"][:200] or "(none)"))
    print(f'\nPort API captures: {len(port_api)}')
    for p in port_api[:8]:
        print('  ', p['url'][:90])
    print(f'\nDOM day descriptions found: {len(day_desc)}')
    for d in day_desc[:3]:
        print('  ---', d[:150].replace(chr(10),' '))
    print('\nSaved:', OUT/'3122006_itinerary_background.json')

if __name__ == '__main__':
    asyncio.run(main())
