import { launch } from 'cloakbrowser';
import { writeFileSync } from 'fs';

const OUT = '/home/john/Thunderbird/validations/rssc_scrape';
const EMAIL = 'jl3lovegrouptravel@gmail.com';
const PW = 'Falcons4me!';

const diningUrls = {
  "Ely": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?McWU05z77cmpnbQbEo2CdOumw8lV3LRNPvEArhnrrs3hl5RgmNGc6tgCF0LEwSWn9KttcnSG6QUQgRzWRDSMkR5hFqPfV%2fyA",
  "Nichols": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?P4lRDbrpl6KimySo%2fK4o%2bwDZRcXP9mymm6bgZqnsScH38MGZtQLDbVpf764ZzfTpNPFFP6eqcei3a2Ce6vxymsS6iwAHa%2be",
  "Furlow": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?eecDnW0xAFxbgFqHZBS8Eko5Uc3K5UTVHzz%2b5iUsOMeF38Ba0f%2bR5xYgM6Gv3nm1CyaweMg7GG9tyKy%2fzaQxv63HngciufiK"
};

async function run() {
  console.log("Launching CloakBrowser to scrape dining reservation times...");
  let browser;
  try {
    browser = await launch({ headless: true, humanize: true });
    const page = await browser.newPage();
    
    console.log("Logging in to agent portal...");
    await page.goto("https://www.rssc.com/agent/default.aspx", { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000);
    
    try { await page.click('#onetrust-accept-btn-handler', { timeout: 3000 }); } catch(_) {}
    
    await page.fill('#uxAgentHomePage_uxAgentRegister_uxLoginEmailAddressTextbox', EMAIL);
    await page.fill('#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox', PW);
    await page.focus('#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(10000);
    
    const results = {};
    
    for (const [name, url] of Object.entries(diningUrls)) {
      console.log(`\n--- Processing dining for ${name} ---`);
      results[name] = [];
      try {
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
        await page.waitForTimeout(8000);
        
        // Find all day items with reservations
        const dayItems = await page.evaluate(() => {
          const items = [...document.querySelectorAll('li[onclick*="ChangeDiningDay"]')];
          return items.map(li => {
            const onclick = li.getAttribute('onclick') || '';
            const match = onclick.match(/ChangeDiningDay\('(\d+)'\)/);
            return {
              text: (li.innerText || '').replace(/\n/g, ' ').trim(),
              index: match ? match[1] : null
            };
          }).filter(item => item.index !== null && item.text.includes('Reservation in'));
        });
        
        console.log(`Found ${dayItems.length} reservations for ${name}:`, dayItems);
        
        for (const item of dayItems) {
          console.log(`Selecting day index ${item.index} (${item.text})...`);
          
          // Make sure Itinerary View is active
          await page.evaluate(() => {
            if (typeof ShowItinView === 'function') ShowItinView();
          });
          await page.waitForTimeout(1000);
          
          // Click/change day
          await page.evaluate(idx => {
            if (typeof ChangeDiningDay === 'function') ChangeDiningDay(idx);
          }, item.index);
          await page.waitForTimeout(4000);
          
          // Extract detailed text
          const detailedText = await page.evaluate(() => {
            const el = document.getElementById('detailedInfo2') || document.getElementById('excursionSelections');
            return el ? el.innerText : '';
          });
          
          console.log(`Detailed Text for Day ${item.index}:`, detailedText.replace(/\n/g, ' ').slice(0, 150));
          
          // Save result
          results[name].push({
            day_text: item.text,
            day_index: item.index,
            details: detailedText
          });
        }
        
      } catch (err) {
        console.error(`Error scraping dining for ${name}:`, err);
      }
    }
    
    writeFileSync(`${OUT}/live_dining_times_scraped.json`, JSON.stringify(results, null, 2));
    console.log("\nSaved all dining details to live_dining_times_scraped.json!");
    
  } catch (err) {
    console.error("General error:", err);
  } finally {
    if (browser) await browser.close();
  }
}

run();
