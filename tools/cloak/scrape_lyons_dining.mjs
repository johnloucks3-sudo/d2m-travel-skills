import { launch } from 'cloakbrowser';
import * as fs from 'fs';

async function run() {
  console.log("Launching CloakBrowser (stealth Firefox/Chrome)...");
  let browser;
  try {
    browser = await launch({ headless: true, humanize: true });
    const page = await browser.newPage();
    
    console.log("Navigating to guest login page...");
    await page.goto("https://www.rssc.com/myaccount/login.aspx", { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    
    console.log("Filling credentials...");
    await page.fill("#uxMal_uxRegister_uxLoginEmailAddressTextbox", "klyons3@bellsouth.net");
    await page.fill("#uxMal_uxRegister_uxLoginPasswordTextbox", "GaBelle");
    
    console.log("Clicking login button...");
    await page.click("#uxMal_uxRegister_uxLoginButton");
    
    console.log("Waiting for navigation after login...");
    await page.waitForLoadState("load", { timeout: 15000 }).catch(e => console.log("Load wait note:", e.message));
    await page.waitForTimeout(5000);
    console.log("Logged in. Current URL:", page.url());
    
    console.log("Navigating directly to booked cruise page...");
    await page.goto("https://www.rssc.com/myaccount/bookedcruise.aspx?OoeY%2fi%2fpcNvwEA8rCTFBNbqLXSz%2bwzqfrh%2bERa7ATjmYtCjNXvYkAy%2fgppcDHTRn5x%2fLye9NU2prEuosAB2vng%3d%3d", { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForLoadState("load", { timeout: 15000 }).catch(e => console.log("Load wait note:", e.message));
    await page.waitForTimeout(5000);
    
    console.log("Clicking Customize section...");
    try {
      await page.click("a:has-text('Customize'), a:has-text('CUSTOMIZE')", { timeout: 5000 });
      await page.waitForTimeout(1000);
    } catch (e) {
      console.log("Customize click note:", e.message);
    }
    
    console.log("Clicking Dining tab...");
    try {
      await page.click("a:has-text('Dining'), a:has-text('DINING')", { timeout: 5000 });
      await page.waitForTimeout(2000);
    } catch (e) {
      console.log("Dining click note:", e.message);
    }
    
    const daysToCheck = {
      "Aug 12 (Pacific Rim)": "1",
      "Aug 19 (Prime 7)": "8",
      "Aug 21 (Chartreuse)": "10",
      "Aug 25 (Prime 7)": "14",
      "Aug 28 (Chartreuse)": "17",
      "Aug 31 (Pacific Rim)": "20"
    };
    
    const results = {};
    for (const [dayName, idx] of Object.entries(daysToCheck)) {
      console.log(`Checking ${dayName} (index ${idx})...`);
      // Run ChangeDiningDay javascript on page
      await page.evaluate((index) => {
        if (typeof ChangeDiningDay === 'function') {
          ChangeDiningDay(index);
        } else {
          throw new Error('ChangeDiningDay function not defined on page');
        }
      }, idx);
      
      await page.waitForTimeout(2000); // Wait for AJAX to finish updating DOM
      
      const detailsText = await page.evaluate(() => {
        const el = document.getElementById('detailedInfo2');
        return el ? el.innerText : '';
      });
      
      let reservedTime = "Not found";
      const lines = detailsText.split('\n');
      for (const line of lines) {
        if (line.includes("(Reserved)")) {
          reservedTime = line.trim();
          break;
        }
      }
      
      console.log(`  Result: ${reservedTime}`);
      results[dayName] = reservedTime;
    }
    
    const outPath = "/home/john/Thunderbird/validations/rssc_scrape/lyons_dining_times.txt";
    let outText = "";
    for (const [day, time] of Object.entries(results)) {
      outText += `${day}: ${time}\n`;
    }
    fs.writeFileSync(outPath, outText);
    console.log("Saved all times to", outPath);
    
  } catch (err) {
    console.error("Error running scraper:", err);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

run();
