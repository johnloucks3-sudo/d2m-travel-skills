import { launch } from 'cloakbrowser';
import { writeFileSync } from 'fs';

const OUT = '/home/john/Thunderbird/scratch';
const EMAIL = process.env.EN_EMAIL;
const PW = process.env.EN_PW;

if (!EMAIL || !PW) {
  console.error('Set EN_EMAIL and EN_PW env vars before running.');
  process.exit(1);
}

async function run() {
  let browser;
  try {
    browser = await launch({ headless: true, humanize: true });
    const page = await browser.newPage();

    console.log('Navigating to Evernote login...');
    await page.goto('https://accounts.evernote.com/login', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(2000);

    console.log('Clicking Continue with Google...');
    const [popup] = await Promise.all([
      page.waitForEvent('popup', { timeout: 15000 }).catch(() => null),
      page.frameLocator('iframe[title="Sign in with Google Button"]').getByRole('button', { name: /Continue with Google/i }).click(),
    ]);

    const googlePage = popup || page;
    await googlePage.waitForTimeout(3000);
    console.log('Google page URL:', googlePage.url());

    if (googlePage.url().includes('rejected')) {
      console.log('BLOCKED at Google bot-detection screen (same as before).');
      await googlePage.screenshot({ path: `${OUT}/cloak_google_rejected.png` });
      return;
    }

    console.log('Filling Google email...');
    await googlePage.waitForSelector('#identifierId, input[type="email"]', { timeout: 15000 });
    await googlePage.fill('#identifierId, input[type="email"]', EMAIL);
    await googlePage.click('#identifierNext');
    await googlePage.waitForTimeout(3000);
    console.log('URL after email submit:', googlePage.url());

    if (googlePage.url().includes('rejected')) {
      console.log('BLOCKED at Google bot-detection screen after email.');
      await googlePage.screenshot({ path: `${OUT}/cloak_google_rejected2.png` });
      return;
    }

    console.log('Filling Google password...');
    await googlePage.fill('input[type="password"]', PW);
    await googlePage.keyboard.press('Enter');
    await googlePage.waitForTimeout(5000);

    console.log('Final URL:', googlePage.url());
    await googlePage.screenshot({ path: `${OUT}/cloak_google_final.png`, fullPage: true });
    const text = await googlePage.evaluate(() => document.body ? document.body.innerText : '');
    writeFileSync(`${OUT}/cloak_google_final.txt`, text.substring(0, 2000));
    console.log('Page text (first 500 chars):', text.substring(0, 500));

  } catch (err) {
    console.error('Error:', err.message);
  } finally {
    if (browser) await browser.close();
  }
}

run();
