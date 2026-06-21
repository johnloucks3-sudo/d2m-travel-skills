"""Find + capture port descriptions for 3122006 itinerary. Click each port day, grab lazy-loaded desc."""
import asyncio, json, re
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path('/home/john/Thunderbird')
COOKIE_FILE = ROOT / 'creds' / 'regent_cookies_oa.json'
BOOKING_URL = 'https://www.rssc.com/agent/myaccount/bookedcruise.aspx?EUQc5OJShNzRnf6WDNdRorwtMN96BHdNAoCRU76%2bXT%2fsOWFoWGyj%2fal2KN%2bqYiHit2tgnul78coeYRaj31f8gA%3d%3d'
OUT = ROOT / 'validations' / 'rssc_scrape'
PORTS = ['George Town','Cartagena','Puntarenas','Puerto Quetzal','Acapulco','Cabo San Lucas','San Diego','Miami','Los Angeles']
MARKERS = ['promontory','fishing village','peninsula','Jesuit','estuary','colonial','UNESCO','rainforest','cloud forest','harbor','archway','cliff','beach','Spanish','indigenous']

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
    s = re.sub(r'<[^>]+>',' ',s)
    s = (s.replace('&nbsp;',' ').replace('&amp;','&').replace('&#39;',"'").replace('&rsquo;',"'")
          .replace('&ldquo;','"').replace('&rdquo;','"').replace('&quot;','"').replace('&ndash;','–'))
    return re.sub(r'\s+',' ',s).strip()

async def main():
    resp_bodies = []
    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(viewport={'width':1440,'height':900})
        await ctx.add_cookies(load_rssc_cookies(COOKIE_FILE))
        page = await ctx.new_page()
        async def grab(resp):
            try:
                ct = resp.headers.get('content-type','')
                if 'json' in ct or 'html' in ct or 'text' in ct:
                    body = await resp.text()
                    if any(mk.lower() in body.lower() for mk in MARKERS):
                        resp_bodies.append({'url':resp.url,'body':body[:60000]})
            except Exception: pass
        page.on('response', lambda r: asyncio.create_task(grab(r)))

        await page.goto(BOOKING_URL, wait_until='domcontentloaded', timeout=45000)
        await page.wait_for_timeout(3000)
        # open itinerary
        await page.evaluate("() => { try { ShowItinView(); } catch(e){} }")
        await page.wait_for_timeout(2500)
        # click every VIEW (re-query each time to avoid detach)
        n = len(await page.query_selector_all('text=VIEW'))
        for i in range(min(n, 18)):
            try:
                els = await page.query_selector_all('text=VIEW')
                if i >= len(els): break
                await els[i].scroll_into_view_if_needed(timeout=3000)
                await els[i].click(timeout=4000)
                await page.wait_for_timeout(1800)
            except Exception:
                pass
        await page.wait_for_timeout(1500)
        page_text = await page.evaluate('() => document.body.innerText')
        await ctx.close(); await b.close()

    # Extract per-port descriptions from captured response bodies + page text
    found = {}
    haystacks = [rb['body'] for rb in resp_bodies] + [page_text]
    for port in PORTS:
        for hay in haystacks:
            # "<Port> Details <description...>" or port followed by a descriptive sentence
            m = re.search(re.escape(port)+r'\s*Details?\s*[:\-]?\s*(.{120,1600}?)(?:Details|VIEW|DAY \d|©|$)', clean(hay), re.I)
            if not m:
                m = re.search(re.escape(port)+r'[^.]{0,30}?\.\s+(This [^©]{120,1500}?\.)\s', clean(hay), re.I)
            if m:
                txt = clean(m.group(1))
                if len(txt) > 100 and txt.count(' ') > 18:
                    found[port] = txt
                    break

    (OUT/'3122006_port_descriptions.json').write_text(json.dumps(found, indent=2, ensure_ascii=False))
    print(f'Captured {len(resp_bodies)} marker-bearing responses.')
    for rb in resp_bodies[:8]:
        print('  RESP:', rb['url'][:95])
    print(f'\nPort descriptions extracted: {len(found)}/{len(PORTS)}')
    for p, d in found.items():
        print(f'\n=== {p} ===\n{d[:260]}')
    print('\nSaved 3122006_port_descriptions.json')

if __name__ == '__main__':
    asyncio.run(main())
