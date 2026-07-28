import { launch } from 'cloakbrowser';
import { writeFileSync } from 'fs';

const OUT = '/home/john/Thunderbird/validations/lyons_regent';
const EMAIL = 'Klyons3@bellsouth.net';
const PW = 'GaBelle';
const log = (m) => process.stderr.write(m + '\n');

let browser;
try {
  browser = await launch({ headless: true, humanize: true });
  const page = await browser.newPage();
  
  log('Navigating to rssc.com homepage...');
  await page.goto('https://www.rssc.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);
  
  try {
    await page.click('#onetrust-accept-btn-handler', { timeout: 5000 });
  } catch(_) {}
  await page.waitForTimeout(1000);

  log('Opening My Account login modal...');
  await page.click('a[href*="modal-mainHeader-my-account"]', { timeout: 8000 });
  await page.waitForTimeout(3000);
  
  log('Filling credentials...');
  await page.fill('#account-email', EMAIL);
  await page.fill('#account-password', PW);
  
  log('Submitting login form...');
  await page.evaluate(() => {
    const f = document.querySelector('#account-email')?.closest('form');
    if (f) {
      const b = f.querySelector('button[type=submit],input[type=submit]');
      if (b) b.click();
    }
  });
  
  await page.waitForTimeout(10000);

  log('Navigating to booked cruises...');
  await page.goto('https://www.rssc.com/myaccount/bookedcruises.aspx', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(8000);

  const detailUrl = await page.evaluate(() => {
    const links = [...document.querySelectorAll('a[href*="bookedcruise.aspx?"]')].map(a => a.href);
    return links[0] || null;
  });

  log('Navigating to booking details: ' + detailUrl);
  await page.goto(detailUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(8000);

  // Trigger the print calendar view by executing the download script or clicking print/download buttons.
  // Wait, does the calendar view have a "Print" button or link? Let's check the calendar view page we downloaded.
  // In calendar_view.html:
  // Line 1221: <a href="javascript: window.print();" class="printButton">Print</a>
  // Let's trigger print-to-pdf or click show itinerary, click print, or download it.
  log('Clicking Show My Itinerary...');
  await page.click('#showItinerary a.itinerary', { timeout: 8000 });
  await page.waitForTimeout(6000);

  log('Toggling to calendar view...');
  await page.evaluate(() => {
    if (typeof ChangeToCalView === 'function') ChangeToCalView();
  });
  await page.waitForTimeout(6000);

  log('Generating print PDF of calendar view...');
  // We can print the page directly to PDF using Playwright's page.pdf()!
  await page.pdf({
    path: OUT + '/itinerary_calendar_view.pdf',
    format: 'Letter',
    printBackground: true,
    margin: { top: '0.4in', bottom: '0.4in', left: '0.4in', right: '0.4in' }
  });
  
  log('Calendar PDF successfully downloaded!');
  process.exit(0);
} catch(e) {
  log('ERR: ' + e.message);
  process.exit(1);
} finally {
  if (browser) try { await browser.close(); } catch(_) {}
}
