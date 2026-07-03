import { launch } from 'cloakbrowser';
import { writeFileSync } from 'fs';
const OUT = '/home/john/Thunderbird/validations/lyons_silversea';
const EMAIL = process.env.SS_EMAIL, PW = process.env.SS_PW;
const log = (m) => process.stderr.write(m + '\n');
let browser;
try {
  browser = await launch({ headless: true, humanize: true });
  const page = await browser.newPage();
  await page.goto('https://my.silversea.com/', { waitUntil:'networkidle', timeout:60000 }).catch(()=>{});
  await page.waitForTimeout(4000);
  log('landed: title="'+(await page.title())+'" url='+page.url().slice(0,60));
  try { await page.click('#onetrust-accept-btn-handler,[id*=accept]', {timeout:4000}); } catch(_){}
  const fields = await page.evaluate(()=>[...document.querySelectorAll('input')].map(i=>({type:i.type,id:i.id,name:i.name,ph:i.placeholder})).filter(f=>f.type!=='hidden'));
  log('fields: '+JSON.stringify(fields));
  writeFileSync(OUT+'/logon_fields.json', JSON.stringify(fields,null,1));
  await page.screenshot({path:OUT+'/03_logon.png'});
  // Attempt fill on the most likely user/pass fields
  const uSel = await page.evaluate(()=>{const e=document.querySelector('input[type=email],input[name*=ser i],input[id*=mail],input[id*=ser],input[name*=mail]');return e?(e.id?'#'+e.id:'[name="'+e.name+'"]'):null;});
  const pSel = await page.evaluate(()=>{const e=document.querySelector('input[type=password]');return e?(e.id?'#'+e.id:'[name="'+e.name+'"]'):null;});
  log('user sel='+uSel+' pass sel='+pSel);
  if (uSel && pSel){
    await page.fill(uSel, EMAIL); await page.fill(pSel, PW);
    await page.evaluate(()=>{const b=document.querySelector('button[type=submit],input[type=submit],button');if(b)b.click();});
    await page.waitForTimeout(8000);
    const t = (await page.evaluate(()=>document.body.innerText)).toLowerCase();
    const ok = /welcome|my voyage|booked|sign out|log out|dashboard|nancy/.test(t);
    const err = /incorrect|invalid|not recogn�|does not match|unable to|error/.test(t);
    log('RESULT ok='+ok+' err='+err+' url='+page.url().slice(0,60)+' title="'+(await page.title())+'"');
    writeFileSync(OUT+'/04_result.txt', await page.evaluate(()=>document.body.innerText));
    await page.screenshot({path:OUT+'/04_result.png'});
  } else { log('could not locate login fields'); }
  process.exit(0);
} catch(e){ log('ERR '+e.message); process.exit(1); }
finally { if(browser) try{await browser.close();}catch(_){} }
