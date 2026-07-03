import { launch } from 'cloakbrowser';
import { writeFileSync } from 'fs';
const OUT = '/home/john/Thunderbird/validations/lyons_silversea';
const EMAIL = process.env.SS_EMAIL, PW = process.env.SS_PW;
const log = (m) => process.stderr.write(m + '\n');
let browser;
try {
  browser = await launch({ headless: true, humanize: true });
  const page = await browser.newPage();
  const resp = await page.goto('https://www.silversea.com/login.html', { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(()=>null);
  await page.waitForTimeout(4000);
  log('login page: HTTP ' + (resp&&resp.status?resp.status():'?') + ' | title="' + (await page.title()) + '" | url=' + page.url());
  try { await page.click('#onetrust-accept-btn-handler,[id*=accept],[class*=accept]', { timeout: 4000 }); } catch(_) {}
  await page.waitForTimeout(1000);
  // dump candidate login fields
  const fields = await page.evaluate(() => [...document.querySelectorAll('input')].map(i=>({type:i.type,id:i.id,name:i.name,ph:i.placeholder})).filter(f=>/email|user|pass|login/i.test((f.id+f.name+f.ph+f.type))));
  writeFileSync(OUT+'/login_fields.json', JSON.stringify(fields,null,1));
  log('login fields: ' + JSON.stringify(fields));
  await page.screenshot({ path: OUT+'/01_login.png' });
  process.exit(0);
} catch(e){ log('ERR '+e.message); process.exit(1); }
finally { if(browser) try{await browser.close();}catch(_){} }
