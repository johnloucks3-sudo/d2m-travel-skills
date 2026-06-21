"""
REGENT BOOKING CAPTURE — universal, reusable for ANY Regent booking.

Pulls, from one authenticated pass over a booking's portal page:
  • Booking ground truth (voyage, ship, dates, suite, totals, balance, FPD, credits, guest reg)
  • ALL booked shore excursions: title, tour code, port, activity date, duration, price,
    full highlights + full description (clean UTF-8)
  • Per-guest shipboard credit allocation

Akamai-tolerant (Firefox + live cookies). Works inside the 48h ASPXAUTH window —
run regent_firefox_cookie_capture.py first (or right after a manual login).

Usage:
  python3 scripts/regent_booking_capture.py --booking 3122006 \
      --url "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?ENCID..." \
      --cookies creds/regent_cookies_oa.json \
      --out validations/rssc_scrape

Booking→URL map for known bookings lives in scripts/regent_parallel_scrape.py (BOOKING_URLS).
"""
import asyncio, json, re, argparse, time
from pathlib import Path
from playwright.async_api import async_playwright

def clean(s):
    if not s: return ''
    s = re.sub(r'</li>','',s); s = re.sub(r'<li>','\n• ',s)
    s = re.sub(r'</?(ul|ol|p|br|div|span|strong|em|h\d)[^>]*>','\n',s,flags=re.I)
    s = re.sub(r'<[^>]+>','',s)
    for a,b in [('&nbsp;',' '),('&amp;','&'),('&#39;',"'"),('&rsquo;',"'"),('&ldquo;','"'),
                ('&rdquo;','"'),('&quot;','"'),('&ndash;','–'),('&#8217;',"'"),('&#8211;','–')]:
        s = s.replace(a,b)
    s = re.sub(r'[ \t]+',' ',s); s = re.sub(r'\n[ \t]+','\n',s); s = re.sub(r'\n{3,}','\n\n',s)
    return s.strip()

def load_rssc_cookies(path):
    raw = json.loads(Path(path).read_text()); out=[]
    for c in raw:
        if 'rssc.com' not in c.get('domain',''): continue
        nc={k:v for k,v in c.items() if k!='sameSite'}
        if c.get('sameSite') in ('Strict','Lax','None'): nc['sameSite']=c['sameSite']
        out.append(nc)
    return out

async def capture(booking, url, cookies_path, out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    uv_raw, guests_raw, purchases_text = [], [], ''
    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(viewport={'width':1440,'height':900})
        await ctx.add_cookies(load_rssc_cookies(cookies_path))
        page = await ctx.new_page()
        async def grab(resp):
            try:
                if 'UpdateVoyage' in resp.url: uv_raw.append(await resp.text())
                elif 'GetGuests' in resp.url: guests_raw.append(await resp.text())
            except Exception: pass
        page.on('response', lambda r: asyncio.create_task(grab(r)))

        await page.goto(url, wait_until='domcontentloaded', timeout=45000)
        await page.wait_for_timeout(3500)
        final_url, title = page.url, await page.title()
        if 'login' in final_url.lower() or 'access denied' in (title or '').lower():
            print(f'AUTH FAIL — bounced to {final_url[:80]}. Re-login + refresh cookies.');
            await ctx.close(); await b.close(); return None
        booking_text = await page.evaluate('() => document.body.innerText')
        for sel in ['text=VIEW PURCHASES']:
            try:
                for el in (await page.query_selector_all(sel))[:1]:
                    await el.click(); await page.wait_for_timeout(2500)
                    purchases_text = await page.evaluate('() => document.body.innerText')
            except Exception: pass
        for attempt in range(4):
            if uv_raw: break
            for sel in ['text=SHORE','text=CUSTOMIZE','text=Book your excursions']:
                try:
                    els = await page.query_selector_all(sel)
                    if els:
                        await els[0].click(); await page.wait_for_timeout(5000)
                        if uv_raw: break
                except Exception: pass
        await page.wait_for_timeout(1500)
        await ctx.close(); await b.close()

    booked_codes = {}
    for m in re.finditer(r'([A-Z]{2,4}-\d{3})\t(\d{1,2}-[A-Za-z]{3})', purchases_text):
        booked_codes[m.group(1).upper()] = m.group(2)

    excursions = {}
    uv = max(uv_raw, key=len) if uv_raw else ''
    if uv:
        (out/f'{booking}_UpdateVoyage_raw.json').write_text(uv)
        try:
            data = json.loads(uv)
            for port in data.get('ports', []):
                for e in port.get('excursions', []):
                    code = (e.get('tourCode') or '').upper()
                    if code in booked_codes:
                        excursions[code] = {
                            'title': e.get('title'), 'port': port.get('name'),
                            'activity_date': booked_codes[code],
                            'duration': e.get('durations'), 'price': e.get('price'),
                            'highlights': clean(e.get('highlights','')),
                            'description': clean(e.get('description','')),
                        }
        except Exception as ex:
            print('UV parse error:', ex)

    credits = {}
    if guests_raw:
        try:
            g = json.loads(guests_raw[-1])
            for gu in g.get('guests', []):
                credits[f"{gu.get('firstName')} {gu.get('lastName')}"] = {
                    'age': gu.get('age'),
                    'shipboard_credit_total': gu.get('credits',{}).get('ShipBoardCredit',{}).get('totalAmount'),
                    'shipboard_credit_available': gu.get('credits',{}).get('ShipBoardCredit',{}).get('availableAmount'),
                }
        except Exception: pass

    result = {
        'booking': booking, 'captured': 'UTC-stamp-after-return',
        'booking_text': booking_text, 'booked_codes': booked_codes,
        'excursions': excursions, 'credits': credits,
        'excursion_count': len(excursions),
    }
    (out/f'{booking}_capture.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f'[{booking}] {len(excursions)} excursions, {len(credits)} guests, codes={list(booked_codes.keys())}')
    print(f'Saved {out}/{booking}_capture.json')
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--booking', required=True)
    ap.add_argument('--url', required=True)
    ap.add_argument('--cookies', default='/home/john/Thunderbird/creds/regent_cookies_oa.json')
    ap.add_argument('--out', default='/home/john/Thunderbird/validations/rssc_scrape')
    a = ap.parse_args()
    asyncio.run(capture(a.booking, a.url, a.cookies, a.out))

if __name__ == '__main__':
    main()
