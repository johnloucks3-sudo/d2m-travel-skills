import { launch } from 'cloakbrowser';
import { writeFileSync } from 'fs';

const OUT = '/home/john/Thunderbird/validations/rssc_scrape';
const EMAIL = 'jl3lovegrouptravel@gmail.com';
const PW = 'Falcons4me!';

const mainUrls = {
  "Ely": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?McWU05z77cmpnbQbEo2CdOumw8lV3LRNPvEArhnrrs3hl5RgmNGc6tgCF0LEwSWn9KttcnSG6QV03Ue0ckTSqA%3d%3d",
  "Nichols": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?P4lRDbrpl6KimySo%2fK4o%2bwDZRcXP9mymm6bgZqnsScH38MGZtQLDbVpf764ZzfTpNPFFP6eqcei3a2Ce6Xvxyh5hFqPfV%2fyA",
  "Furlow": "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?eecDnW0xAFxbgFqHZBS8Eko5Uc3K5UTVHzz%2b5iUsOMeF38Ba0f%2bR5xYgM6Gv3nm1CyaweMg7GG8DwKCVXbjhAg%3d%3d"
};

async function run() {
  console.log("Launching CloakBrowser...");
  let browser;
  try {
    browser = await launch({ headless: true, humanize: true });
    
    // Create login page
    const loginPage = await browser.newPage();
    console.log("Logging in...");
    await loginPage.goto("https://www.rssc.com/agent/default.aspx", { waitUntil: 'domcontentloaded', timeout: 60000 });
    await loginPage.waitForTimeout(5000);
    try { await loginPage.click('#onetrust-accept-btn-handler', { timeout: 3000 }); } catch(_) {}
    
    await loginPage.fill('#uxAgentHomePage_uxAgentRegister_uxLoginEmailAddressTextbox', EMAIL);
    await loginPage.fill('#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox', PW);
    await loginPage.focus('#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox');
    await loginPage.keyboard.press('Enter');
    await loginPage.waitForTimeout(10000);
    await loginPage.close();
    
    const results = {};
    
    for (const [name, mainUrl] of Object.entries(mainUrls)) {
      console.log(`\n=== Scraping Dining Times for ${name} ===`);
      results[name] = [];
      
      let clientPage;
      try {
        // Open a fresh tab for this client
        clientPage = await browser.newPage();
        
        console.log(`Loading main page for ${name}...`);
        await clientPage.goto(mainUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
        await clientPage.waitForTimeout(8000);
        
        // Find dining link
        const diningHref = await clientPage.evaluate(() => {
          const a = [...document.querySelectorAll('a')].find(el => (el.innerText || '').toLowerCase().includes('dining'));
          return a ? a.getAttribute('href') : null;
        });
        
        if (!diningHref) {
          console.log("No dining link found on main page.");
          await clientPage.close();
          continue;
        }
        
        const fullDiningUrl = diningHref.startsWith('http') ? diningHref : 'https://www.rssc.com' + diningHref;
        console.log(`Navigating to dining URL: ${fullDiningUrl}`);
        await clientPage.goto(fullDiningUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
        await clientPage.waitForTimeout(8000);
        
        // Find all day items with reservations
        const dayItems = await clientPage.evaluate(() => {
          const items = [...document.querySelectorAll('li[onclick*="ChangeDiningDay"]')];
          return items.map(li => {
            const onclick = li.getAttribute('onclick') || '';
            const match = onclick.match(/ChangeDiningDay\('(\d+)'\)/);
            return {
              text: (li.innerText || '').replace(/\n/g, ' ').trim(),
              index: match ? match[1] : null
            };
          }).filter(item => item.index !== null && item.text.toLowerCase().includes('reservation in'));
        });
        
        console.log(`Found ${dayItems.length} reservations:`, dayItems);
        
        for (const item of dayItems) {
          console.log(`Selecting day index ${item.index} (${item.text})...`);
          
          try {
            await clientPage.evaluate(() => { if (typeof ShowItinView === 'function') ShowItinView(); });
          } catch (e) {
            console.warn("ShowItinView 1 warning:", e.message);
          }
          await clientPage.waitForTimeout(1000);
          
          try {
            await clientPage.evaluate(idx => { if (typeof ChangeDiningDay === 'function') ChangeDiningDay(idx); }, item.index);
          } catch (e) {
            console.log("ChangeDiningDay triggered postback...");
          }
          
          // Wait for the postback to load, then use a polling loop to extract stabilized text
          let detailedText = '';
          for (let retry = 0; retry < 10; retry++) {
            await clientPage.waitForTimeout(1500);
            try {
              await clientPage.evaluate(() => { if (typeof ShowItinView === 'function') ShowItinView(); }).catch(()=>{});
              detailedText = await clientPage.evaluate(() => {
                const el = document.getElementById('detailedInfo2') || document.getElementById('excursionSelections');
                return el ? el.innerText : '';
              });
              
              if (detailedText && !detailedText.includes('{{') && detailedText.trim().length > 10) {
                break;
              }
            } catch (e) {
              // ignore context destroyed errors and let next poll retry
            }
          }
          
          let foundTime = "Not found";
          const lines = detailedText.split('\n');
          for (const line of lines) {
            if (line.includes('(Reserved)') || line.includes('Dinner')) {
              foundTime = line.trim();
              break;
            }
          }
          
          if (foundTime === "Not found") {
            const html = await clientPage.content();
            const matches = html.match(/<p class="time">([\s\S]*?)<\/p>[\s\S]*?<p class="description">[\s\S]*?<a[\s\S]*?>\s*(.*?)\s*<\/a>/i);
            if (matches) {
              foundTime = `${matches[1].trim()} ${matches[2].trim()}`;
            }
          }
          
          console.log(`  Result text: ${detailedText.replace(/\n/g, ' ').slice(0, 150)}`);
          console.log(`  Extracted Time: ${foundTime}`);
          
          results[name].push({
            day_text: item.text,
            day_index: item.index,
            details: detailedText,
            extracted_time: foundTime
          });
        }
      } catch (err) {
        console.error(`Error processing ${name}:`, err);
      } finally {
        if (clientPage) {
          await clientPage.close().catch(()=>{});
        }
      }
    }
    
    writeFileSync(`${OUT}/live_dining_times_scraped_final.json`, JSON.stringify(results, null, 2));
    console.log("\nSaved all dining times to live_dining_times_scraped_final.json!");
    
  } catch (err) {
    console.error("General error:", err);
  } finally {
    if (browser) await browser.close();
  }
}

run();
