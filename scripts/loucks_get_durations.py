"""Pull full UpdateVoyage (no truncation) and extract duration/highlights for the 7 booked tour codes."""
import asyncio, json, time
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path('/home/john/Thunderbird')
COOKIE_FILE = ROOT / 'creds' / 'regent_cookies_oa.json'
BOOKING_URL = 'https://www.rssc.com/agent/myaccount/bookedcruise.aspx?EUQc5OJShNzRnf6WDNdRorwtMN96BHdNAoCRU76%2bXT%2fsOWFoWGyj%2fal2KN%2bqYiHit2tgnul78coeYRaj31f8gA%3d%3d'
OUT = ROOT / 'validations' / 'rssc_scrape'
BOOKED = {'GCM-021','CTG-021','PNT-012','QUZ-006','ACA-009','CSL-017','SAN-005'}

def load_rssc_cookies(path):
    raw = json.loads(path.read_text()); out=[]
    for c in raw:
        if 'rssc.com' not in c.get('domain',''): continue
        nc={k:v for k,v in c.items() if k!='sameSite'}
        if c.get('sameSite') in ('Strict','Lax','None'): nc['sameSite']=c['sameSite']
        out.append(nc)
    return out

async def main():
    full_uv = []
    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(viewport={'width':1440,'height':900})
        await ctx.add_cookies(load_rssc_cookies(COOKIE_FILE))
        page = await ctx.new_page()
        async def grab(resp):
            if 'UpdateVoyage' in resp.url:
                try: full_uv.append(await resp.text())
                except Exception: pass
        page.on('response', lambda r: asyncio.create_task(grab(r)))
        await page.goto(BOOKING_URL, wait_until='domcontentloaded', timeout=45000)
        await page.wait_for_timeout(3000)
        for sel in ['text=SHORE','text=CUSTOMIZE']:
            try:
                for el in (await page.query_selector_all(sel))[:1]:
                    await el.click(); await page.wait_for_timeout(4000)
            except Exception: pass
        await page.wait_for_timeout(3000)
        await ctx.close(); await b.close()

    import re
    found = {}
    for body in full_uv:
        # regex each excursion object by tourCode
        for code in BOOKED:
            # find the object containing this tourCode
            idx = body.find(f'"tourCode":"{code.lower()}"')
            if idx == -1:
                idx = body.find(f'"tourCode":"{code}"')
            if idx == -1: continue
            # back up to find title, durations near this index
            window = body[max(0,idx-600):idx+200]
            title = re.search(r'"title":"([^"]+)"', window)
            dur = re.search(r'"durations":"([^"]*)"', window)
            price = re.search(r'"price":"([^"]*)"', window)
            found[code] = {
                'title': title.group(1) if title else '?',
                'duration': dur.group(1) if dur else '?',
                'price': price.group(1) if price else '?',
            }
    (OUT / '3122006_booked_durations.json').write_text(json.dumps(found, indent=2))
    print(f'Captured {len(full_uv)} UpdateVoyage responses, total chars: {sum(len(x) for x in full_uv)}')
    print(f'Matched {len(found)}/7 booked codes:\n')
    for code in ['GCM-021','CTG-021','PNT-012','QUZ-006','ACA-009','CSL-017','SAN-005']:
        f = found.get(code)
        if f: print(f"  {code}: {f['title']} | {f['duration']} | {f['price']}")
        else: print(f"  {code}: NOT FOUND in catalog (may be sold out/removed from listing)")

if __name__ == '__main__':
    asyncio.run(main())
