import { launch } from 'cloakbrowser';
import { writeFileSync } from 'fs';

const OUT = '/home/john/Thunderbird/validations/rssc_scrape';
const EMAIL = 'jl3lovegrouptravel@gmail.com';
const PW = 'Falcons4me!';

const elyShorexUrl = "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?McWU05z77cmpnbQbEo2CdOumw8lV3LRNPvEArhnrrs3hl5RgmNGc6tgCF0LEwSWn9KttcnSG6QV03Ue0ckTSqA%3d%3d&shorex=open";
const elyDiningUrl = "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?McWU05z77cmpnbQbEo2CdOumw8lV3LRNPvEArhnrrs3hl5RgmNGc6tgCF0LEwSWn9KttcnSG6QUQgRzWRDSMkR5hFqPfV%2fyA";

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
    
    console.log("Logged in. Navigating to Ely Shorex...");
    await page.goto(elyShorexUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(8000);
    
    let html = await page.content();
    writeFileSync(`${OUT}/live_agent_ely_shorex.html`, html);
    let text = await page.evaluate(() => document.body ? document.body.innerText : '');
    writeFileSync(`${OUT}/live_agent_ely_shorex.txt`, text);
    await page.screenshot({ path: `${OUT}/live_agent_ely_shorex.png` });
    console.log("Saved Ely Shorex. Text length:", text.length);
    
    console.log("Navigating to Ely Dining...");
    await page.goto(elyDiningUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(8000);
    
    html = await page.content();
    writeFileSync(`${OUT}/live_agent_ely_dining.html`, html);
    text = await page.evaluate(() => document.body ? document.body.innerText : '');
    writeFileSync(`${OUT}/live_agent_ely_dining.txt`, text);
    await page.screenshot({ path: `${OUT}/live_agent_ely_dining.png` });
    console.log("Saved Ely Dining. Text length:", text.length);
    
  } catch (err) {
    console.error("Error during run:", err);
  } finally {
    if (browser) await browser.close();
  }
}

run();
