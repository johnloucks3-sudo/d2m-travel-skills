import { launch } from 'cloakbrowser';

async function run() {
  const urls = [
    "https://www.rssc.com/ships/seven_seas_grandeur",
    "https://www.rssc.com/ships/seven-seas-grandeur"
  ];
  let browser;
  try {
    browser = await launch({ headless: true, humanize: true });
    const page = await browser.newPage();
    
    for (const url of urls) {
      console.log(`Probing: ${url}...`);
      try {
        const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
        console.log(`Status: ${resp ? resp.status() : 'No response'} | Final URL: ${page.url()}`);
      } catch (err) {
        console.log(`Failed for ${url}: ${err.message}`);
      }
    }
  } catch (err) {
    console.error(err);
  } finally {
    if (browser) await browser.close();
  }
}

run();
