import { launch } from 'cloakbrowser';

async function run() {
  console.log("Launching CloakBrowser in HEADFUL mode...");
  let browser;
  try {
    // Launch headfully!
    browser = await launch({ headless: false, humanize: true });
    const context = await browser.newContext();
    const page = await context.newPage();
    
    console.log("Navigating to Regent Seven Seas website...");
    await page.goto("https://www.rssc.com/", { waitUntil: 'domcontentloaded', timeout: 60000 });
    
    console.log("Waiting 20 seconds for visual confirmation...");
    await page.waitForTimeout(20000);
    
    console.log("Closing browser.");
  } catch (err) {
    console.error("Error launching headfully:", err);
  } finally {
    if (browser) await browser.close();
  }
}

run();
