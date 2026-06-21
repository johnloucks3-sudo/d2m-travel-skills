"""Reliable UpdateVoyage pull → clean JSON → 7 booked excursions full detail. Saves raw UV too."""
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

def clean(s):
    if not s: return ''
    s = re.sub(r'</li>','',s); s = re.sub(r'<li>','\n• ',s)
    s = re.sub(r'</?(ul|ol|p|br|div|span|strong|em|h\d)[^>]*>','\n',s,flags=re.I)
    s = re.sub(r'<[^>]+>','',s)
    s = (s.replace('&nbsp;',' ').replace('&amp;','&').replace('&#39;',"'")
          .replace('&rsquo;',"'").replace('&ldquo;','"').replace('&rdquo;','"').replace('&quot;','"'))
    s = re.sub(r'[ \t]+',' ',s); s = re.sub(r'\n[ \t]+','\n',s); s = re.sub(r'\n{3,}','\n\n',s)
    return s.strip()

async def main():
    uv_raw = []
    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(viewport={'width':1440,'height':900})
        await ctx.add_cookies(load_rssc_cookies(COOKIE_FILE))
        page = await ctx.new_page()
        page.on('response', lambda r: asyncio.create_task(
            (async_grab := (lambda rr: rr))(None)) if False else None)
        async def grab(resp):
            if 'UpdateVoyage' in resp.url:
                try: uv_raw.append(await resp.text())
                except Exception: pass
        page.on('response', lambda r: asyncio.create_task(grab(r)))

        await page.goto(BOOKING_URL, wait_until='domcontentloaded', timeout=45000)
        await page.wait_for_timeout(3000)
        # robust: try several ways to enter excursion customize, retry until UV captured
        for attempt in range(4):
            if uv_raw: break
            for sel in ['text=SHORE','text=CUSTOMIZE','text=Book your excursions','a:has-text("CUSTOMIZE")']:
                try:
                    els = await page.query_selector_all(sel)
                    if els:
                        await els[0].click()
                        await page.wait_for_timeout(5000)
                        if uv_raw: break
                except Exception: pass
            await page.wait_for_timeout(2000)
        await ctx.close(); await b.close()

    uv = max(uv_raw, key=len) if uv_raw else ''
    if not uv:
        print('FAILED: UpdateVoyage not captured. uv_raw len:', len(uv_raw)); return
    (OUT/'3122006_UpdateVoyage_raw.json').write_text(uv)
    data = json.loads(uv)
    excursions = {}
    for port in data.get('ports', []):
        for e in port.get('excursions', []):
            code = (e.get('tourCode') or '').upper()
            if code in BOOKED:
                excursions[code] = {
                    'title': e.get('title'), 'port': port.get('name'),
                    'duration': e.get('durations'), 'price': e.get('price'),
                    'highlights': clean(e.get('highlights','')),
                    'description': clean(e.get('description','')),
                }
    (OUT/'3122006_excursions_clean.json').write_text(json.dumps(excursions, indent=2, ensure_ascii=False))
    print(f'Captured UV ({len(uv)} chars), parsed {len(excursions)}/7 excursions CLEAN:')
    for code in BOOKED:
        e = excursions.get(code)
        if e: print(f'\n=== {code} {e["title"]} ===\nHL: {e["highlights"][:140]}')
    print('\nSaved 3122006_excursions_clean.json')

if __name__ == '__main__':
    asyncio.run(main())
