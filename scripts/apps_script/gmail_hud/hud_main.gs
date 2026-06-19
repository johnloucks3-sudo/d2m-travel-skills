/**
 * Thunderbird Gmail HUD — hud_main.gs
 *
 * Gmail Add-on. Fires on EVERY email open (desktop + mobile).
 * Calls Claude Haiku for Wing intelligence → renders CardService card.
 * Works on iOS and Android Gmail app.
 *
 * Wing: Dreams2Memories Travel, LLC
 * Commander: John "Yoda" Loucks
 * COS: Victoria "Victory" Hale, SES-6
 * Version: 1.0 · 2026-06-19
 */

// ─── Wing knowledge base ──────────────────────────────────────────────────────

var D2M_CLIENTS = [
  'Kuklinski', 'McLeod', 'McGlasson', 'Furlow', 'Ely', 'Darrow',
  'Nichols', 'Westbrook', 'Spencer', 'Bryana', 'Loucks', 'Morton',
  'Dodge', 'How', 'Quick', 'Trien', 'Heer', 'Scandi'
];

var CRUISE_LINES = [
  'Silversea', 'Regent', 'Viking', 'Princess', 'Celebrity',
  'Holland America', 'Seabourn', 'Oceania', 'Crystal', 'Cunard',
  'Azamara', 'MSC', 'Norwegian', 'Royal Caribbean', 'Carnival',
  'Silver', 'Seven Seas', 'Windstar', 'Paul Gauguin', 'Ponant'
];

var CLAUDE_API_URL = 'https://api.anthropic.com/v1/messages';
var CLAUDE_MODEL   = 'claude-haiku-4-5-20251001';

// ─── main trigger ─────────────────────────────────────────────────────────────

/**
 * onGmailMessage — fires when Commander opens any email in Gmail.
 * e.gmail.messageId — the open email's ID
 * e.gmail.accessToken — scoped token for this message
 */
function onGmailMessage(e) {
  try {
    var messageId   = e.gmail.messageId;
    var accessToken = e.gmail.accessToken;
    GmailApp.setCurrentMessageAccessToken(accessToken);

    var message = GmailApp.getMessageById(messageId);
    if (!message) return buildErrorCard('Message not found.');

    var emailData = {
      subject: message.getSubject()   || '(no subject)',
      from:    message.getFrom()      || '',
      date:    message.getDate() ? message.getDate().toISOString() : '',
      body:    (message.getPlainBody() || '').substring(0, 3000)
    };

    // Fast local scan — zero API cost
    var scan = localPreScan(emailData);

    // Skip Claude for obvious junk
    if (scan.isSpam && !scan.isClient) {
      return buildSpamCard(emailData);
    }

    // Call Claude Haiku
    var intel = callClaude(emailData, scan);

    // Fallback if API key not set or call fails
    if (!intel) return buildFallbackCard(emailData, scan);

    return buildHudCard(intel, emailData);

  } catch (err) {
    return buildErrorCard('HUD: ' + err.message);
  }
}

/** Homepage card — shown when add-on opened without an email context */
function onHomepage() {
  return buildStatusCard();
}

// ─── local pre-scan (no API cost) ────────────────────────────────────────────

function localPreScan(email) {
  var text = (email.subject + ' ' + email.from + ' ' + email.body).toLowerCase();
  var fromLc = email.from.toLowerCase();

  var isClient = D2M_CLIENTS.some(function(c) {
    return text.indexOf(c.toLowerCase()) !== -1 || fromLc.indexOf(c.toLowerCase()) !== -1;
  });

  var isCruiseLine = CRUISE_LINES.some(function(c) {
    return fromLc.indexOf(c.toLowerCase()) !== -1;
  });

  var hasFinancial = /\$[\d,]+|\bpayment\b|\binvoice\b|\bbalance due\b|\bfpd\b|\bdeposit\b|\bcommission\b/i.test(text);
  var isUrgent     = /urgent|immediately|today only|overdue|past due|expires today|deadline|action required/i.test(text);
  var isSpam       = /unsubscribe|click here to|special offer|you've been selected|winner|prize/i.test(text);

  return { isClient: isClient, isCruiseLine: isCruiseLine, hasFinancial: hasFinancial, isUrgent: isUrgent, isSpam: isSpam };
}

// ─── Claude Haiku call ────────────────────────────────────────────────────────

function callClaude(emailData, scan) {
  var apiKey = PropertiesService.getUserProperties().getProperty('CLAUDE_API_KEY');
  if (!apiKey) return null;

  var clientHint = scan.isClient ? ' (LIKELY D2M CLIENT EMAIL — treat as P1 minimum)' : '';
  var finHint    = scan.hasFinancial ? ' (HAS FINANCIAL CONTENT — Harlan flag)' : '';

  var prompt =
    'You are the Thunderbird Wing HUD for Dreams2Memories Travel LLC — AI-powered luxury travel agency.\n' +
    'Commander John "Yoda" Loucks reads this on his phone when he opens email.\n' +
    'Be brief. Be useful. Wing posture: bottom-line-first, no fluff.\n\n' +
    'Known D2M clients: ' + D2M_CLIENTS.join(', ') + '\n' +
    'Known cruise line partners: ' + CRUISE_LINES.join(', ') + '\n' +
    'Local scan flags: client=' + scan.isClient + ' cruiseline=' + scan.isCruiseLine +
    ' financial=' + scan.hasFinancial + ' urgent=' + scan.isUrgent + clientHint + finHint + '\n\n' +
    'Email to analyze:\n' +
    'From: ' + emailData.from + '\n' +
    'Subject: ' + emailData.subject + '\n' +
    'Date: ' + emailData.date + '\n' +
    'Body:\n' + emailData.body + '\n\n' +
    'Respond with ONLY valid JSON — no markdown, no explanation:\n' +
    '{\n' +
    '  "category": "CLIENT_REPLY|SUPPLIER|BOOKING_CONFIRM|FINANCIAL|BOOKING_CHANGE|INTEL|INTERNAL|PERSONAL|VENDOR|MARKETING|SPAM",\n' +
    '  "priority": "P0|P1|P2|ROUTINE",\n' +
    '  "summary": "2 crisp sentences — what is this email about",\n' +
    '  "client_name": "D2M client first+last if identifiable, else null",\n' +
    '  "wing_action": "one sentence — what should Commander do with this right now",\n' +
    '  "financial_flag": "exact dollar amount or FPD date if mentioned, else null",\n' +
    '  "persona": "HALE|DANI|DEMBE|STERLING|HARLAN|NONE",\n' +
    '  "sender_org": "company/organization of sender if clear, else null"\n' +
    '}\n\n' +
    'P0=payment overdue/emergency/action<24h. P1=client comms/booking change. P2=supplier/vendor/fyi. ROUTINE=everything else.\n' +
    'persona: DANI=client voice/response needed, DEMBE=intel/research/cruise pricing, STERLING=process/tech/booking, HARLAN=financial verification, HALE=ops routing, NONE=personal/spam.';

  try {
    var resp = UrlFetchApp.fetch(CLAUDE_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01'
      },
      payload: JSON.stringify({
        model: CLAUDE_MODEL,
        max_tokens: 400,
        messages: [{ role: 'user', content: prompt }]
      }),
      muteHttpExceptions: true
    });

    if (resp.getResponseCode() !== 200) {
      Logger.log('Claude API HTTP ' + resp.getResponseCode() + ': ' + resp.getContentText().substring(0, 200));
      return null;
    }

    var result = JSON.parse(resp.getContentText());
    var text   = result.content[0].text.trim();
    var match  = text.match(/\{[\s\S]*\}/);
    if (!match) return null;

    return JSON.parse(match[0]);

  } catch (err) {
    Logger.log('Claude call failed: ' + err.message);
    return null;
  }
}

// ─── card builders ────────────────────────────────────────────────────────────

var PRIORITY_EMOJI = { P0: '🔴', P1: '🟡', P2: '🟢', ROUTINE: '⚪' };
var CATEGORY_EMOJI = {
  CLIENT_REPLY:    '👤',
  SUPPLIER:        '🚢',
  BOOKING_CONFIRM: '📋',
  FINANCIAL:       '💰',
  BOOKING_CHANGE:  '✏️',
  INTEL:           '🔍',
  INTERNAL:        '⚡',
  PERSONAL:        '👋',
  VENDOR:          '🏢',
  MARKETING:       '📣',
  SPAM:            '🗑️'
};
var PERSONA_LABEL = {
  HALE:     '⚡ Hale — ops/routing',
  DANI:     '✈️ Dani — client voice',
  DEMBE:    '🔍 Dembe — intel',
  STERLING: '📊 Sterling — process',
  HARLAN:   '💰 Harlan — financial',
  NONE:     '—'
};

function buildHudCard(intel, emailData) {
  var prio     = intel.priority || 'ROUTINE';
  var cat      = intel.category || 'EMAIL';
  var prioMark = PRIORITY_EMOJI[prio]     || '⚪';
  var catMark  = CATEGORY_EMOJI[cat]      || '📧';

  var card = CardService.newCardBuilder();

  card.setHeader(
    CardService.newCardHeader()
      .setTitle('⚡ Thunderbird HUD')
      .setSubtitle(prioMark + ' ' + prio + '  ' + catMark + ' ' + cat)
  );

  // ── Intel
  var intelSec = CardService.newCardSection().setHeader('Wing Intel');

  intelSec.addWidget(
    CardService.newTextParagraph().setText(intel.summary || '(no summary)')
  );

  if (intel.financial_flag) {
    intelSec.addWidget(
      CardService.newDecoratedText()
        .setTopLabel('💰 Financial')
        .setText(intel.financial_flag)
        .setWrapText(true)
    );
  }

  if (intel.sender_org) {
    intelSec.addWidget(
      CardService.newDecoratedText()
        .setTopLabel('From')
        .setText(intel.sender_org)
    );
  }

  card.addSection(intelSec);

  // ── Wing Action
  var actionSec = CardService.newCardSection().setHeader('Wing Recommendation');

  actionSec.addWidget(
    CardService.newDecoratedText()
      .setTopLabel(PERSONA_LABEL[intel.persona] || '⚡ Hale')
      .setText(intel.wing_action || 'No action required.')
      .setWrapText(true)
  );

  card.addSection(actionSec);

  // ── Client context (if recognized)
  if (intel.client_name) {
    var clientSec = CardService.newCardSection().setHeader('👤 ' + intel.client_name);
    clientSec.addWidget(
      CardService.newTextParagraph()
        .setText('Recognized D2M client. Check dossier for active bookings and open TPs.')
    );
    card.addSection(clientSec);
  }

  return card.build();
}

function buildFallbackCard(emailData, scan) {
  var flags = [];
  if (scan.isClient)     flags.push('🟡 D2M client detected');
  if (scan.isCruiseLine) flags.push('🚢 Cruise line');
  if (scan.hasFinancial) flags.push('💰 Financial mention');
  if (scan.isUrgent)     flags.push('🔴 Urgency keywords');
  if (flags.length === 0) flags.push('⚪ No Wing flags');

  return CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader()
      .setTitle('⚡ Thunderbird HUD')
      .setSubtitle('⚠️ Offline — local scan only'))
    .addSection(CardService.newCardSection()
      .setHeader('Quick Scan')
      .addWidget(CardService.newTextParagraph().setText(flags.join('\n')))
      .addWidget(CardService.newDecoratedText()
        .setTopLabel('From').setText(emailData.from))
    )
    .addSection(CardService.newCardSection()
      .setHeader('Setup')
      .addWidget(CardService.newTextParagraph()
        .setText('API key not configured. Run initHud() from Apps Script editor once to activate Wing Intel.'))
    )
    .build();
}

function buildSpamCard(emailData) {
  return CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader()
      .setTitle('⚡ Thunderbird HUD')
      .setSubtitle('🗑️ SPAM · ROUTINE'))
    .addSection(CardService.newCardSection()
      .addWidget(CardService.newTextParagraph()
        .setText('Marketing/spam detected. No Wing action required.')))
    .build();
}

function buildErrorCard(msg) {
  return CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader()
      .setTitle('⚡ HUD').setSubtitle('Error'))
    .addSection(CardService.newCardSection()
      .addWidget(CardService.newTextParagraph().setText(msg)))
    .build();
}

function buildStatusCard() {
  var key    = PropertiesService.getUserProperties().getProperty('CLAUDE_API_KEY');
  var status = key ? '✅ Active — Claude Haiku connected' : '⚠️ API key not set — run initHud() once';

  return CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader()
      .setTitle('⚡ Thunderbird HUD')
      .setSubtitle('Dreams2Memories Travel · Wing v1.0'))
    .addSection(CardService.newCardSection()
      .setHeader('Status')
      .addWidget(CardService.newDecoratedText().setTopLabel('Wing Intel').setText(status))
      .addWidget(CardService.newDecoratedText().setTopLabel('Coverage').setText('All incoming email — unconditional'))
      .addWidget(CardService.newDecoratedText().setTopLabel('Model').setText('Claude Haiku (fast triage)'))
    )
    .build();
}

// ─── one-time setup (run from Apps Script editor) ────────────────────────────

/**
 * initHud — stores Claude API key securely in PropertiesService.
 * Run ONCE from the Apps Script editor: select initHud → Run.
 * Key never appears in code or git. Encrypted per-user.
 *
 * The setup script (setup_hud_apikey.py) runs this automatically.
 */
function initHud(apiKey) {
  if (!apiKey || apiKey.indexOf('sk-ant') !== 0) {
    Logger.log('ERROR: Pass a valid Anthropic API key beginning with sk-ant');
    return;
  }
  PropertiesService.getUserProperties().setProperty('CLAUDE_API_KEY', apiKey);
  Logger.log('✅ Thunderbird HUD active. Wing Intel enabled.');
  Logger.log('Open Gmail on phone — HUD card appears on next email open.');
}

/** checkSetup — verify API key status */
function checkSetup() {
  var key = PropertiesService.getUserProperties().getProperty('CLAUDE_API_KEY');
  if (key) {
    Logger.log('✅ API key: SET (' + key.substring(0, 12) + '...)');
  } else {
    Logger.log('❌ API key: NOT SET. Run: initHud("sk-ant-...")');
  }
}
