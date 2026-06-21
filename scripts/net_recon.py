"""Network recon — log EVERY request on the public voyage page + booking page, dump JSON bodies, find port-description endpoint."""
import asyncio, json, re
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path('/home/john/Thunderbird/validations/rssc_scrape')
COOKIE_FILE = Path('/home/john/Thunderbird/creds/regent_cookies_oa.json')
PUBLIC = 'https://www.rssc.com/cruises/GRA261229/itinerary/'
MARKERS = ['promontory','fishing village','Jesuit','Médano','Lover','El Arco','estuary','cloud forest','stingray','peninsula','colonial','UNESCO','Baja','Cayman']

def load_cookies(path):
    raw = json.loads(path.read_text()); out=[]
    for c in raw:
        if 'rssc.com' not in c.get('domain',''): continue
        nc={k:v for k,v in c.items() if k!='sameSite'}
        if c.get('sameSite') in ('Strict','Lax','None'): nc['sameSite']=c['sameSite']
        out.append(nc)
    return out

async def recon(url, use_cookies, tag):
    reqlog = []
    bodies = []
    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0')
        if use_cookies:
            await ctx.add_cookies(load_cookies(COOKIE_FILE))
        page = await ctx.new_page()
        async def on_resp(resp):
            u = resp.url
            ct = resp.headers.get('content-type','')
            reqlog.append(f'{resp.status} {ct[:30]} {u[:140]}')
            if ('json' in ct or 'javascript' in ct) and 'rssc.com' in u:
                try:
                    body = await resp.text()
                    if any(mk.lower() in body.lower() for mk in MARKERS):
                        bodies.append({'url':u,'ct':ct,'body':body[:80000],'matched':[mk for mk in MARKERS if mk.lower() in body.lower()]})
                except Exception: pass
        page.on('response', lambda r: asyncio.create_task(on_resp(r)))
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=40000)
            await page.wait_for_timeout(6000)
            for y in range(0, 6000, 500):
                await page.evaluate(f'() => window.scrollTo(0,{y})'); await page.wait_for_timeout(300)
            # try clicking itinerary/port expanders
            for sel in ['text=Details','text=Itinerary','text=ITINERARY','text=Read More','[class*=port]','[class*=day]']:
                try:
                    for el in (await page.query_selector_all(sel))[:10]:
                        try: await el.click(timeout=1000); await page.wait_for_timeout(400)
                        except Exception: pass
                except Exception: pass
            await page.wait_for_timeout(2000)
            # scan inline scripts for embedded state
            scripts = await page.evaluate('''() => Array.from(document.querySelectorAll('script'))
                .map(s => s.innerText).filter(t => t && t.length > 500).slice(0,40)''')
        except Exception as e:
            scripts = []
            reqlog.append(f'NAV ERROR: {e}')
        await ctx.close(); await b.close()

    # check inline scripts for port markers
    script_hits = []
    for sc in scripts:
        if any(mk.lower() in sc.lower() for mk in MARKERS):
            script_hits.append(sc[:80000])

    (OUT/f'net_recon_{tag}_reqlog.txt').write_text('\n'.join(reqlog))
    (OUT/f'net_recon_{tag}_bodies.json').write_text(json.dumps({'bodies':bodies,'script_hits':script_hits}, indent=2, ensure_ascii=False))
    print(f'\n######## {tag} ({url[:60]}) ########')
    print(f'Total requests: {len(reqlog)} | port-marker JSON bodies: {len(bodies)} | script hits: {len(script_hits)}')
    print('--- rssc.com API-ish endpoints ---')
    seen=set()
    for line in reqlog:
        if '/api/' in line or '.ashx' in line or 'graphql' in line.lower() or 'itiner' in line.lower() or 'port' in line.lower() or 'destination' in line.lower():
            key = line.split('?')[0]
            if key not in seen:
                seen.add(key); print('  ', line[:130])
    print(f'--- bodies with port markers ({len(bodies)}) ---')
    for bd in bodies[:6]:
        print(f'  MATCH {bd["matched"][:4]} @ {bd["url"][:110]}')
    if script_hits:
        print(f'--- {len(script_hits)} inline scripts contain port markers (embedded state) ---')

async def main():
    await recon(PUBLIC, False, 'public_itin')

asyncio.run(main())
