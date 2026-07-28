import { launch } from 'cloakbrowser';
import * as fs from 'fs';

function loadCookies(path) {
  const raw = JSON.parse(fs.readFileSync(path, 'utf8'));
  const out = [];
  for (const c of raw) {
    if (!c.domain.includes("rssc.com")) continue;
    const nc = { ...c };
    delete nc.sameSite;
    if (c.sameSite === "Strict" || c.sameSite === "Lax" || c.sameSite === "None") {
      nc.sameSite = c.sameSite;
    }
    out.push(nc);
  }
  return out;
}

async function run() {
  console.log("Launching CloakBrowser with pre-saved cookies...");
  let browser;
  try {
    browser = await launch({ headless: true, humanize: true });
    const context = await browser.newContext();
    
    const cookies = loadCookies("/home/john/Thunderbird/creds/regent_cookies_oa.json");
    await context.addCookies(cookies);
    console.log(`Loaded ${cookies.length} cookies.`);
    
    const page = await context.newPage();
    console.log("Navigating directly to booked cruise page...");
    const resp = await page.goto("https://www.rssc.com/myaccount/bookedcruise.aspx?OoeY%2fi%2fpcNvwEA8rCTFBNbqLXSz%2bwzqfrh%2bERa7ATjmYtCjNXvYkAy%2fgppcDHTRn5x%2fLye9NU2prEuosAB2vng%3d%3d", { waitUntil: 'domcontentloaded', timeout: 60000 });
    
    await page.waitForTimeout(5000);
    const finalUrl = page.url();
    const title = await page.title();
    console.log("Final URL:", finalUrl);
    console.log("Page Title:", title);
    
    const text = await page.evaluate(() => document.body.innerText);
    const bounced = finalUrl.includes("login") || finalUrl.includes("default.aspx") || finalUrl.includes("404");
    console.log("Bounced to login/404?:", bounced);
    
    await page.screenshot({ path: "/home/john/Thunderbird/validations/rssc_scrape/cookie_test.png" });
    console.log("Saved screenshot to cookie_test.png");
    
  } catch (err) {
    console.error("Error:", err);
  } finally {
    if (browser) await browser.close();
  }
}

run();
