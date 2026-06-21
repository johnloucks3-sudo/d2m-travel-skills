"""Scrape public Regent voyage page GRA261229 for port descriptions."""
import asyncio, json, re
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path('/home/john/Thunderbird/validations/rssc_scrape')
URLS = [
    'https://www.rssc.com/cruises/GRA261229/summary/',
    'https://www.rssc.com/cruises/GRA261229/itinerary/',
    'https://www.rssc.com/cruises/GRA261229/',
]
PORTS = ['George Town','Cartagena','Puntarenas','Puerto Quetzal','Acapulco','Cabo San Lucas','San Diego','Miami','Los Angeles','Panama Canal']

def clean(s):
    s = re.sub(r'<[^>]+>',' ',s or '')
    s = (s.replace('&nbsp;',' ').replace('&amp;','&').replace('&#39;',"'").replace('&rsquo;',"'")
          .replace('&ldquo;','"').replace('&rdquo;','"').replace('&quot;','"').replace('&ndash;','–').replace('&#8217;',"'"))
    return re.sub(r'\s+',' ',s).strip()

async def main():
    found = {}
    api_caps = []
    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(viewport={'width':1440,'height':900},
                                  user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0')
        page = await ctx.new_page()
        async def grab(resp):
            try:
                if any(k in resp.url.lower() for k in ['itiner','port','destination','voyage','cruise','geo','api']):
                    ct = resp.headers.get('content-type','')
                    if 'json' in ct:
                        body = await resp.text()
                        if any(p.lower() in body.lower() for p in PORTS) and len(body) < 200000:
                            api_caps.append({'url':resp.url,'body':body})
            except Exception: pass
        page.on('response', lambda r: asyncio.create_task(grab(r)))

        page_texts = []
        for url in URLS:
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=40000)
                await page.wait_for_timeout(4000)
                try: await page.wait_for_load_state('networkidle', timeout=8000)
                except Exception: pass
                # expand any "Details"/"Read more" toggles
                for sel in ['text=Details','text=Read More','text=READ MORE','text=View Details']:
                    try:
                        for el in (await page.query_selector_all(sel))[:15]:
                            try: await el.click(timeout=1500); await page.wait_for_timeout(300)
                            except Exception: pass
                    except Exception: pass
                await page.wait_for_timeout(1500)
                page_texts.append(await page.evaluate('() => document.body.innerText'))
            except Exception as e:
                page_texts.append(f'ERR {url}: {e}')
        await ctx.close(); await b.close()

    # Parse port descriptions from API JSON first (most structured)
    for cap in api_caps:
        try:
            j = json.loads(cap['body'])
        except Exception:
            continue
        def walk(o):
            if isinstance(o, dict):
                name = o.get('name') or o.get('portName') or o.get('title') or o.get('cityName')
                desc = o.get('description') or o.get('portDescription') or o.get('longDescription') or o.get('overview') or o.get('body')
                if name and desc and isinstance(name,str) and isinstance(desc,str):
                    for p in PORTS:
                        if p.lower() in name.lower() and len(clean(desc)) > 100:
                            found.setdefault(p, clean(desc))
                for v in o.values(): walk(v)
            elif isinstance(o, list):
                for v in o: walk(v)
        walk(j)

    # Fallback: regex from page text
    alltext = '\n'.join(page_texts)
    for p in PORTS:
        if p in found: continue
        m = re.search(re.escape(p)+r'\s*(?:Details|Overview)?\s*[:\-]?\s*((?:This|The|Once|Known|A |Set |Located|Founded|Nestled|Home)[^\n]{120,1500})', alltext, re.I)
        if m:
            found[p] = clean(m.group(1))

    (OUT/'3122006_port_descriptions_public.json').write_text(json.dumps(found, indent=2, ensure_ascii=False))
    print(f'API JSON captures: {len(api_caps)}')
    for c in api_caps[:6]: print('  ', c['url'][:100])
    print(f'\nPort descriptions found: {len(found)}/{len(PORTS)}')
    for p, d in found.items():
        print(f'\n=== {p} ===\n{d[:240]}')
    print('\nSaved 3122006_port_descriptions_public.json')

if __name__ == '__main__':
    asyncio.run(main())
