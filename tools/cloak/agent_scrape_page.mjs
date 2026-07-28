import { launch } from 'cloakbrowser';
import { writeFileSync } from 'fs';

const OUT = '/home/john/Thunderbird/validations/rssc_scrape';
const EMAIL = 'jl3lovegrouptravel@gmail.com';
const PW = 'Falcons4me!';

const elyUrl = "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?McWU05z77cmpnbQbEo2CdOumw8lV3LRNPvEArhnrrs3hl5RgmNGc6tgCF0LEwSWn9KttcnSG6QV03Ue0ckTSqA%3d%3d";

async function run() {
  console.log("Launching CloakBrowser...");
  let browser;
  try {
    browser = await launch({ headless: true, humanize: true });
    const page = await browser.newPage();
    
    console.log("Logging in...");
    await page.goto("https://www.rssc.com/agent/default.aspx", { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000);
    
    try { await page.click('#onetrust-accept-btn-handler', { timeout: 3000 }); } catch(_) {}
    
    await page.fill('#uxAgentHomePage_uxAgentRegister_uxLoginEmailAddressTextbox', EMAIL);
    await page.fill('#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox', PW);
    await page.focus('#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox');
    await page.keyboard.press('Enter');
    
    await page.waitForTimeout(10000);
    console.log("Logged in. Navigating to Ely's booking page...");
    
    await page.goto(elyUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(8000);
    console.log("Ely page loaded. URL:", page.url());
    
    // Save content FIRST before screenshot to avoid timeout block
    const html = await page.content();
    writeFileSync(`${OUT}/live_agent_booking_Ely.html`, html);
    
    const text = await page.evaluate(() => document.body ? document.body.innerText : '');
    writeFileSync(`${OUT}/live_agent_booking_Ely.txt`, text);
    console.log("Saved Ely html and text. Text length:", text.length);
    
    // Try taking a normal (non-fullPage) screenshot
    console.log("Taking normal screenshot...");
    await page.screenshot({ path: `${OUT}/live_agent_booking_Ely_normal.png` });
    console.log("Normal screenshot saved!");
    
    // Dump all links
    const links = await page.evaluate(() => {
      return [...document.querySelectorAll('a')].map(a => ({
        text: (a.innerText || '').trim(),
        href: a.getAttribute('href'),
        id: a.id,
        onclick: a.getAttribute('onclick')
      }));
    });
    
    console.log("All links found on Ely page:");
    for (const l of links) {
      if (l.href || l.onclick || l.text) {
        console.log(`- Text: "${l.text}" | Href: ${l.href} | ID: ${l.id} | Onclick: ${l.onclick}`);
      }
    }
    
  } catch (err) {
    console.error("Error during run:", err);
  } finally {
    if (browser) await browser.close();
  }
}

run();
