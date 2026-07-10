#!/usr/bin/env node
// One-off test: interactive form-fill (not deep-link) for a ROUND-TRIP
// united.com search, per Step 4 of the United flight-search task
// (2026-07-10). Navigate to homepage, fill origin/destination/dates as a
// real user would, click Search — test whether this avoids the round-trip
// silent-block that direct deep-linking hits.
import { launch } from 'cloakbrowser';

let browser;
try {
  browser = await launch({ headless: true, humanize: true });
  const page = await browser.newPage();
  await page.goto('https://www.united.com/en/us', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(2000);

  // Dismiss cookie banner if present
  try {
    const acceptBtn = page.getByRole('button', { name: /accept cookies/i });
    if (await acceptBtn.isVisible({ timeout: 3000 })) await acceptBtn.click();
  } catch (_) {}

  // Fill origin
  await page.fill('#originAirportCode, input[name="originAirportCode"], input[aria-label*="From"]', 'DEN').catch(async () => {
    const fromInput = page.locator('input').filter({ hasText: '' }).first();
  });
  await page.waitForTimeout(1000);

  console.log('SNAPSHOT_MARKER_BEGIN');
  console.log(await page.title());
  const bodyText = await page.evaluate(() => document.body.innerText.slice(0, 500));
  console.log(bodyText);
  console.log('SNAPSHOT_MARKER_END');
} catch (err) {
  console.error('error:', err.message);
} finally {
  if (browser) await browser.close();
}
