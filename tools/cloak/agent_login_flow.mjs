import { launch } from 'cloakbrowser';
import { writeFileSync } from 'fs';

const OUT = '/home/john/Thunderbird/validations/rssc_scrape';
const EMAIL = 'jl3lovegrouptravel@gmail.com';
const PW = 'Falcons4me!';

async function run() {
  console.log("Launching CloakBrowser to execute Agent Login...");
  let browser;
  try {
    browser = await launch({ headless: true, humanize: true });
    const page = await browser.newPage();
    
    console.log("Navigating to https://www.rssc.com/agent/default.aspx...");
    await page.goto("https://www.rssc.com/agent/default.aspx", { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000);
    
    // Accept cookies
    try {
      await page.click('#onetrust-accept-btn-handler', { timeout: 3000 });
      console.log("Accepted cookies.");
    } catch(_) {}
    
    console.log("Filling login fields...");
    await page.fill('#uxAgentHomePage_uxAgentRegister_uxLoginEmailAddressTextbox', EMAIL);
    await page.fill('#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox', PW);
    
    // Check for the login button or trigger enter
    console.log("Pressing Enter on password field to submit...");
    await page.focus('#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox');
    await page.keyboard.press('Enter');
    
    console.log("Waiting 10 seconds for post-login redirect...");
    await page.waitForTimeout(10000);
    
    let currentUrl = page.url();
    console.log("URL after login attempt:", currentUrl);
    
    await page.screenshot({ path: `${OUT}/agent_post_login.png`, fullPage: true });
    writeFileSync(`${OUT}/agent_post_login.html`, await page.content());
    
    const text = await page.evaluate(() => document.body ? document.body.innerText : '');
    writeFileSync(`${OUT}/agent_post_login.txt`, text);
    
    console.log("First 300 chars of page text:");
    console.log(text.substring(0, 300));
    
  } catch (err) {
    console.error("Error during agent login:", err);
  } finally {
    if (browser) await browser.close();
  }
}

run();
