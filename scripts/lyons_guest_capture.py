import asyncio, json, re, sys
from pathlib import Path
from playwright.async_api import async_playwright

COOKIE_FILE = Path("/home/john/Thunderbird/creds/regent_cookies_oa.json")
OUT = Path("/home/john/Thunderbird/validations/rssc_scrape")
OUT.mkdir(parents=True, exist_ok=True)
TARGET_RES = {"2979301", "3116314"}  # in scope: August Splendor + December Grandeur

# distinct detail base URLs (shorex variants stripped) from the bookings list
BASE = "https://www.rssc.com/myaccount/bookedcruise.aspx?"
URLS = [
    BASE + "OoeY%2fi%2fpcNvwEA8rCTFBNbqLXSz%2bwzqfrh%2bERa7ATjmYtCjNXvYkAy%2fgppcDHTRn5x%2fLye9NU2oeYRaj31f8gA%3d%3d",
    BASE + "OoeY%2fi%2fpcNvwEA8rCTFBNbqLXSz%2bwzqfrh%2bERa7ATjmYtCjNXvYkAy%2fgppcDHTRn5x%2fLye9NU2prEuosAB2vng%3d%3d",
    BASE + "YSO4LJQKvMMCoQE9FTBocXipb8JmJj1KymR%2fuujgSMM3%2frSH%2bEeczHWt0A9Tow6FbhPkjAgp8cI%3d",
    BASE + "tI%2b5yE4Bq9ZGTGX1xKxc%2bLqLXSz%2bwzqfv4nh1I1r6F43%2frSH%2bEeczHWt0A9Tow6FbhPkjAgp8cI%3d",
    BASE + "tI%2b5yE4Bq9aAK8Ws0rWez7qLXSz%2bwzqfBk8N5RnSi043%2frSH%2bEeczHWt0A9Tow6FbhPkjAgp8cI%3d",
]

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

def load(path):
    raw=json.loads(path.read_text()); out=[]
    for c in raw:
        if "rssc.com" not in c.get("domain",""): continue
        nc={k:v for k,v in c.items() if k!="sameSite"}
        if c.get("sameSite") in ("Strict","Lax","None"): nc["sameSite"]=c["sameSite"]
        out.append(nc)
    return out

async def capture_one(ctx, url):
    page = await ctx.new_page()
    uv_raw, guests_raw, xhr_log = [], [], []
    async def grab(resp):
        try:
            u = resp.url
            if any(x in u for x in ['.ashx','.asmx','/api/','json','Voyage','Guest','Excursion','Shorex','Credit']):
                xhr_log.append(u)
            if 'UpdateVoyage' in u: uv_raw.append(await resp.text())
            elif 'GetGuests' in u: guests_raw.append(await resp.text())
        except Exception: pass
    page.on('response', lambda r: asyncio.create_task(grab(r)))

    await page.goto(url, wait_until='domcontentloaded', timeout=45000)
    await page.wait_for_timeout(4000)
    final, title = page.url, await page.title()
    text = await page.evaluate('() => document.body.innerText')
    resnos = sorted(set(re.findall(r'\b(2\d{6}|3\d{6})\b', text)))
    res = resnos[0] if resnos else 'UNKNOWN'
    bounced = 'default.aspx' in final.lower() or 'login' in final.lower()
    print(f"  URL -> res#{res} bounced={bounced} title={title[:40]}")

    if res not in TARGET_RES or bounced:
        await page.close()
        return res, None  # identified only, not in scope

    # IN SCOPE: full capture in same pass
    booking_text = text
    purchases_text = ''
    for sel in ['text=VIEW PURCHASES']:
        try:
            els = await page.query_selector_all(sel)
            if els:
                await els[0].click(); await page.wait_for_timeout(2500)
                purchases_text = await page.evaluate('() => document.body.innerText')
        except Exception: pass
    # trigger shore excursion load
    for attempt in range(4):
        if uv_raw: break
        for sel in ['text=SHORE','text=CUSTOMIZE','text=Book your excursions','text=VIEW EXCURSIONS','text=SHORE EXCURSIONS']:
            try:
                els = await page.query_selector_all(sel)
                if els:
                    await els[0].click(); await page.wait_for_timeout(5000)
                    if uv_raw: break
            except Exception: pass
    await page.wait_for_timeout(1500)
    await page.close()

    # parse booked codes from purchases tab
    booked_codes = {}
    for m in re.finditer(r'([A-Z]{2,4}-\d{3})\t(\d{1,2}-[A-Za-z]{3})', purchases_text):
        booked_codes[m.group(1).upper()] = m.group(2)

    excursions = {}
    uv = max(uv_raw, key=len) if uv_raw else ''
    if uv:
        (OUT/f'{res}_UpdateVoyage_raw.json').write_text(uv)
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
            print('   UV parse error:', ex)

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
        'booking': res, 'url': url, 'final_url': final, 'title': title,
        'booking_text': booking_text, 'purchases_text': purchases_text,
        'booked_codes': booked_codes, 'excursions': excursions,
        'excursion_count': len(excursions), 'credits': credits,
        'xhr_handlers_seen': sorted(set(xhr_log)),
        'uv_raw_len': len(uv),
    }
    (OUT/f'{res}_capture.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"  [{res}] excursions={len(excursions)} codes={list(booked_codes.keys())[:8]} uv_len={len(uv)} guests={len(credits)}")
    print(f"  [{res}] XHR handlers: {sorted(set(xhr_log))[:12]}")
    return res, result

async def main():
    seen = {}
    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(viewport={'width':1440,'height':900})
        await ctx.add_cookies(load(COOKIE_FILE))
        for url in URLS:
            try:
                res, _ = await capture_one(ctx, url)
                if res in seen:
                    continue
                seen[res] = url
                await asyncio.sleep(6)  # be gentle with Akamai
            except Exception as e:
                print("  ERR", url[:70], str(e)[:80])
        await ctx.close(); await b.close()
    print("RES_MAP", json.dumps({k:v for k,v in seen.items()}, indent=2))

asyncio.run(main())
