/**
 * Thunderbird Gmail HUD — hud_main.gs
 * v1.2 — longer summary + Wing query interface
 *
 * Gmail Add-on. Fires on EVERY email open (desktop + mobile).
 * Calls Claude Haiku → Wing Intel card + interactive query box.
 *
 * Wing: Dreams2Memories Travel, LLC
 * Commander: John "Yoda" Loucks
 * COS: Victoria "Victory" Hale, SES-6
 */

var D2M_CLIENTS = [
  'Kuklinski', 'McLeod', 'McGlasson', 'Furlow', 'Ely', 'Darrow',
  'Nichols', 'Westbrook', 'Spencer', 'Bryana', 'Loucks', 'Morton',
  'Dodge', 'How', 'Quick', 'Trien', 'Heer', 'Scandi'
];

var CRUISE_LINES = [
  'Silversea', 'Regent', 'Viking', 'Princess', 'Celebrity',
  'Holland America', 'Seabourn', 'Oceania', 'Crystal', 'Cunard',
  'Azamara', 'MSC', 'Norwegian', 'Royal Caribbean', 'Silver',
  'Seven Seas', 'Windstar', 'Ponant'
];

var CLAUDE_API_URL = 'https://api.anthropic.com/v1/messages';
var CLAUDE_MODEL   = 'claude-haiku-4-5-20251001';

// Cache email context across card → query callback
var _emailCache = {};

// ─── main trigger ─────────────────────────────────────────────────────────────

function onGmailMessage(e) {
  try {
    var messageId   = e.gmail.messageId;
    var accessToken = e.gmail.accessToken;
    GmailApp.setCurrentMessageAccessToken(accessToken);

    var message = GmailApp.getMessageById(messageId);
    if (!message) return buildErrorCard('Message not found.');

    var emailData = {
      id:      messageId,
      subject: message.getSubject()   || '(no subject)',
      from:    message.getFrom()      || '',
      date:    message.getDate() ? message.getDate().toISOString() : '',
      body:    (message.getPlainBody() || '').substring(0, 4000)
    };

    var scan  = localPreScan(emailData);

    var intel = callClaude(emailData, scan, null);
    if (!intel) return buildFallbackCard(emailData, scan);

    return buildHudCard(intel, emailData, null);

  } catch (err) {
    return buildErrorCard('HUD: ' + err.message);
  }
}

function onHomepage() {
  var hasKey = (typeof CLAUDE_API_KEY !== 'undefined' && !!CLAUDE_API_KEY);
  return CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader()
      .setTitle('⚡ Thunderbird HUD').setSubtitle('D2M · v1.2'))
    .addSection(CardService.newCardSection()
      .setHeader('Status')
      .addWidget(CardService.newDecoratedText()
        .setTopLabel('Wing Intel')
        .setText(hasKey ? '✅ Active — Claude Haiku' : '⚠️ Config missing'))
      .addWidget(CardService.newDecoratedText()
        .setTopLabel('Coverage').setText('All email — unconditional'))
      .addWidget(CardService.newDecoratedText()
        .setTopLabel('Query').setText('✅ Interactive Wing query'))
    ).build();
}

// ─── query callback ───────────────────────────────────────────────────────────

/**
 * onQuerySubmit — fires when Commander taps "Ask Wing" button.
 * e.formInput.wing_query holds the typed question.
 * e.gmail.messageId / accessToken still present in callback context.
 */
function onQuerySubmit(e) {
  try {
    var query     = (e.formInput && e.formInput.wing_query) ? e.formInput.wing_query.trim() : '';
    var messageId = e.gmail ? e.gmail.messageId : null;

    if (!query) return buildErrorCard('No query received.');

    // Re-fetch email for context
    var emailData = { subject: '', from: '', body: '', id: messageId };
    if (messageId && e.gmail && e.gmail.accessToken) {
      GmailApp.setCurrentMessageAccessToken(e.gmail.accessToken);
      var msg = GmailApp.getMessageById(messageId);
      if (msg) {
        emailData.subject = msg.getSubject() || '';
        emailData.from    = msg.getFrom()    || '';
        emailData.body    = (msg.getPlainBody() || '').substring(0, 4000);
      }
    }

    var answer = callClaude(emailData, null, query);
    if (!answer) return buildErrorCard('Wing query failed — check API config.');

    return buildQueryResultCard(query, answer);

  } catch (err) {
    return buildErrorCard('Query error: ' + err.message);
  }
}

// ─── local pre-scan ───────────────────────────────────────────────────────────

function localPreScan(email) {
  var text   = (email.subject + ' ' + email.from + ' ' + email.body).toLowerCase();
  var fromLc = email.from.toLowerCase();
  return {
    isClient:     D2M_CLIENTS.some(function(c) { return text.indexOf(c.toLowerCase()) !== -1; }),
    isCruiseLine: CRUISE_LINES.some(function(c) { return fromLc.indexOf(c.toLowerCase()) !== -1; }),
    hasFinancial: /\$[\d,]+|\bpayment\b|\binvoice\b|\bbalance due\b|\bfpd\b|\bdeposit\b/i.test(text),
    isUrgent:     /urgent|immediately|today only|overdue|past due|expires today|deadline/i.test(text),
    isSpam:       /unsubscribe|click here to|special offer|you.ve been selected|winner|prize/i.test(text)
  };
}

// ─── Claude call (dual mode: intel + query) ───────────────────────────────────

function callClaude(emailData, scan, query) {
  if (typeof CLAUDE_API_KEY === 'undefined' || !CLAUDE_API_KEY) return null;

  var prompt;

  if (query) {
    // Query mode — answer Commander's specific question about the email
    prompt =
      'You are the Thunderbird Wing HUD. Commander John "Yoda" Loucks is asking a question about this email.\n' +
      'Read the email. Answer the question factually based on what the email says.\n' +
      'No opinion. No recommendation. No judgment about whether the email is relevant to D2M.\n\n' +
      'From: ' + emailData.from + '\n' +
      'Subject: ' + emailData.subject + '\n' +
      'Body:\n' + emailData.body + '\n\n' +
      'Commander query: ' + query + '\n\n' +
      'Return ONLY valid JSON:\n' +
      '{"answer": "factual answer based on what the email says. Length as warranted by the question."}';
  } else {
    // Intel mode — read and report. No classification. No recommendation.
    prompt =
      'You are the Thunderbird Wing HUD. Your job is to read this email and report what it says.\n' +
      'Commander John "Yoda" Loucks is reading this. If he is reading it, it is significant to him.\n' +
      'Do NOT editorialize. Do NOT classify. Do NOT recommend action. Do NOT judge D2M relevance.\n' +
      'Pure reportage only.\n\n' +
      'Format: use MFR (Memorandum for Record) format for short or simple emails.\n' +
      'Use Staff Paper format for long or substantive emails with multiple points.\n' +
      'Include the level of detail the content warrants — if there are claims, background, or multiple threads, cover them fully.\n\n' +
      'From: ' + emailData.from + '\n' +
      'Subject: ' + emailData.subject + '\n' +
      'Body:\n' + emailData.body + '\n\n' +
      'Return ONLY valid JSON:\n' +
      '{"summary": "MFR or Staff Paper — pure reportage of what this email says. Depth as the content warrants.",' +
      '"financial_flag": "exact dollar amount and date if mentioned, else null",' +
      '"key_dates": "comma-separated dates or deadlines if mentioned, else null",' +
      '"sender_org": "sender organization or null"}';
  }

  try {
    var resp = UrlFetchApp.fetch(CLAUDE_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': CLAUDE_API_KEY,
        'anthropic-version': '2023-06-01'
      },
      payload: JSON.stringify({
        model: CLAUDE_MODEL,
        max_tokens: query ? 512 : 700,
        messages: [{ role: 'user', content: prompt }]
      }),
      muteHttpExceptions: true
    });

    if (resp.getResponseCode() !== 200) {
      Logger.log('Claude HTTP ' + resp.getResponseCode() + ': ' + resp.getContentText().substring(0,200));
      return null;
    }

    var result = JSON.parse(resp.getContentText());
    var text   = result.content[0].text.trim();
    var match  = text.match(/\{[\s\S]*\}/);
    return match ? JSON.parse(match[0]) : null;

  } catch (err) {
    Logger.log('Claude error: ' + err.message);
    return null;
  }
}

// ─── card builders ────────────────────────────────────────────────────────────

var PRIO_EMOJI = { P0:'🔴', P1:'🟡', P2:'🟢', ROUTINE:'⚪' };
var CAT_EMOJI  = {
  CLIENT_REPLY:'👤', SUPPLIER:'🚢', BOOKING_CONFIRM:'📋',
  FINANCIAL:'💰', BOOKING_CHANGE:'✏️', INTEL:'🔍',
  INTERNAL:'⚡', PERSONAL:'👋', VENDOR:'🏢', MARKETING:'📣', SPAM:'🗑️'
};
var PERSONA = {
  HALE:'⚡ Hale', DANI:'✈️ Dani', DEMBE:'🔍 Dembe',
  STERLING:'📊 Sterling', HARLAN:'💰 Harlan', NONE:'Wing'
};

function buildHudCard(intel, emailData, prevQuery) {
  var card = CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader()
      .setTitle('⚡ Thunderbird HUD')
      .setSubtitle(intel.sender_org || emailData.from || 'Wing Intel'));

  // ── Report
  var intelSec = CardService.newCardSection().setHeader('Wing Intel');
  intelSec.addWidget(CardService.newTextParagraph()
    .setText(intel.summary || '(no summary)'));

  if (intel.financial_flag) {
    intelSec.addWidget(CardService.newDecoratedText()
      .setTopLabel('💰 Financial').setText(intel.financial_flag).setWrapText(true));
  }
  if (intel.key_dates) {
    intelSec.addWidget(CardService.newDecoratedText()
      .setTopLabel('📅 Key dates').setText(intel.key_dates).setWrapText(true));
  }
  card.addSection(intelSec);

  // ── Wing Query
  var querySec = CardService.newCardSection().setHeader('Ask the Wing');
  querySec.addWidget(CardService.newTextInput()
    .setFieldName('wing_query')
    .setTitle('Question about this email...')
    .setHint('e.g. "What did they ask for?" · "What is the FPD?" · "Who sent this?"'));
  querySec.addWidget(CardService.newButtonSet()
    .addButton(CardService.newTextButton()
      .setText('Ask Wing ⚡')
      .setOnClickAction(CardService.newAction()
        .setFunctionName('onQuerySubmit'))));
  card.addSection(querySec);

  return card.build();
}

function buildQueryResultCard(query, result) {
  var card = CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader()
      .setTitle('⚡ Wing Response')
      .setSubtitle('Wing Answer'));

  // Query echo
  card.addSection(CardService.newCardSection()
    .setHeader('Your Question')
    .addWidget(CardService.newTextParagraph().setText(query)));

  // Answer
  card.addSection(CardService.newCardSection()
    .setHeader('Answer')
    .addWidget(CardService.newTextParagraph().setText(result.answer || '(no answer)')));

  // Back button
  card.addSection(CardService.newCardSection()
    .addWidget(CardService.newButtonSet()
      .addButton(CardService.newTextButton()
        .setText('← Back to HUD')
        .setOnClickAction(CardService.newAction()
          .setFunctionName('onHomepage')))));

  return card.build();
}

function buildFallbackCard(emailData, scan) {
  var flags = [];
  if (scan && scan.isClient)     flags.push('🟡 D2M client detected');
  if (scan && scan.isCruiseLine) flags.push('🚢 Cruise line');
  if (scan && scan.hasFinancial) flags.push('💰 Financial mention');
  if (scan && scan.isUrgent)     flags.push('🔴 Urgency keywords');
  if (!flags.length)             flags.push('⚪ No Wing flags');

  return CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader()
      .setTitle('⚡ Thunderbird HUD').setSubtitle('⚠️ Offline — local scan'))
    .addSection(CardService.newCardSection()
      .setHeader('Quick Scan')
      .addWidget(CardService.newTextParagraph().setText(flags.join('\n')))
      .addWidget(CardService.newDecoratedText().setTopLabel('From').setText(emailData.from)))
    .build();
}

function buildSpamCard() {
  return CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader().setTitle('⚡ HUD').setSubtitle('🗑️ SPAM · ROUTINE'))
    .addSection(CardService.newCardSection()
      .addWidget(CardService.newTextParagraph().setText('Marketing/spam. No Wing action.')))
    .build();
}

function buildErrorCard(msg) {
  return CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader().setTitle('⚡ HUD').setSubtitle('Error'))
    .addSection(CardService.newCardSection()
      .addWidget(CardService.newTextParagraph().setText(msg)))
    .build();
}
