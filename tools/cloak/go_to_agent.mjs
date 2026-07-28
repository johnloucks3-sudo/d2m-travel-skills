import { launch } from 'cloakbrowser';
import { writeFileSync } from 'fs';

async function run() {
  console.log("Launching CloakBrowser to access travel agent portal...");
  let browser;
  try {
    browser = await launch({ headless: true, humanize: true });
    const page = await browser.newPage();
    
    console.log("Navigating to https://www.rssc.com/agent/...");
    const resp = await page.goto("https://www.rssc.com/agent/", { waitUntil: 'domcontentloaded', timeout: 60000 });
    console.log("Initial load complete. URL:", page.url());
    
    await page.waitForTimeout(5000);
    
    // Check if there is an Accept Cookies button
    try {
      await page.click('#onetrust-accept-btn-handler', { timeout: 5000 });
      console.log("Accepted cookies.");
      await page.waitForTimeout(1000);
    } catch(_) {}
    
    // Save screenshot and print HTML/text
    const text = await page.evaluate(() => document.body ? document.body.innerText : '');
    const title = await page.title();
    console.log("Page Title:", title);
    console.log("URL after redirect/load:", page.url());
    
    await page.screenshot({ path: "/home/john/Thunderbird/validations/rssc_scrape/agent_portal_initial.png", fullPage: true });
    console.log("Saved initial portal screenshot to agent_portal_initial.png");
    
    // Log the first 500 chars of body text
    console.log("Body text preview:");
    console.log(text.substring(0, 500));
    
  } catch (err) {
    console.error("Error accessing agent portal:", err);
  } finally {
    if (browser) await browser.close();
  }
}

run();
