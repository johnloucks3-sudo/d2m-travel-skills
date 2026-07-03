import { launch } from 'cloakbrowser';
import { writeFileSync } from 'fs';
const OUT = '/home/john/Thunderbird/validations/lyons_silversea';
const EMAIL = process.env.SS_EMAIL, PW = process.env.SS_PW;
const log = (m) => process.stderr.write(m + '\n');
const tryUrl = async (page, url) => {
  try { const r = await page.goto(url, { waitUntil:'domcontentloaded', timeout:40000 }); await page.waitForTimeout(3500);
    return {url, status:r&&r.status?r.status():'?', title:await page.title(), finalUrl:page.url()};
  } catch(e){ return {url, err:e.message}; }
};
let browser;
try {
  browser = await launch({ headless: true, humanize: true });
  const page = await browser.newPage();
  const candidates = ['https://my.silversea.com/','https://www.silversea.com/my-silversea.html','https://myvoyage.silversea.com/','https://www.silversea.com/booked-guests.html'];
  const found = [];
  for (const u of candidates){ const r = await tryUrl(page,u); found.push(r); log(JSON.stringify(r)); }
  writeFileSync(OUT+'/portal_candidates.json', JSON.stringify(found,null,1));
  // On the best candidate (first non-404), dump login fields
  const best = found.find(f=>f.status && f.status!==404 && !f.err);
  if (best){
    await page.goto(best.url, {waitUntil:'domcontentloaded',timeout:40000}); await page.waitForTimeout(4000);
    try { await page.click('#onetrust-accept-btn-handler,[id*=accept]', {timeout:4000}); } catch(_){}
    const fields = await page.evaluate(()=>[...document.querySelectorAll('input')].map(i=>({type:i.type,id:i.id,name:i.name,ph:i.placeholder})));
    writeFileSync(OUT+'/portal_fields.json', JSON.stringify(fields,null,1));
    log('best='+best.url+' fields='+JSON.stringify(fields.filter(f=>/email|user|pass/i.test(f.type+f.id+f.name+f.ph))));
    await page.screenshot({path:OUT+'/02_portal.png'});
  }
  process.exit(0);
} catch(e){ log('ERR '+e.message); process.exit(1); }
finally { if(browser) try{await browser.close();}catch(_){} }
