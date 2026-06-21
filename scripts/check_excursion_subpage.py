"""Navigate to booking page, click into a per-day excursion VIEW/detail, hunt for clock times."""
import asyncio, json, re, time
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path('/home/john/Thunderbird')
COOKIE_FILE = ROOT / 'creds' / 'regent_cookies_oa.json'
BOOKING_URL = 'https://www.rssc.com/agent/myaccount/bookedcruise.aspx?EUQc5OJShNzRnf6WDNdRorwtMN96BHdNAoCRU76%2bXT%2fsOWFoWGyj%2fal2KN%2bqYiHit2tgnul78coeYRaj31f8gA%3d%3d'
OUT = ROOT / 'validations' / 'rssc_scrape'
TIME_RE = re.compile(r'\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b|\bDepart\w*\b|\bMeet\w*\b|\bTour Time\b|\bStart Time\b|\bdeparture\b', re.I)

def load_rssc_cookies(path):
    raw = json.loads(path.read_text()); out=[]
    for c in raw:
        if 'rssc.com' not in c.get('domain',''): continue
        nc={k:v for k,v in c.items() if k!='sameSite'}
        if c.get('sameSite') in ('Strict','Lax','None'): nc['sameSite']=c['sameSite']
        out.append(nc)
    return out

async def main():
    api_bodies = []
    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(viewport={'width':1440,'height':900})
        await ctx.add_cookies(load_rssc_cookies(COOKIE_FILE))
        page = await ctx.new_page()
        async def grab(resp):
            u = resp.url
            if any(k in u for k in ['Excursion','excursion','shorex','Detail','GetTour','TourDetail','Booked']):
                try:
                    body = await resp.text()
                    if TIME_RE.search(body) or 'tourTime' in body or 'departureTime' in body or 'meetTime' in body:
                        api_bodies.append({'url':u,'body':body[:6000]})
                except Exception: pass
        page.on('response', lambda r: asyncio.create_task(grab(r)))

        await page.goto(BOOKING_URL, wait_until='domcontentloaded', timeout=45000)
        await page.wait_for_timeout(3500)

        # ensure itinerary view open
        for sel in ['text=SHOW MY ITINERARY']:
            try:
                for el in (await page.query_selector_all(sel))[:1]:
                    await el.click(); await page.wait_for_timeout(2000)
            except Exception: pass

        # Find all VIEW links/buttons in the itinerary and click the first few that lead to an excursion day
        clicked_results = []
        view_els = await page.query_selector_all('text=VIEW')
        print(f'Found {len(view_els)} VIEW elements')
        # Click VIEW for George Town (booked: Dolphin). Try first 4 VIEWs.
        for i, el in enumerate(view_els[:6]):
            try:
                await el.click()
                await page.wait_for_timeout(2500)
                txt = await page.evaluate('() => document.body.innerText')
                # Find time-ish lines
                hits = []
                for m in TIME_RE.finditer(txt):
                    s=max(0,m.start()-50); e=min(len(txt),m.start()+50)
                    hits.append(txt[s:e].replace(chr(10),' ').strip())
                clicked_results.append({'view_index':i,'time_hits':hits[:8],'url':page.url})
                # close any modal
                for closer in ['button[aria-label=Close]','text=CLOSE','.close','[class*=close]']:
                    try:
                        c = await page.query_selector(closer)
                        if c: await c.click(); await page.wait_for_timeout(500)
                    except Exception: pass
                await page.goto(BOOKING_URL, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)
                view_els = await page.query_selector_all('text=VIEW')
            except Exception as e:
                clicked_results.append({'view_index':i,'error':str(e)[:100]})

        result = {'api_bodies_with_times':api_bodies, 'view_click_results':clicked_results}
        (OUT/'3122006_subpage_times_probe.json').write_text(json.dumps(result,indent=2,default=str))

        print('\n=== API RESPONSES CONTAINING TIME PATTERNS ===')
        if not api_bodies: print('  (none — no excursion API returned clock-time fields)')
        for a in api_bodies[:5]:
            print(f'\n--- {a["url"][:100]}')
            for m in TIME_RE.finditer(a['body']):
                s=max(0,m.start()-40); e=min(len(a['body']),m.start()+40)
                print('   ', a['body'][s:e].replace(chr(10),' '))
        print('\n=== VIEW SUBPAGE CLICK RESULTS ===')
        for r in clicked_results:
            print(f'  VIEW[{r.get("view_index")}] {"ERROR:"+r["error"] if r.get("error") else ("time_hits="+str(r.get("time_hits")))}')
        await ctx.close(); await b.close()

if __name__ == '__main__':
    asyncio.run(main())
