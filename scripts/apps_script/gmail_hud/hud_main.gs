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
    if (scan.isSpam && !scan.isClient) return buildSpamCard();

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
      'You are the Thunderbird Wing HUD AI for Dreams2Memories Travel LLC.\n' +
      'Commander John "Yoda" Loucks is asking a question about this email on his phone.\n' +
      'Answer directly and briefly. Wing posture: bottom-line-first, no fluff.\n\n' +
      'Known D2M clients: ' + D2M_CLIENTS.join(', ') + '\n' +
      'Known cruise partners: ' + CRUISE_LINES.join(', ') + '\n\n' +
      'Email context:\n' +
      'From: ' + emailData.from + '\n' +
      'Subject: ' + emailData.subject + '\n' +
      'Body:\n' + emailData.body + '\n\n' +
      'Commander query: ' + query + '\n\n' +
      'Return ONLY valid JSON:\n' +
      '{"answer": "direct answer in 3-5 sentences", "action": "one sentence — what Commander should do next", "persona": "HALE|DANI|DEMBE|STERLING|HARLAN|NONE"}';
  } else {
    // Intel mode — full email classification and summary
    var scanFlags = scan ?
      'client=' + scan.isClient + ' cruise=' + scan.isCruiseLine +
      ' financial=' + scan.hasFinancial + ' urgent=' + scan.isUrgent : '';

    prompt =
      'You are the Thunderbird Wing HUD for Dreams2Memories Travel LLC — AI luxury travel agency.\n' +
      'Commander John "Yoda" Loucks reads this on his phone. Wing posture: bottom-line-first.\n\n' +
      'Known D2M clients: ' + D2M_CLIENTS.join(', ') + '\n' +
      'Known cruise partners: ' + CRUISE_LINES.join(', ') + '\n' +
      'Local flags: ' + scanFlags + '\n\n' +
      'From: ' + emailData.from + '\n' +
      'Subject: ' + emailData.subject + '\n' +
      'Body:\n' + emailData.body + '\n\n' +
      'Return ONLY valid JSON:\n' +
      '{"category":"CLIENT_REPLY|SUPPLIER|BOOKING_CONFIRM|FINANCIAL|BOOKING_CHANGE|INTEL|INTERNAL|PERSONAL|VENDOR|MARKETING|SPAM",' +
      '"priority":"P0|P1|P2|ROUTINE",' +
      '"summary":"4-5 sentence Wing Intel brief. Cover: what this email is about, who sent it, what they want or are reporting, any deadlines or dollar amounts, and the overall significance to D2M operations. Be specific — include names, amounts, dates if present.",' +
      '"client_name":"full D2M client name if identifiable, else null",' +
      '"wing_action":"specific one-sentence action for Commander right now",' +
      '"financial_flag":"exact dollar amount and/or date if mentioned, else null",' +
      '"persona":"HALE|DANI|DEMBE|STERLING|HARLAN|NONE",' +
      '"sender_org":"sender company or null",' +
      '"key_dates":"comma-separated list of any dates/deadlines mentioned, else null"}';
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
  var prio = intel.priority || 'ROUTINE';
  var cat  = intel.category || 'EMAIL';

  var card = CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader()
      .setTitle('⚡ Thunderbird HUD')
      .setSubtitle((PRIO_EMOJI[prio]||'⚪') + ' ' + prio + '  ' + (CAT_EMOJI[cat]||'📧') + ' ' + cat));

  // ── Wing Intel (longer summary)
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
  if (intel.sender_org) {
    intelSec.addWidget(CardService.newDecoratedText()
      .setTopLabel('From').setText(intel.sender_org));
  }
  card.addSection(intelSec);

  // ── Wing Recommendation
  var actionSec = CardService.newCardSection().setHeader('Wing Recommendation');
  actionSec.addWidget(CardService.newDecoratedText()
    .setTopLabel(PERSONA[intel.persona] || '⚡ Hale')
    .setText(intel.wing_action || 'No action required.')
    .setWrapText(true));
  card.addSection(actionSec);

  // ── Client context
  if (intel.client_name) {
    card.addSection(CardService.newCardSection()
      .setHeader('👤 ' + intel.client_name)
      .addWidget(CardService.newTextParagraph()
        .setText('Recognized D2M client — check dossier for active TPs.')));
  }

  // ── Wing Query
  var querySec = CardService.newCardSection().setHeader('Ask the Wing');
  querySec.addWidget(CardService.newTextInput()
    .setFieldName('wing_query')
    .setTitle('Question about this email...')
    .setHint('e.g. "Should I reply?" · "What is the FPD?" · "Draft a short response"'));
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
      .setSubtitle(PERSONA[result.persona] || '⚡ Hale'));

  // Query echo
  card.addSection(CardService.newCardSection()
    .setHeader('Your Question')
    .addWidget(CardService.newTextParagraph().setText(query)));

  // Answer
  card.addSection(CardService.newCardSection()
    .setHeader('Wing Answer')
    .addWidget(CardService.newTextParagraph().setText(result.answer || '(no answer)')));

  // Next action
  if (result.action) {
    card.addSection(CardService.newCardSection()
      .setHeader('Next Step')
      .addWidget(CardService.newTextParagraph().setText(result.action)));
  }

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
