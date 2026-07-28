import { launch } from 'cloakbrowser';
import { writeFileSync } from 'fs';

const OUT = '/home/john/Thunderbird/validations/rssc_scrape';

async function run() {
  console.log("Launching CloakBrowser to scrape Seven Seas Grandeur ship info...");
  let browser;
  try {
    browser = await launch({ headless: true, humanize: true });
    const page = await browser.newPage();
    
    console.log("Navigating to Seven Seas Grandeur page...");
    await page.goto("https://www.rssc.com/ships/seven_seas_grandeur", { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(8000);
    
    console.log("Saving ship info...");
    const html = await page.content();
    writeFileSync(`${OUT}/live_grandeur_ship_info.html`, html);
    
    const text = await page.evaluate(() => document.body ? document.body.innerText : '');
    writeFileSync(`${OUT}/live_grandeur_ship_info.txt`, text);
    
    await page.screenshot({ path: `${OUT}/live_grandeur_ship_info.png` });
    console.log("Ship info saved successfully!");
  } catch (err) {
    console.error("Error scraping ship info:", err);
  } finally {
    if (browser) await browser.close();
  }
}

run();
