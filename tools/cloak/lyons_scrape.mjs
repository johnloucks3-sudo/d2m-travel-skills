import { launch } from 'cloakbrowser';
import { writeFileSync } from 'fs';
const OUT = '/home/john/Thunderbird/validations/lyons_regent';
const EMAIL = process.env.RSSC_EMAIL, PW = process.env.RSSC_PW;
const log = (m) => process.stderr.write(m + '\n');
const dump = async (page, tag) => {
  await page.screenshot({ path: `${OUT}/${tag}.png`, fullPage: true }).catch(()=>{});
  writeFileSync(`${OUT}/${tag}.html`, await page.content());
  const txt = await page.evaluate(() => document.body.innerText);
  writeFileSync(`${OUT}/${tag}.txt`, txt);
  log(`  [${tag}] title="${await page.title()}" bytes=${txt.length}`);
  return txt;
};
let browser;
try {
  browser = await launch({ headless: true, humanize: true });
  const page = await browser.newPage();
  await page.goto('https://www.rssc.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(4000);
  try { await page.click('#onetrust-accept-btn-handler', { timeout: 5000 }); } catch(_) {}
  await page.waitForTimeout(1000);
  await page.click('a[href*="modal-mainHeader-my-account"]', { timeout: 8000 }).catch(()=>{});
  await page.waitForTimeout(2500);
  await page.waitForSelector('#account-email', { state: 'visible', timeout: 10000 });
  await page.fill('#account-email', EMAIL);
  await page.fill('#account-password', PW);
  await page.evaluate(() => document.querySelector('#account-email').closest('form').querySelector('button[type=submit],input[type=submit]').click());
  await page.waitForTimeout(9000);
  log('logged in, url=' + page.url());

  // List-all page (plural)
  await page.goto('https://www.rssc.com/myaccount/bookedcruises.aspx', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(6000);
  await dump(page, 'booked_list');
  // Collect all detail links (ENCID) + online-checkin links (contain reservation numbers)
  const detail = await page.evaluate(() => {
    const links = [...document.querySelectorAll('a[href*="bookedcruise.aspx?"]')].map(a=>a.getAttribute('href'));
    const checkins = [...document.querySelectorAll('a[href*="online-checkin/"]')].map(a=>a.getAttribute('href'));
    return { links: [...new Set(links)], checkins: [...new Set(checkins)] };
  });
  log('detail links found: ' + detail.links.length + ' | checkin links: ' + detail.checkins.length);
  writeFileSync(OUT+'/detail_links.json', JSON.stringify(detail,null,1));

  // Scrape each booking detail
  let i = 0;
  for (const href of detail.links) {
    if (href.includes('shorex=open')) continue; // skip the shore-ex variant duplicate
    i++;
    const url = href.startsWith('http') ? href : 'https://www.rssc.com' + href;
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(6000);
      await dump(page, 'booking_' + i);
    } catch(e){ log(`  booking_${i} ERR ${e.message}`); }
  }
  const cookies = await page.context().cookies();
  writeFileSync(OUT+'/cookies.json', JSON.stringify(cookies,null,1));
  log('DONE — ' + i + ' bookings captured');
  process.exit(0);
} catch(e){ log('ERR '+e.message); process.exit(1); }
finally { if(browser) try{await browser.close();}catch(_){} }
