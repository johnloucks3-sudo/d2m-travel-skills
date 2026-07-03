import { launch } from 'cloakbrowser';
import { writeFileSync } from 'fs';
const OUT = '/home/john/Thunderbird/validations/lyons_regent';
const EMAIL = process.env.RSSC_EMAIL, PW = process.env.RSSC_PW;
const log = (m) => process.stderr.write(m + '\n');
let browser;
try {
  browser = await launch({ headless: true, humanize: true });
  const page = await browser.newPage();
  await page.goto('https://www.rssc.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(4000);
  try { await page.click('#onetrust-accept-btn-handler', { timeout: 5000 }); } catch(_) {}
  await page.waitForTimeout(1200);
  try { await page.click('a[href*="modal-mainHeader-my-account"]', { timeout: 8000 }); } catch(e){ log('MyAccount: '+e.message); }
  await page.waitForTimeout(2500);
  // Ensure the account email field is visible before typing
  await page.waitForSelector('#account-email', { state: 'visible', timeout: 10000 });
  await page.fill('#account-email', EMAIL);
  await page.fill('#account-password', PW);
  const check = await page.evaluate(() => ({e: document.querySelector('#account-email')?.value, p: (document.querySelector('#account-password')?.value||'').length}));
  log('field check: email=' + check.e + ' pwlen=' + check.p);
  // Click the submit button that lives in the SAME form as #account-email
  const clicked = await page.evaluate(() => {
    const f = document.querySelector('#account-email')?.closest('form');
    if (!f) return 'no-form';
    const b = f.querySelector('button[type=submit],input[type=submit]');
    if (!b) return 'no-btn';
    b.click(); return 'clicked:' + (b.innerText||b.value||'').trim().slice(0,20);
  });
  log('submit: ' + clicked);
  await page.waitForTimeout(9000);
  log('post-submit url: ' + page.url());
  await page.screenshot({ path: OUT + '/03_postlogin.png' });
  // Now try to reach the account/bookings area
  const acctErr = await page.evaluate(() => {
    const f = document.querySelector('#account-email')?.closest('form');
    const e = f?.querySelector('.error,.alert,[class*=error],[class*=invalid]');
    return e ? e.innerText.slice(0,120) : '';
  });
  log('account-form error: ' + (acctErr||'(none)'));
  const cookies = await page.context().cookies();
  writeFileSync(OUT+'/cookies.json', JSON.stringify(cookies,null,1));
  const aspx = cookies.find(c=>c.name==='ASPXAUTH');
  log('ASPXAUTH len: ' + (aspx ? aspx.value.length : 'none'));
  writeFileSync(OUT+'/03_postlogin.html', await page.content());
  const links = await page.evaluate(() => [...document.querySelectorAll('a[href]')].map(a=>({t:(a.innerText||'').trim().slice(0,45), h:a.href})).filter(x=>x.h.includes('rssc.com')));
  writeFileSync(OUT+'/postlogin_links.json', JSON.stringify([...new Map(links.map(l=>[l.h,l])).values()],null,1));
  process.exit(0);
} catch(e){ log('ERR '+e.message); process.exit(1); }
finally { if(browser) try{await browser.close();}catch(_){} }
