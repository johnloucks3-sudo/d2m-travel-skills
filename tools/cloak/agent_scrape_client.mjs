import { launch } from 'cloakbrowser';
import { writeFileSync, existsSync } from 'fs';
import * as path from 'path';

function getArg(flag) {
  const idx = process.argv.indexOf(flag);
  return (idx !== -1 && process.argv[idx + 1]) ? process.argv[idx + 1] : null;
}

const name = getArg('--name');
const url = getArg('--url');

if (!name || !url) {
  console.error("Usage: node agent_scrape_client.mjs --name <Name> --url <URL>");
  process.exit(1);
}

const OUT = '/home/john/Thunderbird/validations/rssc_scrape';
const EMAIL = 'jl3lovegrouptravel@gmail.com';
const PW = 'Falcons4me!';

async function run() {
  console.log(`Starting scrape for ${name}...`);
  let browser;
  let page;
  try {
    browser = await launch({ headless: true, humanize: true });
    page = await browser.newPage();
    
    console.log(`[${name}] Logging in...`);
    await page.goto("https://www.rssc.com/agent/default.aspx", { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000);
    
    try { await page.click('#onetrust-accept-btn-handler', { timeout: 3000 }); } catch(_) {}
    
    await page.fill('#uxAgentHomePage_uxAgentRegister_uxLoginEmailAddressTextbox', EMAIL);
    await page.fill('#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox', PW);
    await page.focus('#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(10000);
    
    console.log(`[${name}] Loading main booking page...`);
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    } catch (e) {
      console.log(`[${name}] Warning: main page load timeout/error (continuing):`, e.message);
    }
    await page.waitForTimeout(8000);
    
    // Save main screen
    try {
      await page.screenshot({ path: `${OUT}/live_agent_booking_${name}_main.png`, timeout: 5000 });
    } catch (e) {
      console.warn(`[${name}] Failed to save main screenshot: ${e.message}`);
    }
    const mainHtml = await page.content();
    writeFileSync(`${OUT}/live_agent_booking_${name}_main.html`, mainHtml);
    const mainText = await page.evaluate(() => document.body ? document.body.innerText : '');
    writeFileSync(`${OUT}/live_agent_booking_${name}_main.txt`, mainText);
    
    // Find dining and excursion links
    const diningHref = await page.evaluate(() => {
      const a = [...document.querySelectorAll('a')].find(el => (el.innerText || '').toLowerCase().includes('dining'));
      return a ? a.getAttribute('href') : null;
    });
    
    console.log(`[${name}] Found dining link:`, diningHref);
    
    // Extract info from main page
    const parsedData = {
      name: name,
      booking_url: url,
      scraped_at: new Date().toISOString(),
      main_text: mainText.substring(0, 2000), // snippet
      excursions: [],
      dining: []
    };
    
    // Scrape Excursions (&shorex=open)
    const shorexUrl = url + "&shorex=open";
    console.log(`[${name}] Loading shore excursions page...`);
    try {
      await page.goto(shorexUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    } catch (e) {
      console.log(`[${name}] Warning: shorex page load timeout/error (continuing):`, e.message);
    }
    await page.waitForTimeout(8000);
    
    try {
      await page.screenshot({ path: `${OUT}/live_agent_booking_${name}_shorex.png`, timeout: 5000 });
    } catch (e) {
      console.warn(`[${name}] Failed to save shorex screenshot: ${e.message}`);
    }
    const shorexHtml = await page.content();
    writeFileSync(`${OUT}/live_agent_booking_${name}_shorex.html`, shorexHtml);
    const shorexText = await page.evaluate(() => document.body ? document.body.innerText : '');
    writeFileSync(`${OUT}/live_agent_booking_${name}_shorex.txt`, shorexText);
    
    // Scrape Dining
    if (diningHref) {
      const fullDiningUrl = diningHref.startsWith('http') ? diningHref : 'https://www.rssc.com' + diningHref;
      console.log(`[${name}] Loading dining page:`, fullDiningUrl);
      try {
        await page.goto(fullDiningUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
      } catch (e) {
        console.log(`[${name}] Warning: dining page load timeout/error (continuing):`, e.message);
      }
      await page.waitForTimeout(8000);
      
      try {
        await page.screenshot({ path: `${OUT}/live_agent_booking_${name}_dining.png`, timeout: 5000 });
      } catch (e) {
        console.warn(`[${name}] Failed to save dining screenshot: ${e.message}`);
      }
      const diningHtml = await page.content();
      writeFileSync(`${OUT}/live_agent_booking_${name}_dining.html`, diningHtml);
      const diningText = await page.evaluate(() => document.body ? document.body.innerText : '');
      writeFileSync(`${OUT}/live_agent_booking_${name}_dining.txt`, diningText);
    } else {
      console.log(`[${name}] No dining link found (or dining not open yet).`);
    }
    
    console.log(`[${name}] Scrape successfully completed!`);
    writeFileSync(`${OUT}/live_agent_${name}_scraped_status.json`, JSON.stringify({ status: "success", timestamp: new Date().toISOString() }, null, 2));
    
  } catch (err) {
    console.error(`[${name}] Scrape failed:`, err);
    try {
      if (page) {
        await page.screenshot({ path: `${OUT}/live_agent_error_${name}.png` });
        writeFileSync(`${OUT}/live_agent_error_${name}.html`, await page.content());
      }
    } catch (e) {
      console.error("Failed to save error state:", e);
    }
    writeFileSync(`${OUT}/live_agent_${name}_scraped_status.json`, JSON.stringify({ status: "failed", error: err.message, timestamp: new Date().toISOString() }, null, 2));
    process.exit(1);
  } finally {
    if (browser) await browser.close();
  }
}

run();
