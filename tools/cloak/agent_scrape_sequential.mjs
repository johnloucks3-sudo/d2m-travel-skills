import { launch } from 'cloakbrowser';
import { writeFileSync } from 'fs';

const OUT = '/home/john/Thunderbird/validations/rssc_scrape';
const EMAIL = 'jl3lovegrouptravel@gmail.com';
const PW = 'Falcons4me!';

const bookings = {
  "Ely": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?McWU05z77cmpnbQbEo2CdOumw8lV3LRNPvEArhnrrs3hl5RgmNGc6tgCF0LEwSWn9KttcnSG6QV03Ue0ckTSqA%3d%3d",
  "Nichols": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?P4lRDbrpl6KimySo%2fK4o%2bwDZRcXP9mymm6bgZqnsScH38MGZtQLDbVpf764ZzfTpNPFFP6eqcei3a2Ce6Xvxyh5hFqPfV%2fyA",
  "Furlow": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?eecDnW0xAFxbgFqHZBS8Eko5Uc3K5UTVHzz%2b5iUsOMeF38Ba0f%2bR5xYgM6Gv3nm1CyaweMg7GG8DwKCVXbjhAg%3d%3d",
  "McLeod": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?21uwzkkXT97f7JcY1xK9hyCQmJ8KAZNizQbA8RnZf9%2b2GB6xoVkHtRcCZey5%2bUtfz14I9iYKQKotURuEHXNX822RP7fimObr"
};

async function scrapeBooking(page, name, url) {
  console.log(`\n--- SCRAPING ${name.toUpperCase()} ---`);
  try {
    console.log(`[${name}] Navigating to main booking page...`);
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(6000);
    
    // Save main HTML and text
    const mainHtml = await page.content();
    writeFileSync(`${OUT}/live_agent_booking_${name}_main.html`, mainHtml);
    const mainText = await page.evaluate(() => document.body ? document.body.innerText : '');
    writeFileSync(`${OUT}/live_agent_booking_${name}_main.txt`, mainText);
    console.log(`[${name}] Saved main info. Length: ${mainText.length}`);
    try {
      await page.screenshot({ path: `${OUT}/live_agent_booking_${name}_main.png`, timeout: 5000 });
    } catch (e) {
      console.warn(`[${name}] Failed to save main screenshot: ${e.message}`);
    }
    
    // Find dining link
    const diningHref = await page.evaluate(() => {
      const a = [...document.querySelectorAll('a')].find(el => (el.innerText || '').toLowerCase().includes('dining'));
      return a ? a.getAttribute('href') : null;
    });
    
    // Go to Shore Excursions
    const shorexUrl = url + "&shorex=open";
    console.log(`[${name}] Navigating to shore excursions...`);
    await page.goto(shorexUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(6000);
    
    const shorexHtml = await page.content();
    writeFileSync(`${OUT}/live_agent_booking_${name}_shorex.html`, shorexHtml);
    const shorexText = await page.evaluate(() => document.body ? document.body.innerText : '');
    writeFileSync(`${OUT}/live_agent_booking_${name}_shorex.txt`, shorexText);
    console.log(`[${name}] Saved shore excursions. Length: ${shorexText.length}`);
    try {
      await page.screenshot({ path: `${OUT}/live_agent_booking_${name}_shorex.png`, timeout: 5000 });
    } catch (e) {
      console.warn(`[${name}] Failed to save shorex screenshot: ${e.message}`);
    }
    
    // Go to Dining if link exists
    if (diningHref) {
      const fullDiningUrl = diningHref.startsWith('http') ? diningHref : 'https://www.rssc.com' + diningHref;
      console.log(`[${name}] Navigating to dining: ${fullDiningUrl}`);
      await page.goto(fullDiningUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(6000);
      
      const diningHtml = await page.content();
      writeFileSync(`${OUT}/live_agent_booking_${name}_dining.html`, diningHtml);
      const diningText = await page.evaluate(() => document.body ? document.body.innerText : '');
      writeFileSync(`${OUT}/live_agent_booking_${name}_dining.txt`, diningText);
      console.log(`[${name}] Saved dining. Length: ${diningText.length}`);
      try {
        await page.screenshot({ path: `${OUT}/live_agent_booking_${name}_dining.png`, timeout: 5000 });
      } catch (e) {
        console.warn(`[${name}] Failed to save dining screenshot: ${e.message}`);
      }
    } else {
      console.log(`[${name}] No dining link found.`);
    }
    
    console.log(`[${name}] Completed successfully.`);
  } catch (err) {
    console.error(`[${name}] Error:`, err);
  }
}

async function run() {
  console.log("Launching CloakBrowser for sequential agent scraping...");
  let browser;
  try {
    browser = await launch({ headless: true, humanize: true });
    const page = await browser.newPage();
    
    console.log("Logging into the agent portal...");
    await page.goto("https://www.rssc.com/agent/default.aspx", { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000);
    
    try { await page.click('#onetrust-accept-btn-handler', { timeout: 3000 }); } catch(_) {}
    
    await page.fill('#uxAgentHomePage_uxAgentRegister_uxLoginEmailAddressTextbox', EMAIL);
    await page.fill('#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox', PW);
    await page.focus('#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(10000);
    
    console.log("Logged in. Starting sequential scraping...");
    
    for (const name of ["Ely", "Nichols", "Furlow", "McLeod"]) {
      await scrapeBooking(page, name, bookings[name]);
    }
    
    console.log("\nALL SCRAPING COMPLETED SEQUENTIALLY!");
  } catch (err) {
    console.error("General error:", err);
  } finally {
    if (browser) await browser.close();
  }
}

run();
