#!/usr/bin/env node
// cloak_fetch.mjs — CloakBrowser stealth-fetch tier for Anansi escalation.
// Self-contained, domain-agnostic. Defeats Akamai/Imperva/Cloudflare where
// plain HTTP is walled. Available for ANY project, not scoped to any one
// site or vertical (cruise portals were just the first target).
// Usage: node cloak_fetch.mjs <url> [--output markdown|text|html] [--timeout ms] [--wait-for selector]
// Exit 0 with content on stdout; non-zero on failure/empty.
// FIXED 2026-07-09: fixed 3s post-load wait was too short for AJAX-heavy SPAs
// (confirmed live against Kayak — page returns mid-loading placeholder text
// "Loading results...", "Comparing flight sites..." instead of real content).
// Now polls for the loading-indicator pattern to clear (max --timeout budget)
// instead of a blind sleep. See MISSION-1499 log 2026-07-09.
import { launch } from 'cloakbrowser';

function arg(flag, def) {
  const i = process.argv.indexOf(flag);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : def;
}

const url = process.argv[2];
if (!url || url.startsWith('--')) {
  process.stderr.write('usage: node cloak_fetch.mjs <url> [--output markdown|text|html] [--timeout ms] [--wait-for selector]\n');
  process.exit(2);
}
const output = arg('--output', 'markdown');
const timeout = parseInt(arg('--timeout', '45000'), 10);
const waitForSelector = arg('--wait-for', null);

// Generic "still loading" text patterns seen across airline/OTA SPAs (Kayak,
// United, etc). Polls body text until none of these substrings are present,
// or until the timeout budget is exhausted — whichever comes first.
const LOADING_PATTERNS = [
  'loading results', 'comparing flight', 'searching for', 'please wait',
  'loading...', 'fetching prices', 'boarding group', 'finding flights',
];

async function waitForContentSettled(page, budgetMs) {
  const pollInterval = 500;
  const start = Date.now();
  let lastText = '';
  let stableCount = 0;
  while (Date.now() - start < budgetMs) {
    let text;
    try {
      text = await page.evaluate(() => document.body ? document.body.innerText.toLowerCase() : '');
    } catch (_) {
      // SPA client-side navigation destroyed the execution context mid-poll —
      // treat as still-loading and retry rather than aborting the fetch.
      await page.waitForTimeout(pollInterval);
      continue;
    }
    const stillLoading = LOADING_PATTERNS.some((p) => text.includes(p));
    if (!stillLoading) {
      // Also require text to have stabilized for 2 consecutive polls (AJAX
      // content sometimes finishes the loading-text swap but keeps re-rendering).
      if (text === lastText) {
        stableCount++;
        if (stableCount >= 2) return;
      } else {
        stableCount = 0;
      }
    }
    lastText = text;
    await page.waitForTimeout(pollInterval);
  }
}

// Light HTML→Markdown: strip scripts/styles, collapse whitespace. Good enough for content extraction.
function htmlToMarkdown(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<h([1-6])[^>]*>([\s\S]*?)<\/h\1>/gi, (_, n, t) => '\n' + '#'.repeat(+n) + ' ' + t.replace(/<[^>]+>/g, '').trim() + '\n')
    .replace(/<li[^>]*>([\s\S]*?)<\/li>/gi, (_, t) => '- ' + t.replace(/<[^>]+>/g, '').trim() + '\n')
    .replace(/<\/(p|div|br|tr)>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&#39;/g, "'").replace(/&quot;/g, '"')
    .replace(/\n{3,}/g, '\n\n').replace(/[ \t]{2,}/g, ' ').trim();
}

let browser;
try {
  browser = await launch({ headless: true, humanize: true });
  const page = await browser.newPage();
  const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout });
  const elapsedNav = Date.now();
  if (waitForSelector) {
    try {
      await page.waitForSelector(waitForSelector, { timeout: Math.max(1000, timeout - 5000) });
    } catch (_) {
      process.stderr.write('[cloak_fetch] --wait-for selector never appeared, continuing anyway\n');
    }
  } else {
    const remainingBudget = Math.max(3000, timeout - (Date.now() - elapsedNav));
    await waitForContentSettled(page, remainingBudget);
  }
  // Surface the HTTP status on stderr so the Python caller can parse it (stdout stays content-only).
  const httpStatus = resp && typeof resp.status === 'function' ? resp.status() : null;
  if (httpStatus != null) process.stderr.write('[cloak_fetch] HTTP ' + httpStatus + '\n');
  let content;
  // One retry on transient "execution context destroyed" — final SPA
  // client-side navigations can land right as we try to extract content.
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      if (output === 'html') {
        content = await page.content();
      } else if (output === 'text') {
        content = await page.evaluate(() => document.body ? document.body.innerText : '');
      } else {
        content = htmlToMarkdown(await page.content());
      }
      break;
    } catch (err) {
      if (attempt === 0 && /execution context was destroyed/i.test(err.message || '')) {
        await page.waitForTimeout(1000);
        continue;
      }
      throw err;
    }
  }
  content = (content || '').trim();
  if (!content) { process.stderr.write('[cloak_fetch] empty content\n'); process.exit(1); }
  process.stdout.write(content + '\n');
  process.exit(0);
} catch (err) {
  process.stderr.write('[cloak_fetch] error: ' + (err && err.message ? err.message : String(err)) + '\n');
  process.exit(1);
} finally {
  if (browser) { try { await browser.close(); } catch (_) {} }
}
