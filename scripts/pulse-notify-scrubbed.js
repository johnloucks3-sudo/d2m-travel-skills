#!/usr/bin/env node
'use strict';

/*
 * PII-scrubbing Notification hook for Claude-Pulse (B3 hardened).
 *
 * Replaces the stock notify-hook.js in settings.json.
 * Strips client names, booking IDs, email addresses, and file paths
 * from Claude's notification messages before sending to ntfy.sh.
 * Never blocks Claude (async, fire-and-forget, 2.5s timeout).
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const https = require('https');

// ── PII patterns ──────────────────────────────────────────────────────
// Client names to scrub — loaded from dossiers/ directory
const DOSSIER_DIR = path.join(os.homedir(), 'Thunderbird', 'dossiers');
const BOOKING_RE = /\b\d{6,8}[-]?\d{0,4}\b/g;          // booking refs
const EMAIL_RE   = /\b[\w.+-]+@[\w-]+\.[\w.-]+\b/g;     // emails
const PATH_RE    = /\/(?:home|tmp|Users)[\w/.@-]+/g;     // absolute paths

function loadClientNames() {
  // Curated list of actual D2M client surnames (plus their partners/spouses).
  // These are the real privacy-sensitive identifiers.
  const KNOWN_CLIENTS = [
    'Furlow', 'Kuklinski', 'McLeod', 'McGlasson', 'Lyons', 'Loucks',
    'Nichols', 'Spencer', 'Morton', 'Piontek', 'Rehfeldt', 'Trien',
    'Westbrook', 'Ely', 'Darrow', 'Heer', 'Langford', 'Riley',
    'Burcham', 'Britan', 'McLeran', 'Erik', 'Melissa', 'Erica',
    'Joshua', 'Nancy', 'Ken', 'Phillip', 'Kim', 'Richard', 'Sofi',
    'Steve', 'Brent', 'Stefanie', 'Sarah', 'Grace', 'Shawn', 'Ann',
    'Justin', 'Ryan',
  ];

  // Generic travel/business words that appear in filenames but are NOT PII.
  // Expanded list to avoid false positives.
  const STOPWORDS = new Set([
    'The','For','With','From','Group','Trip','Track','Guide','Data','Self',
    'Alaska','Allianz','Athens','Atlas','Baltic','Brief','Complete',
    'Correspondence','Coverage','Draft','Eligibility','Excursions',
    'Family','Grandeur','Hawaii','Itinerary','Japan','Lead','Mediterranean',
    'Monthly','Multi','Newport','Oceania','Pacific','Panama','Personal',
    'Prestige','Princess','Prospect','Regent','Research','Romance',
    'Scandi','Scandinavia','Senior','Test','Tips','Venice','Viking',
    'Drive','MultiTrip','Track','Timeline','Logistics','Matrix',
    'Amendment','Copy','ARCHIVE','Archive','CallPrep','App',
    'Season','To','Cheer','Lesser','Antilles','Mexico','Riviera',
    'North','Cape','Expedition','Free','Air','Picklist','TEMPLATE',
    'WorldTraveller','Leg3','Leg','Sister','Bay','Dec','Jan','Feb',
    'Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov',
    '2025','2026','2027','2028',
  ]);

  const names = [...KNOWN_CLIENTS];

  // Also scan dossiers for names we might have missed
  try {
    const files = fs.readdirSync(DOSSIER_DIR);
    for (const f of files) {
      if (!f.endsWith('.md')) continue;
      const base = f.replace(/\.md$/, '');
      const parts = base.split(/[\s_]+/);
      parts.forEach(p => {
        if (p.length < 3) return;
        if (STOPWORDS.has(p)) return;
        // Only catch capitalized words that look like proper names
        if (/^(?:Mc|Mac)?[A-Z][a-z]{2,}$/.test(p)) {
          names.push(p);
        }
      });
    }
  } catch (e) { /* dossiers dir may not exist */ }

  return [...new Set(names)];
}

function scrub(message, clientNames) {
  if (!message) return message;

  // Replace absolute paths
  let s = message.replace(PATH_RE, '[PATH]');
  // Replace booking IDs (numeric patterns)
  s = s.replace(BOOKING_RE, '[BOOKING]');
  // Replace email addresses
  s = s.replace(EMAIL_RE, '[EMAIL]');
  // Replace client names (case-insensitive, whole-word)
  for (const name of clientNames) {
    const re = new RegExp('\\b' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'gi');
    s = s.replace(re, '[CLIENT]');
  }

  // If scrubbing collapsed the message, provide a generic summary
  if (s.length < 5) s = 'Claude needs your attention';

  return s;
}

function classify(message) {
  const m = String(message || '').toLowerCase();
  if (m.includes('permission') || m.includes('approve') || m.includes('allow')) return 'permission';
  return 'notification';
}

// ── Config ────────────────────────────────────────────────────────────
function readConfig() {
  try {
    return JSON.parse(fs.readFileSync(path.join(os.homedir(), '.claude-pulse.json'), 'utf8'));
  } catch (e) { return {}; }
}

// ── ntfy push (with optional auth token) ─────────────────────────────
function pushNtfy(topic, title, message, tags) {
  if (!topic) return Promise.resolve();
  const cfg = readConfig();
  const accessToken = cfg.ntfyAccessToken || '';

  return new Promise(function (resolve) {
    const data = Buffer.from(message || '', 'utf8');
    const headers = {
      'Content-Type': 'text/plain; charset=utf-8',
      'Content-Length': data.length,
      'Title': String(title || 'Claude Code').replace(/[^\x20-\x7E]/g, ''),
      'Tags': tags || 'warning',
      'Priority': 'high',
    };
    if (accessToken) {
      headers['Authorization'] = 'Bearer ' + accessToken;
    }
    const req = https.request({
      method: 'POST',
      hostname: 'ntfy.sh',
      path: '/' + encodeURIComponent(topic),
      headers: headers,
    }, function (res) { res.on('data', function () {}); res.on('end', resolve); });
    req.on('error', resolve);
    req.write(data); req.end();
    setTimeout(resolve, 2500);
  });
}

// ── Event log (for Pulse dashboard) ──────────────────────────────────₀
function appendEvent(ev) {
  const runtimeDir = path.join(os.homedir(), '.claude-pulse');
  const eventsFile = path.join(runtimeDir, 'events.jsonl');
  try { fs.mkdirSync(runtimeDir, { recursive: true }); } catch (e) {}
  let lines = [];
  try { lines = fs.readFileSync(eventsFile, 'utf8').split('\n').filter(Boolean); } catch (e) {}
  lines.push(JSON.stringify(ev));
  if (lines.length > 200) lines = lines.slice(lines.length - 200);
  try { fs.writeFileSync(eventsFile, lines.join('\n') + '\n'); } catch (e) {}
}

// ── Main ──────────────────────────────────────────────────────────────
(async function main() {
  const clientNames = loadClientNames();

  // Read stdin
  let raw = '';
  if (!process.stdin.isTTY) {
    process.stdin.setEncoding('utf8');
    for await (const chunk of process.stdin) { raw += chunk; }
  }

  let input = {};
  try { input = JSON.parse(raw); } catch (e) {}

  const originalMessage = input.message || input.notification || 'Claude needs your attention';
  const message = scrub(originalMessage, clientNames);

  // Build event (scrubbed)
  const ev = {
    time: Date.now(),
    original: classify(originalMessage),
    sessionId: input.session_id || input.sessionId || null,
    cwd: input.cwd || null,
    message: message,   // scrubbed
    _scrubbed: (originalMessage !== message),
  };

  appendEvent(ev);

  const project = ev.cwd ? path.basename(ev.cwd) : '';
  const cfg = readConfig();
  const topic = cfg.ntfyTopic || '';

  if (topic) {
    await pushNtfy(topic,
      'Claude needs you' + (project ? ' (' + project + ')' : ''),
      message,
      'warning'
    );
  }

  process.exit(0);
})();
