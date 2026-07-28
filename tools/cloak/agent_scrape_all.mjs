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

async function run() {
  console.log("Launching CloakBrowser to scrape all agent bookings...");
  let browser;
  try {
    browser = await launch({ headless: true, humanize: true });
    const page = await browser.newPage();
    
    console.log("Logging into the agent portal...");
    await page.goto("https://www.rssc.com/agent/default.aspx", { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000);
    
    // Accept cookies
    try {
      await page.click('#onetrust-accept-btn-handler', { timeout: 3000 });
    } catch(_) {}
    
    await page.fill('#uxAgentHomePage_uxAgentRegister_uxLoginEmailAddressTextbox', EMAIL);
    await page.fill('#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox', PW);
    await page.focus('#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox');
    await page.keyboard.press('Enter');
    
    await page.waitForTimeout(10000);
    console.log("Login finished. Current URL:", page.url());
    
    // Now loop and scrape each booking
    for (const [name, url] of Object.entries(bookings)) {
      console.log(`\nScraping booking for ${name}...`);
      try {
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
        await page.waitForTimeout(8000);
        
        console.log(`Loaded ${name} page. URL:`, page.url());
        
        // Take full-page screenshot
        await page.screenshot({ path: `${OUT}/live_agent_booking_${name}.png`, fullPage: true });
        
        // Save HTML content
        const html = await page.content();
        writeFileSync(`${OUT}/live_agent_booking_${name}.html`, html);
        
        // Save Text content
        const text = await page.evaluate(() => document.body ? document.body.innerText : '');
        writeFileSync(`${OUT}/live_agent_booking_${name}.txt`, text);
        
        console.log(`Saved ${name} details: size=${text.length} chars`);
        
        // Check for shore excursion or dining tabs/links
        const links = await page.evaluate(() => {
          return [...document.querySelectorAll('a[href]')].map(a => ({
            text: (a.innerText || '').trim(),
            href: a.getAttribute('href')
          })).filter(l => 
            l.href.includes("dining") || 
            l.href.includes("excursion") || 
            l.href.includes("itinerary") ||
            l.href.includes("shorex") ||
            l.href.includes("calendar")
          );
        });
        console.log(`Found sub-links for ${name}:`, JSON.stringify(links, null, 2));
        
      } catch (err) {
        console.error(`Error scraping ${name}:`, err);
      }
    }
    
    console.log("\nScrape cycle complete!");
  } catch (err) {
    console.error("General error:", err);
  } finally {
    if (browser) await browser.close();
  }
}

run();
