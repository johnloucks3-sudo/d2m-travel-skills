import { launch } from 'cloakbrowser';
import { writeFileSync } from 'fs';
const OUT = '/home/john/Thunderbird/validations/lyons_silversea';
const log = (m) => process.stderr.write(m + '\n');
let browser;
try {
  browser = await launch({ headless: true, humanize: true });
  const page = await browser.newPage();
  const resp = await page.goto('https://www.silversea.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(4000);
  log('home: HTTP ' + (resp&&resp.status?resp.status():'?') + ' | title="' + (await page.title()) + '"');
  const links = await page.evaluate(() => [...document.querySelectorAll('a[href]')].map(a=>({t:(a.innerText||'').trim().slice(0,30),h:a.href})).filter(x=>/login|sign|account|my-|myvoyage|voyage|guest|mysilversea/i.test(x.h+x.t)));
  const uniq=[...new Map(links.map(l=>[l.h,l])).values()];
  writeFileSync(OUT+'/home_login_links.json', JSON.stringify(uniq,null,1));
  uniq.slice(0,15).forEach(l=>log('  '+l.t.padEnd(24)+' '+l.h.slice(0,70)));
  process.exit(0);
} catch(e){ log('ERR '+e.message); process.exit(1); }
finally { if(browser) try{await browser.close();}catch(_){} }
