import asyncio, json, re
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path('/home/john/Thunderbird/validations/rssc_scrape')
PORTS = ['George Town','Cartagena','Puntarenas','Puerto Quetzal','Acapulco','Cabo San Lucas','San Diego','Miami','Los Angeles','Panama Canal','Grand Cayman']

def clean(s):
    s = re.sub(r'<[^>]+>',' ',s or '')
    for a,b in [('&nbsp;',' '),('&amp;','&'),('&#39;',"'"),('&rsquo;',"'"),('&ldquo;','"'),('&rdquo;','"'),('&quot;','"'),('&ndash;','–'),('&#8217;',"'"),('&#8211;','–')]:
        s = s.replace(a,b)
    return re.sub(r'\s+',' ',s).strip()

async def main():
    caps = []
    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0')
        page = await ctx.new_page()
        async def grab(resp):
            try:
                ct = resp.headers.get('content-type','')
                if 'json' in ct:
                    body = await resp.text()
                    if any(p.lower() in body.lower() for p in ['cartagena','acapulco','cabo','quetzal','cayman']) and len(body)<300000:
                        caps.append({'url':resp.url,'body':body})
            except Exception: pass
        page.on('response', lambda r: asyncio.create_task(grab(r)))
        await page.goto('https://www.rssc.com/cruises/GRA261229/itinerary/', wait_until='domcontentloaded', timeout=40000)
        await page.wait_for_timeout(5000)
        for y in range(0, 8000, 600):
            await page.evaluate(f'() => window.scrollTo(0, {y})')
            await page.wait_for_timeout(400)
        await page.wait_for_timeout(2000)
        for sel in ['text=Details','text=MORE','text=Read More','[class*=expand]','[class*=accordion]']:
            try:
                for el in (await page.query_selector_all(sel))[:20]:
                    try: await el.click(timeout=1000); await page.wait_for_timeout(200)
                    except Exception: pass
            except Exception: pass
        await page.wait_for_timeout(1500)
        txt = await page.evaluate('() => document.body.innerText')
        html = await page.evaluate('() => document.body.innerHTML')
        await ctx.close(); await b.close()

    found = {}
    for c in caps:
        try: j = json.loads(c['body'])
        except Exception: continue
        def walk(o):
            if isinstance(o, dict):
                nm = o.get('name') or o.get('portName') or o.get('cityName') or o.get('title')
                ds = o.get('description') or o.get('portDescription') or o.get('longDescription') or o.get('overview')
                if isinstance(nm,str) and isinstance(ds,str) and len(clean(ds))>100:
                    for p in PORTS:
                        if p.lower() in nm.lower(): found.setdefault(p, clean(ds))
                for v in o.values(): walk(v)
            elif isinstance(o,list):
                for v in o: walk(v)
        walk(j)
    for p in PORTS:
        if p in found: continue
        m = re.search(re.escape(p)+r'[^\n]{0,40}\n+((?:This|The|Once|Known|A |Set |Located|Nestled|Home|Founded|One )[^\n]{120,1600})', txt, re.I)
        if m: found[p]=clean(m.group(1))

    (OUT/'3122006_ports_from_itin.json').write_text(json.dumps(found,indent=2,ensure_ascii=False))
    (OUT/'voyage_itin_text.txt').write_text(txt)
    print('API caps:', len(caps), '| text len:', len(txt))
    for c in caps[:6]: print('  ', c['url'][:100])
    print('Ports found:', len(found))
    for p,d in found.items(): print(f'\n=== {p} ===\n{d[:220]}')
    print('\nPort names in itinerary text:')
    for p in PORTS: print(f'  {p}:', 'YES' if p.lower() in txt.lower() else 'no')

asyncio.run(main())
