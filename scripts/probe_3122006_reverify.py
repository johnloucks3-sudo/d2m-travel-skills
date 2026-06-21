import asyncio, json, re
from pathlib import Path
from playwright.async_api import async_playwright

COOKIE_FILE = Path('/home/john/Thunderbird/creds/regent_cookies_oa.json')
AGENT_URL = 'https://www.rssc.com/agent/myaccount/bookedcruise.aspx?EUQc5OJShNzRnf6WDNdRorwtMN96BHdNAoCRU76%2bXT%2fsOWFoWGyj%2fal2KN%2bqYiHit2tgnul78coeYRaj31f8gA%3d%3d'

def load(path):
    raw = json.loads(path.read_text()); out = []
    for c in raw:
        if 'rssc.com' not in c.get('domain', ''): continue
        nc = {k: v for k, v in c.items() if k != 'sameSite'}
        if c.get('sameSite') in ('Strict', 'Lax', 'None'): nc['sameSite'] = c['sameSite']
        out.append(nc)
    return out

async def main():
    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900})
        await ctx.add_cookies(load(COOKIE_FILE))
        page = await ctx.new_page()
        r = await page.goto(AGENT_URL, wait_until='domcontentloaded', timeout=45000)
        await page.wait_for_timeout(4000)
        final = page.url; title = await page.title()
        text = await page.evaluate('() => document.body.innerText')
        low = final.lower()
        bounce = ('login' in low or 'default.aspx' in low or 'signin' in low)
        money = re.compile(r':\s*\$([\d,]+\.\d{2})')
        def grab(label):
            m = re.search(re.escape(label) + r'\s*\$([\d,]+\.\d{2})', text)
            return m.group(1) if m else None
        fpd = re.search(r'Remaining Balance Due:\s*([\d/]+)', text)
        out = {
            'status': r.status if r else None, 'final_url': final, 'title': title,
            'bounce': bounce, 'has_3122006': '3122006' in text,
            'total': grab('Total Booking Amount:'),
            'paid': grab('Paid to Date:'),
            'balance_due': grab('Balance Due:'),
            'fpd': fpd.group(1) if fpd else None,
            'sbc_300_present': '$300' in text,
            'guest_reg_incomplete': 'COMPLETE GUEST REGISTRATION' in text.upper(),
            'text_len': len(text),
        }
        Path('/home/john/Thunderbird/validations/rssc_scrape/3122006_reverify_20260612.json').write_text(json.dumps(out, indent=2))
        print(json.dumps(out, indent=2))
        await ctx.close(); await b.close()

asyncio.run(main())
