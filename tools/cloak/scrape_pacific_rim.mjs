import { launch } from 'cloakbrowser';

const EMAIL = 'jl3lovegrouptravel@gmail.com';
const PW = 'Falcons4me!';
const NicholsUrl = "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?P4lRDbrpl6KimySo%2fK4o%2bwDZRcXP9mymm6bgZqnsScH38MGZtQLDbVpf764ZzfTpNPFFP6eqcei3a2Ce6Xvxyh5hFqPfV%2fyA";

async function run() {
  console.log("Launching CloakBrowser to target Stockholm (Pacific Rim) for Nichols...");
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
    
    console.log("Loading Nichols main page...");
    await page.goto(NicholsUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(8000);
    
    const diningHref = await page.evaluate(() => {
      const a = [...document.querySelectorAll('a')].find(el => (el.innerText || '').toLowerCase().includes('dining'));
      return a ? a.getAttribute('href') : null;
    });
    
    const fullDiningUrl = diningHref.startsWith('http') ? diningHref : 'https://www.rssc.com' + diningHref;
    console.log("Loading Nichols dining page...");
    await page.goto(fullDiningUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(8000);
    
    // Select Pacific Rim in the dropdown first!
    console.log("Selecting Pacific Rim in dropdown...");
    await page.evaluate(() => {
      const select = document.getElementById('uxBookedCruiseWrapper_uxCustomize_uxBookDining_uxRestaurantsDropDownList');
      if (select) {
        select.value = 'Pacific Rim';
        // Trigger change event
        const event = document.createEvent('HTMLEvents');
        event.initEvent('change', true, true);
        select.dispatchEvent(event);
      }
    });
    await page.waitForTimeout(5000);
    
    // Make sure Itinerary View is active
    await page.evaluate(() => { if (typeof ShowItinView === 'function') ShowItinView(); });
    await page.waitForTimeout(1000);
    
    // Click Day 1 (Stockholm - Pacific Rim)
    console.log("Clicking Day 1 (Pacific Rim)...");
    try {
      await page.evaluate(() => { if (typeof ChangeDiningDay === 'function') ChangeDiningDay('1'); });
    } catch (e) {
      console.log("Postback triggered...");
    }
    
    await page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 20000 }).catch(()=>{});
    await page.waitForTimeout(5000);
    
    // Wait for compilation
    let detailedText = '';
    for (let retry = 0; retry < 5; retry++) {
      try {
        await page.evaluate(() => { if (typeof ShowItinView === 'function') ShowItinView(); }).catch(()=>{});
        detailedText = await page.evaluate(() => {
          const el = document.getElementById('detailedInfo2') || document.getElementById('excursionSelections');
          return el ? el.innerText : '';
        });
        if (detailedText && !detailedText.includes('{{') && detailedText.trim().length > 10) {
          break;
        }
      } catch (e) {}
      await page.waitForTimeout(2000);
    }
    
    console.log("Detailed Text for Stockholm (Pacific Rim):");
    console.log(detailedText);
    
  } catch (err) {
    console.error("Error:", err);
  } finally {
    if (browser) await browser.close();
  }
}

run();
