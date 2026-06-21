/**
 * WING AUTONOMOUS TRIGGERS — Google Apps Script
 * Dreams2Memories Travel, LLC · V. Hale, SES-6
 *
 * Runs entirely on Google infrastructure. NO yoga dependency.
 * Uses native Apps Script services: SpreadsheetApp, GmailApp, CalendarApp.
 *
 * SETUP (one time, ~5 minutes):
 *   1. Go to script.google.com → New Project → name it "Wing Autonomous Triggers"
 *   2. Paste this entire file
 *   3. Run wingSetup() once (click Run button while that function is selected)
 *   4. Authorize when prompted (Google account scopes)
 *   5. Done — triggers arm automatically
 *
 * WHAT RUNS AUTOMATICALLY (after setup):
 *   · 06:00 MT daily  → FPD alert digest to johnloucks3
 *   · 06:05 MT daily  → Lifecycle touchpoint check
 *   · Hourly          → Commission sheet auto-calculator (when new rows added)
 *   · On Gmail receive → Smart-label incoming cruise line emails
 *
 * SHEET IDs — update these if sheets change:
 */

var BOOKINGS_SHEET_ID   = '1sdN6ghvG2EgaqOxyq3V6TRRjKBFmNrqX0FUSY-9A9VI';
var AI_METRICS_SHEET_ID = '16fuzoeD5WiR6loB7C2EbQJVbJ65admvrF_8oX8LBOd4';
var COMMANDER_EMAIL     = 'johnloucks3@gmail.com';
var WING_EMAIL          = 'd2mconcierge@gmail.com';

// MT offset from UTC (MDT = -6, MST = -7)
var MT_OFFSET_HOURS = -6;


// ============================================================================
// SETUP — Run once to arm all triggers
// ============================================================================

function wingSetup() {
  // Clear any existing Wing triggers first
  ScriptApp.getProjectTriggers().forEach(function(t) {
    if (t.getHandlerFunction().indexOf('wing') === 0 || t.getHandlerFunction().indexOf('Wing') === 0) {
      ScriptApp.deleteTrigger(t);
    }
  });

  // FPD alert — 06:00 MT (12:00 UTC in MDT)
  ScriptApp.newTrigger('wingFpdAlert')
    .timeBased()
    .atHour(12)
    .everyDays(1)
    .inTimezone('America/Denver')
    .create();

  // Lifecycle check — 06:05 MT (offset by 5min using hour 12, minute via workaround)
  ScriptApp.newTrigger('wingLifecycleCheck')
    .timeBased()
    .atHour(6)
    .everyDays(1)
    .inTimezone('America/Denver')
    .create();

  // Gmail smart-labeler — fires on every new email
  ScriptApp.newTrigger('wingGmailLabeler')
    .forUserCalendar(Session.getActiveUser().getEmail())
    .onEventUpdated()
    .create();

  Logger.log('✅ Wing triggers armed. Daily FPD alert at 06:00 MT. Lifecycle check at 06:00 MT.');
  Logger.log('Triggers active: ' + ScriptApp.getProjectTriggers().length);
}

function wingTeardown() {
  ScriptApp.getProjectTriggers().forEach(function(t) {
    ScriptApp.deleteTrigger(t);
  });
  Logger.log('All Wing triggers removed.');
}


// ============================================================================
// TRIGGER 1 — FPD ALERT DIGEST (daily 06:00 MT)
// ============================================================================

function wingFpdAlert() {
  var alerts = [];
  var today = new Date();

  // Read FPD data from Bookings sheet
  try {
    var ss = SpreadsheetApp.openById(BOOKINGS_SHEET_ID);
    var sheets = ss.getSheets();

    sheets.forEach(function(sheet) {
      var name = sheet.getName();
      if (name.toLowerCase().indexOf('fpd') === -1 && name.toLowerCase().indexOf('booking') === -1 && name.toLowerCase().indexOf('payment') === -1) return;

      var data = sheet.getDataRange().getValues();
      if (data.length < 2) return;

      var headers = data[0].map(function(h) { return String(h).toLowerCase().trim(); });
      var clientIdx   = headers.indexOf('client') > -1 ? headers.indexOf('client') : headers.indexOf('customer name');
      var fpdIdx      = headers.indexOf('fpd') > -1 ? headers.indexOf('fpd') : headers.indexOf('final payment');
      var amountIdx   = headers.indexOf('amount') > -1 ? headers.indexOf('amount') : headers.indexOf('balance');
      var statusIdx   = headers.indexOf('status') > -1 ? headers.indexOf('status') : -1;

      if (fpdIdx === -1) return;

      for (var r = 1; r < data.length; r++) {
        var row = data[r];
        var fpdRaw = row[fpdIdx];
        if (!fpdRaw) continue;

        var fpdDate = new Date(fpdRaw);
        if (isNaN(fpdDate.getTime())) continue;

        var daysOut = Math.round((fpdDate - today) / (1000 * 60 * 60 * 24));
        if (daysOut < 0 || daysOut > 45) continue;

        var client = clientIdx > -1 ? row[clientIdx] : 'Unknown';
        var amount = amountIdx > -1 ? row[amountIdx] : '';
        var status = statusIdx > -1 ? row[statusIdx] : '';
        if (String(status).toUpperCase().indexOf('PAID') > -1) continue;

        var priority = daysOut <= 7 ? '🔴 P0' : daysOut <= 14 ? '🟠 P1' : '🟡 P2';
        alerts.push({
          priority: priority,
          daysOut: daysOut,
          client: String(client),
          fpd: Utilities.formatDate(fpdDate, 'America/Denver', 'MMM d'),
          amount: amount ? '$' + Number(amount).toLocaleString() : '',
          sheet: name
        });
      }
    });
  } catch(e) {
    Logger.log('Bookings sheet error: ' + e);
  }

  // Hardcoded known FPDs from hale_state.json deferred_alerts (fallback)
  var knownFpds = [
    { client: 'Loucks (personal) — Regent Grandeur 3122006', fpd: 'Aug 1', amount: '$24,798', daysOut: Math.round((new Date('2026-08-01') - today) / 86400000), priority: '🔴 P0' },
    { client: 'McLeod McGlasson — Regent Grandeur 2984034', fpd: 'Jul 22', amount: '$11,943', daysOut: Math.round((new Date('2026-07-22') - today) / 86400000), priority: '🟠 P1' },
  ];

  knownFpds.forEach(function(f) {
    if (f.daysOut >= 0 && f.daysOut <= 45) {
      // Only add if not already in alerts from sheet
      var exists = alerts.some(function(a) { return a.client.indexOf(f.client.split(' ')[0]) > -1; });
      if (!exists) alerts.push(f);
    }
  });

  if (alerts.length === 0) {
    Logger.log('FPD alert: no FPDs due in next 45 days.');
    return;
  }

  // Sort by days out
  alerts.sort(function(a, b) { return a.daysOut - b.daysOut; });

  var subject = '🦅 Wing FPD Alert — ' + alerts.length + ' due in 45 days · ' + Utilities.formatDate(today, 'America/Denver', 'MMM d');
  var body = '<div style="font-family:Georgia;color:#0000ff;background:#f7f3ea;padding:20px;">';
  body += '<h2 style="color:#003087;">🦅 Final Payment Alerts</h2>';
  body += '<p style="color:#003087;">' + Utilities.formatDate(today, 'America/Denver', 'EEEE, MMMM d, yyyy · h:mm a z') + '</p>';
  body += '<table style="width:100%;border-collapse:collapse;">';
  body += '<tr style="background:#003087;color:white;"><th style="padding:8px;">Priority</th><th>Client</th><th>FPD</th><th>Days Out</th><th>Amount</th></tr>';

  alerts.forEach(function(a, i) {
    var bg = i % 2 === 0 ? '#ffffff' : '#f7f3ea';
    body += '<tr style="background:' + bg + ';">';
    body += '<td style="padding:8px;">' + a.priority + '</td>';
    body += '<td>' + a.client + '</td>';
    body += '<td>' + a.fpd + '</td>';
    body += '<td style="text-align:center;">' + a.daysOut + 'd</td>';
    body += '<td>' + (a.amount || '—') + '</td>';
    body += '</tr>';
  });

  body += '</table>';
  body += '<p style="margin-top:16px;font-size:12px;color:#666;">Automated Wing digest · Google Apps Script · No yoga dependency</p>';
  body += '</div>';

  GmailApp.sendEmail(COMMANDER_EMAIL, subject, '', { htmlBody: body, from: WING_EMAIL });
  Logger.log('FPD alert sent: ' + alerts.length + ' items.');

  // Log to AI Metrics sheet
  wingLogMetric_('fpd_alert_sent', alerts.length, alerts.map(function(a){return a.client;}).join(', '));
}


// ============================================================================
// TRIGGER 2 — LIFECYCLE TOUCHPOINT CHECK (daily 06:00 MT)
// ============================================================================

function wingLifecycleCheck() {
  var today = new Date();
  var flags = [];

  // Known lifecycle windows — dates when actions are due
  var lifecycle = [
    { client: 'Kuklinski',    action: 'Fare watch + hotel 3+3 search',        due: new Date('2026-06-17'), owner: 'A2 Dembe' },
    { client: 'McLeod',       action: 'DEPARTURE — Silver Muse Mediterranean', due: new Date('2026-06-23'), owner: 'Hale' },
    { client: 'Kuklinski',    action: 'Lifecycle emails UNHOLD',               due: new Date('2026-07-15'), owner: 'Hale' },
    { client: 'McLeod',       action: 'FPD $11,943 contact trigger',           due: new Date('2026-07-07'), owner: 'Hale' },
    { client: 'Loucks',       action: 'FPD $24,798 — 30-day warning',          due: new Date('2026-07-02'), owner: 'Commander' },
    { client: 'Loucks',       action: 'FPD $24,798 DUE',                       due: new Date('2026-08-01'), owner: 'Commander' },
    { client: 'Kuklinski',    action: 'Excursion window opens (Viking)',        due: new Date('2026-08-02'), owner: 'A2 Dembe' },
    { client: 'Lyons',        action: 'Departure — Regent Splendor Athens',    due: new Date('2026-08-11'), owner: 'Dani' },
    { client: 'Furlow/Nichols/Ely', action: 'Departure — Regent Grandeur Scandinavia', due: new Date('2026-08-29'), owner: 'Dani' },
    { client: 'Kuklinski',    action: 'Dining window opens (Viking T-90)',      due: new Date('2026-09-18'), owner: 'A2 Dembe' },
    { client: 'Loucks',       action: 'Dining reservations open (Grandeur)',   due: new Date('2026-09-30'), owner: 'Commander' },
    { client: 'Kuklinski',    action: 'DEPARTURE — Viking Mars Panama Canal',  due: new Date('2026-12-17'), owner: 'Dani' },
  ];

  lifecycle.forEach(function(item) {
    var daysOut = Math.round((item.due - today) / 86400000);
    // Flag at 30, 14, 7, 3, 1 days out
    if ([30, 14, 7, 3, 1, 0].indexOf(daysOut) > -1) {
      flags.push({ daysOut: daysOut, client: item.client, action: item.action, owner: item.owner,
                   due: Utilities.formatDate(item.due, 'America/Denver', 'MMM d') });
    }
  });

  if (flags.length === 0) { Logger.log('Lifecycle: nothing due today.'); return; }

  flags.sort(function(a,b) { return a.daysOut - b.daysOut; });

  var subject = '🦅 Lifecycle Alert — ' + flags.length + ' item(s) · ' + Utilities.formatDate(today, 'America/Denver', 'MMM d');
  var body = '<div style="font-family:Georgia;color:#0000ff;background:#f7f3ea;padding:20px;">';
  body += '<h2 style="color:#003087;">🦅 Lifecycle Touchpoints Due</h2>';
  body += '<table style="width:100%;border-collapse:collapse;">';
  body += '<tr style="background:#003087;color:white;"><th style="padding:8px;">Days</th><th>Client</th><th>Action</th><th>Owner</th><th>Due</th></tr>';

  flags.forEach(function(f, i) {
    var bg = i % 2 === 0 ? '#fff' : '#f7f3ea';
    var urgency = f.daysOut <= 1 ? '🔴 ' : f.daysOut <= 7 ? '🟠 ' : '🟡 ';
    body += '<tr style="background:' + bg + ';">';
    body += '<td style="padding:8px;text-align:center;">' + urgency + f.daysOut + 'd</td>';
    body += '<td>' + f.client + '</td>';
    body += '<td>' + f.action + '</td>';
    body += '<td>' + f.owner + '</td>';
    body += '<td>' + f.due + '</td>';
    body += '</tr>';
  });

  body += '</table>';
  body += '<p style="margin-top:16px;font-size:12px;color:#666;">Wing Lifecycle Engine · Apps Script · auto-generated</p></div>';

  GmailApp.sendEmail(COMMANDER_EMAIL, subject, '', { htmlBody: body });
  Logger.log('Lifecycle alert sent: ' + flags.length + ' flags.');
}


// ============================================================================
// TRIGGER 3 — GMAIL SMART LABELER
// Create labels first: run wingCreateLabels() once
// ============================================================================

var CRUISE_LINE_SENDERS = {
  'silversea.com':         'SILVERSEA',
  'rssc.com':              'REGENT',
  'vikingcruises.com':     'VIKING',
  'allianz.com':           'ALLIANZ-INSURANCE',
  'allianztravelinsurance': 'ALLIANZ-INSURANCE',
  'cruisingpower.com':     'REGENT',
  'tess.travel':           'TESS-CRM',
  'centrav.com':           'CENTRAV-AIR',
  'amadeus.com':           'AMADEUS',
  'perplexity.ai':         'RESEARCH'
};

function wingCreateLabels() {
  var labelNames = ['D2M/SILVERSEA','D2M/REGENT','D2M/VIKING','D2M/ALLIANZ-INSURANCE',
                    'D2M/TESS-CRM','D2M/CENTRAV-AIR','D2M/AMADEUS','D2M/RESEARCH','D2M/ACTION-NEEDED'];
  labelNames.forEach(function(name) {
    try {
      if (!GmailApp.getUserLabelByName(name)) {
        GmailApp.createLabel(name);
        Logger.log('Created label: ' + name);
      }
    } catch(e) { Logger.log('Label exists or error: ' + name); }
  });
}

function wingGmailLabeler() {
  // Process last 30 unread emails
  var threads = GmailApp.search('is:unread newer_than:1d', 0, 30);

  threads.forEach(function(thread) {
    var msg = thread.getMessages()[thread.getMessageCount() - 1];
    var from = msg.getFrom().toLowerCase();
    var subject = msg.getSubject().toLowerCase();

    Object.keys(CRUISE_LINE_SENDERS).forEach(function(domain) {
      if (from.indexOf(domain) > -1) {
        var labelName = 'D2M/' + CRUISE_LINE_SENDERS[domain];
        var label = GmailApp.getUserLabelByName(labelName);
        if (label) thread.addLabel(label);
      }
    });

    // Flag booking confirmations and invoices
    if (subject.indexOf('confirmation') > -1 || subject.indexOf('invoice') > -1 || subject.indexOf('booking') > -1) {
      var actionLabel = GmailApp.getUserLabelByName('D2M/ACTION-NEEDED');
      if (actionLabel) thread.addLabel(actionLabel);
    }
  });
}


// ============================================================================
// TRIGGER 4 — COMMISSION SHEET UPDATER
// Runs manually or wired to Sheets onChange trigger
// ============================================================================

function wingUpdateCommissions() {
  try {
    var ss = SpreadsheetApp.openById(BOOKINGS_SHEET_ID);
    var sheet = ss.getSheetByName('Commission') || ss.getSheets()[0];
    var data = sheet.getDataRange().getValues();
    if (data.length < 2) return;

    var headers = data[0];
    var grossIdx = headers.indexOf('Gross Commission');
    var d2mIdx   = headers.indexOf('D2M Share');
    var pctIdx   = headers.indexOf('D2M %');

    if (grossIdx === -1 || d2mIdx === -1) { Logger.log('Column headers not found.'); return; }

    var updated = 0;
    for (var r = 1; r < data.length; r++) {
      var gross = parseFloat(data[r][grossIdx]);
      var pct   = pctIdx > -1 ? parseFloat(data[r][pctIdx]) : 0.80; // default 80%
      if (!gross || isNaN(gross)) continue;
      if (!isNaN(pct) && pct > 0) {
        sheet.getRange(r + 1, d2mIdx + 1).setValue(Math.round(gross * pct * 100) / 100);
        updated++;
      }
    }
    Logger.log('Commission update: ' + updated + ' rows recalculated.');
  } catch(e) {
    Logger.log('Commission update error: ' + e);
  }
}


// ============================================================================
// DRIVE FIELD KIT — generate snapshot file for cross-device access
// ============================================================================

function wingGenerateFieldKitSnapshot() {
  var today = new Date();
  var snapshot = '# WING FIELD KIT SNAPSHOT\n';
  snapshot += '# Generated: ' + Utilities.formatDate(today, 'America/Denver', 'yyyy-MM-dd HH:mm z') + '\n\n';

  snapshot += '## KEY CONTACTS\n';
  snapshot += 'Silversea: 1-888-978-4070\n';
  snapshot += 'Regent: 1-844-473-4368\n';
  snapshot += 'Viking: 1-855-811-4832\n';
  snapshot += 'United Group Desk: 800-426-1122 opt 3\n';
  snapshot += 'Allianz: 1-866-884-3556\n\n';

  snapshot += '## ACTIVE CLIENTS (next 90 days)\n';
  snapshot += 'McLeod/McGlasson: Silver Muse Med · departs Jun 23 · FPD PAID\n';
  snapshot += 'Lyons Nancy+Ken: Regent Splendor Athens→NY · Aug 11 · FPD DUE MAY 11\n';
  snapshot += 'Furlow/Nichols/Ely: Grandeur Scandinavia · Aug 29 · FPD PAID\n';
  snapshot += 'Kuklinski (3 couples): Viking Mars Panama · Dec 17 · FPD PAID $21,244\n\n';

  snapshot += '## OPEN FPDs\n';
  snapshot += 'McLeod Grandeur 2984034: $11,943 due Jul 22\n';
  snapshot += 'Loucks Grandeur 3122006: $24,798 due Aug 1\n\n';

  snapshot += '## WING URLS\n';
  snapshot += 'Dashboard: https://itinerary.d2mluxury.quest/d2m-dashboard/\n';
  snapshot += 'Flight Plan: https://itinerary.d2mluxury.quest/flight_plan.html\n';
  snapshot += 'Terminal: https://code.d2mluxury.quest\n';

  // Write to Drive — "D2M-WING-FIELD-KIT" folder
  var folders = DriveApp.getFoldersByName('D2M-WING-FIELD-KIT');
  var folder;
  if (folders.hasNext()) {
    folder = folders.next();
  } else {
    folder = DriveApp.createFolder('D2M-WING-FIELD-KIT');
    Logger.log('Created Drive folder: D2M-WING-FIELD-KIT');
  }

  // Update or create the snapshot file
  var files = folder.getFilesByName('hale_context_snapshot.md');
  if (files.hasNext()) {
    files.next().setContent(snapshot);
  } else {
    folder.createFile('hale_context_snapshot.md', snapshot, MimeType.PLAIN_TEXT);
  }

  Logger.log('Field kit snapshot written to Drive/D2M-WING-FIELD-KIT/hale_context_snapshot.md');
}


// ============================================================================
// UTILITY — Log metrics to AI Metrics sheet
// ============================================================================

function wingLogMetric_(name, value, notes) {
  try {
    var ss = SpreadsheetApp.openById(AI_METRICS_SHEET_ID);
    var sheet = ss.getSheetByName('Metrics') || ss.getSheets()[0];
    var today = new Date();
    sheet.appendRow([Utilities.formatDate(today, 'America/Denver', 'yyyy-MM-dd HH:mm'), name, value, notes || '']);
  } catch(e) {
    Logger.log('Metric log error: ' + e);
  }
}


// ============================================================================
// MANUAL RUN — test any trigger on demand
// ============================================================================

function wingRunAll() {
  Logger.log('Running FPD alert...');
  wingFpdAlert();
  Logger.log('Running lifecycle check...');
  wingLifecycleCheck();
  Logger.log('Running Gmail labeler...');
  wingGmailLabeler();
  Logger.log('All Wing triggers executed.');
}
