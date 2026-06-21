import asyncio, json, re
from pathlib import Path
from playwright.async_api import async_playwright

COOKIE_FILE = Path('/home/john/Thunderbird/creds/regent_cookies_oa.json')
CANDS = [
    'https://www.rssc.com/myaccount',
    'https://www.rssc.com/my-account',
    'https://www.rssc.com/account',
    'https://www.rssc.com/myaccount/mybookings',
    'https://www.rssc.com/account/bookings',
    'https://www.rssc.com/myaccount/bookedcruise',
    'https://www.rssc.com/booked',
    'https://www.rssc.com/my-account/my-cruises',
    'https://www.rssc.com/account/my-cruises',
    'https://www.rssc.com/myaccount/dashboard',
]
def load(path):
    raw=json.loads(path.read_text()); out=[]
    for c in raw:
        if 'rssc.com' not in c.get('domain',''): continue
        nc={k:v for k,v in c.items() if k!='sameSite'}
        if c.get('sameSite') in ('Strict','Lax','None'): nc['sameSite']=c['sameSite']
        out.append(nc)
    return out
async def main():
    async with async_playwright() as pw:
        b=await pw.firefox.launch(headless=True)
        ctx=await b.new_context(viewport={'width':1440,'height':900})
        await ctx.add_cookies(load(COOKIE_FILE))
        page=await ctx.new_page()
        for url in CANDS:
            try:
                r=await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)
                final=page.url; title=await page.title()
                text=await page.evaluate('() => document.body.innerText')
                links=await page.evaluate("() => Array.from(document.querySelectorAll('a')).map(a=>a.href).filter(h=>h&&(h.includes('bookedcruise')||h.includes('booking')||h.includes('cruise')&&h.includes('account')))")
                resnos=sorted(set(re.findall(r'\b(2\d{6}|3\d{6})\b', text)))
                is404='404' in title
                bounce='login' in final.lower() or 'default.aspx' in final.lower() or 'signin' in final.lower()
                names = [n for n in ['LOUCKS','LYONS','Nancy','Splendor','Grandeur','SPLENDOR','GRANDEUR'] if n.lower() in text.lower()]
                print(f'{r.status if r else "?"} {"404" if is404 else ("BOUNCE" if bounce else "OK")} | res#{resnos[:8]} names={names} | {url}')
                if (resnos or links) and not bounce and not is404:
                    print('   booking links:', links[:8])
                    Path('/tmp/guest_bookings.json').write_text(json.dumps({'url':url,'links':links,'resnos':resnos,'names':names},indent=2))
            except Exception as e:
                print(f'ERR {url}: {str(e)[:60]}')
        await ctx.close(); await b.close()
asyncio.run(main())
