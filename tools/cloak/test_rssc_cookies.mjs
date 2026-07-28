import { launch } from 'cloakbrowser';
import * as fs from 'fs';

function loadCookies(path) {
  if (!fs.existsSync(path)) return [];
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

async function checkCookies(cookiePath, label) {
  console.log(`\nTesting cookies from: ${cookiePath} (${label})`);
  let browser;
  try {
    browser = await launch({ headless: true, humanize: true });
    const context = await browser.newContext();
    const cookies = loadCookies(cookiePath);
    if (cookies.length === 0) {
      console.log("No cookies found in file.");
      return;
    }
    await context.addCookies(cookies);
    console.log(`Loaded ${cookies.length} cookies.`);
    
    const page = await context.newPage();
    console.log("Navigating to booked cruises dashboard...");
    await page.goto("https://www.rssc.com/myaccount/bookedcruises.aspx", { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(5000);
    
    const finalUrl = page.url();
    const title = await page.title();
    console.log("Final URL:", finalUrl);
    console.log("Page Title:", title);
    
    const text = await page.evaluate(() => document.body ? document.body.innerText : '');
    const loggedIn = finalUrl.includes("bookedcruises.aspx") && !text.includes("Login") && !text.includes("SIGN IN");
    console.log("Successfully logged in?:", loggedIn);
    
    if (loggedIn) {
      console.log("First 300 chars of dashboard text:");
      console.log(text.substring(0, 300));
    }
  } catch (err) {
    console.error("Error during check:", err);
  } finally {
    if (browser) await browser.close();
  }
}

async function run() {
  await checkCookies("/home/john/Thunderbird/creds/regent_cookies_oa.json", "regent_cookies_oa.json");
  await checkCookies("/home/john/Thunderbird/creds/regent_cookies.json", "regent_cookies.json");
}

run();
