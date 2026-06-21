"""List all bookings visible in the current Regent session + their encrypted bookedcruise URLs."""
import asyncio, json, re
from pathlib import Path
from playwright.async_api import async_playwright

COOKIE_FILE = Path('/home/john/Thunderbird/creds/regent_cookies_oa.json')
# Common account landing pages
CANDIDATES = [
    'https://www.rssc.com/agent/myaccount/',
    'https://www.rssc.com/agent/myaccount/mybookings.aspx',
    'https://www.rssc.com/account/mybookings',
    'https://www.rssc.com/agent/',
]

def load(path):
    raw = json.loads(path.read_text()); out=[]
    for c in raw:
        if 'rssc.com' not in c.get('domain',''): continue
        nc={k:v for k,v in c.items() if k!='sameSite'}
        if c.get('sameSite') in ('Strict','Lax','None'): nc['sameSite']=c['sameSite']
        out.append(nc)
    return out

async def main():
    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(viewport={'width':1440,'height':900})
        await ctx.add_cookies(load(COOKIE_FILE))
        page = await ctx.new_page()
        for url in CANDIDATES:
            try:
                r = await page.goto(url, wait_until='domcontentloaded', timeout=35000)
                await page.wait_for_timeout(3500)
                final = page.url
                title = await page.title()
                # find all bookedcruise links + nearby reservation numbers
                links = await page.evaluate('''() => Array.from(document.querySelectorAll('a'))
                    .map(a => a.href).filter(h => h && h.includes('bookedcruise.aspx'))''')
                text = await page.evaluate('() => document.body.innerText')
                resnos = re.findall(r'\b(2\d{6}|3\d{6})\b', text)
                bounced = 'login' in final.lower()
                print(f'\n### {url}')
                print(f'  final: {final[:80]} | title: {title[:50]} | bounced={bounced}')
                print(f'  bookedcruise links: {len(links)} | reservation#s in text: {sorted(set(resnos))[:12]}')
                for l in links[:12]:
                    print('   ', l[:130])
                if links:
                    Path('/tmp/booking_links.json').write_text(json.dumps({'url':url,'links':links,'resnos':sorted(set(resnos))}, indent=2))
                    break
            except Exception as e:
                print(f'  {url} ERROR: {str(e)[:80]}')
        await ctx.close(); await b.close()

asyncio.run(main())
