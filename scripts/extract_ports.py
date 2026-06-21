"""Fetch /api/browse/v1/cruises/GRA261229/summary (+ /ports fallback), extract port descriptions."""
import asyncio, json, re
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path('/home/john/Thunderbird/validations/rssc_scrape')
PORTS = ['George Town','Grand Cayman','Cartagena','Puntarenas','Puerto Quetzal','Acapulco','Cabo San Lucas','San Diego','Miami','Los Angeles','Panama Canal','Antigua']

def clean(s):
    if not isinstance(s,str): return ''
    s = re.sub(r'<[^>]+>',' ',s)
    for a,b in [('&nbsp;',' '),('&amp;','&'),('&#39;',"'"),('&rsquo;',"'"),('&ldquo;','"'),('&rdquo;','"'),('&quot;','"'),('&ndash;','–'),('&#8217;',"'"),('&#8211;','–')]:
        s=s.replace(a,b)
    return re.sub(r'\s+',' ',s).strip()

async def main():
    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0')
        page = await ctx.new_page()
        await page.goto('https://www.rssc.com/cruises/GRA261229/summary', wait_until='domcontentloaded', timeout=40000)
        await page.wait_for_timeout(2500)
        async def fetch(p):
            return await page.evaluate('''async (p) => {
                const r = await fetch(p, {headers:{'Accept':'application/json'}});
                return await r.text();
            }''', p)
        summary = await fetch('/api/browse/v1/cruises/GRA261229/summary')
        await ctx.close(); await b.close()

    (OUT/'voyage_summary_full.json').write_text(summary)
    data = json.loads(summary)

    # Walk JSON for objects that pair a port-ish name with a description
    results = {}
    def walk(o, path=''):
        if isinstance(o, dict):
            # collect name + description-like fields
            name = None
            for nk in ('portName','name','title','cityName','displayName','heading','label'):
                if isinstance(o.get(nk), str): name = o[nk]; break
            desc = None
            for dk in ('description','portDescription','longDescription','overview','body','copy','text','content'):
                if isinstance(o.get(dk), str) and len(o[dk]) > 100: desc = o[dk]; break
            if name and desc:
                for p in PORTS:
                    if p.lower() in name.lower() or name.lower() in p.lower():
                        c = clean(desc)
                        if len(c) > 100: results.setdefault(p, c)
            for k,v in o.items(): walk(v, path+'/'+k)
        elif isinstance(o, list):
            for i,v in enumerate(o): walk(v, f'{path}[{i}]')
    walk(data)

    # Also: find any long descriptive strings near port names anywhere in raw
    if len(results) < 5:
        flat = json.dumps(data, ensure_ascii=False)
        for p in PORTS:
            if p in results: continue
            # look for "...port...":"<long text mentioning the port or landmarks>"
            for m in re.finditer(r'"(?:description|overview|longDescription|body|copy)"\s*:\s*"((?:[^"\\]|\\.){150,2000})"', flat):
                txt = clean(m.group(1).encode().decode('unicode_escape', errors='ignore'))
                if p.lower() in txt.lower()[:200]:
                    results.setdefault(p, txt); break

    (OUT/'3122006_ports_FINAL.json').write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f'Summary JSON: {len(summary)} chars')
    print(f'Port descriptions extracted: {len(results)}')
    for p,d in results.items():
        print(f'\n=== {p} ===\n{d[:260]}')
    # if still thin, dump the top-level keys to understand structure
    if len(results) < 5:
        print('\n--- top-level keys ---', list(data.keys())[:30])
        # find where itinerary/ports live
        flat = json.dumps(data)
        for key in ['itinerary','ports','days','portDescription','description']:
            print(f'  "{key}" occurrences:', flat.count(f'"{key}"'))

asyncio.run(main())
