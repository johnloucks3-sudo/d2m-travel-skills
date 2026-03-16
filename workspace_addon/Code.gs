/**
 * THUNDERBIRD HUD v2 — Google Workspace Add-on
 * Dreams2Memories Travel, LLC
 *
 * EARA-style command center inside Gmail.
 * AI-powered via Groq Llama 3.3 (through Thunderbird API).
 *
 * Features:
 *   - AI email summarization (bullet points)
 *   - AI draft reply in John's voice
 *   - Free-form query window (like EARA Command Center)
 *   - Send to Evernote (yodainva@gmail.com)
 *   - Save to Google Drive
 *   - Intel sweeps (Ship, World, Tech)
 *   - Fare watch dashboard
 */

// ============================================================================
// CONFIG
// ============================================================================

function getConfig_() {
  var props = PropertiesService.getScriptProperties();
  return {
    apiUrl: props.getProperty('THUNDERBIRD_URL') || 'http://localhost:8766',
    apiKey: props.getProperty('THUNDERBIRD_API_KEY') || '',
  };
}

function apiCall_(endpoint, method, payload) {
  var config = getConfig_();
  var url = config.apiUrl + endpoint;

  var options = {
    method: method || 'GET',
    headers: {
      'X-API-Key': config.apiKey,
      'Content-Type': 'application/json',
    },
    muteHttpExceptions: true,
  };

  if (payload && method !== 'GET') {
    options.payload = JSON.stringify(payload);
  }

  try {
    var response = UrlFetchApp.fetch(url, options);
    var code = response.getResponseCode();
    if (code >= 200 && code < 300) {
      return JSON.parse(response.getContentText());
    } else {
      return { error: 'HTTP ' + code, detail: response.getContentText().substring(0, 500) };
    }
  } catch (e) {
    return { error: 'Connection failed', detail: e.toString().substring(0, 300) };
  }
}


// ============================================================================
// HOMEPAGE — MAIN HUD
// ============================================================================

function onHomepage(e) {
  var card = CardService.newCardBuilder();

  // Header
  card.setHeader(
    CardService.newCardHeader()
      .setTitle('THUNDERBIRD HUD')
      .setSubtitle('Dreams2Memories Command Center')
  );

  // --- Status ---
  var statusSection = CardService.newCardSection().setHeader('STATUS');
  var health = apiCall_('/api/health', 'GET');

  if (health.status === 'ok') {
    statusSection.addWidget(
      CardService.newDecoratedText()
        .setText('API Online | Groq AI Active')
        .setBottomLabel(health.timestamp ? health.timestamp.substring(0, 19) : '')
    );
  } else {
    statusSection.addWidget(
      CardService.newDecoratedText()
        .setText('API OFFLINE')
        .setBottomLabel(health.error || 'Cannot reach Thunderbird server')
    );
  }
  card.addSection(statusSection);

  // --- Command Center (Query Window) ---
  var querySection = CardService.newCardSection().setHeader('COMMAND CENTER');

  querySection.addWidget(
    CardService.newTextInput()
      .setFieldName('command_query')
      .setTitle('Enter command or question')
      .setHint('e.g. "What cruises depart in April?" or "Summarize Kuklinski booking"')
  );

  querySection.addWidget(
    CardService.newTextButton()
      .setText('Execute Command')
      .setOnClickAction(CardService.newAction().setFunctionName('executeCommand'))
  );

  card.addSection(querySection);

  // --- Quick Actions ---
  var actionsSection = CardService.newCardSection().setHeader('INTEL OPERATIONS');

  actionsSection.addWidget(
    CardService.newButtonSet()
      .addButton(CardService.newTextButton()
        .setText('Morning Brief')
        .setOnClickAction(CardService.newAction().setFunctionName('showBriefing')))
      .addButton(CardService.newTextButton()
        .setText('Fare Watches')
        .setOnClickAction(CardService.newAction().setFunctionName('showFareWatches')))
  );

  actionsSection.addWidget(
    CardService.newButtonSet()
      .addButton(CardService.newTextButton()
        .setText('Ship Intel')
        .setOnClickAction(CardService.newAction().setFunctionName('runShipIntel')))
      .addButton(CardService.newTextButton()
        .setText('World Intel')
        .setOnClickAction(CardService.newAction().setFunctionName('runWorldIntel')))
  );

  actionsSection.addWidget(
    CardService.newTextButton()
      .setText('Tech Monitor')
      .setOnClickAction(CardService.newAction().setFunctionName('runTechMonitor'))
  );

  card.addSection(actionsSection);

  // --- Tools List (collapsible) ---
  var toolsSection = CardService.newCardSection()
    .setHeader('REGISTERED TOOLS')
    .setCollapsible(true)
    .setNumUncollapsibleWidgets(0);

  var tools = apiCall_('/api/tools', 'GET');
  if (tools.tools) {
    toolsSection.addWidget(
      CardService.newDecoratedText()
        .setText(tools.count + ' tools online')
        .setBottomLabel(tools.tools.join(', '))
        .setWrapText(true)
    );
  }
  card.addSection(toolsSection);

  return card.build();
}


// ============================================================================
// GMAIL CONTEXTUAL CARD — appears when viewing an email
// ============================================================================

function onGmailMessage(e) {
  var messageId = e.gmail.messageId;
  var accessToken = e.gmail.accessToken;

  GmailApp.setCurrentMessageAccessToken(accessToken);
  var message = GmailApp.getMessageById(messageId);
  var thread = message.getThread();

  var card = CardService.newCardBuilder();
  card.setHeader(
    CardService.newCardHeader()
      .setTitle('THUNDERBIRD')
      .setSubtitle('Email Intelligence')
  );

  // --- Email Info ---
  var infoSection = CardService.newCardSection().setHeader('TARGET');

  infoSection.addWidget(
    CardService.newDecoratedText()
      .setTopLabel('From')
      .setText(message.getFrom() || 'Unknown')
      .setWrapText(true)
  );

  infoSection.addWidget(
    CardService.newDecoratedText()
      .setTopLabel('Subject')
      .setText(message.getSubject() || '(no subject)')
      .setWrapText(true)
  );

  infoSection.addWidget(
    CardService.newDecoratedText()
      .setTopLabel('Thread Depth')
      .setText(thread.getMessageCount() + ' messages | ' + message.getDate().toLocaleDateString())
  );

  card.addSection(infoSection);

  // --- AI Actions ---
  var aiSection = CardService.newCardSection().setHeader('AI ACTIONS');

  aiSection.addWidget(
    CardService.newTextButton()
      .setText('AI Summarize Thread')
      .setOnClickAction(
        CardService.newAction()
          .setFunctionName('aiSummarizeThread')
          .setParameters({ threadId: thread.getId(), messageId: messageId })
      )
  );

  aiSection.addWidget(
    CardService.newTextButton()
      .setText('AI Draft Reply (D2M Voice)')
      .setOnClickAction(
        CardService.newAction()
          .setFunctionName('aiDraftReply')
          .setParameters({ messageId: messageId })
      )
  );

  card.addSection(aiSection);

  // --- Command Window (contextual) ---
  var querySection = CardService.newCardSection().setHeader('COMMAND');

  querySection.addWidget(
    CardService.newTextInput()
      .setFieldName('email_command')
      .setTitle('Ask about this email')
      .setHint('e.g. "What action items?" or "Draft a polite decline"')
  );

  querySection.addWidget(
    CardService.newTextButton()
      .setText('Execute')
      .setOnClickAction(
        CardService.newAction()
          .setFunctionName('executeEmailCommand')
          .setParameters({ messageId: messageId })
      )
  );

  card.addSection(querySection);

  // --- Export Actions ---
  var exportSection = CardService.newCardSection().setHeader('EXPORT');

  exportSection.addWidget(
    CardService.newButtonSet()
      .addButton(CardService.newTextButton()
        .setText('Save to Evernote')
        .setOnClickAction(
          CardService.newAction()
            .setFunctionName('sendToEvernote')
            .setParameters({
              messageId: messageId,
              subject: message.getSubject() || 'Gmail Note',
              from: message.getFrom() || ''
            })
        ))
      .addButton(CardService.newTextButton()
        .setText('Save to Drive')
        .setOnClickAction(
          CardService.newAction()
            .setFunctionName('saveToDrive')
            .setParameters({
              messageId: messageId,
              subject: message.getSubject() || 'Gmail Note',
              from: message.getFrom() || ''
            })
        ))
  );

  exportSection.addWidget(
    CardService.newTextButton()
      .setText('Search Similar Emails')
      .setOnClickAction(
        CardService.newAction()
          .setFunctionName('searchSimilar')
          .setParameters({ from: message.getFrom(), subject: message.getSubject() })
      )
  );

  card.addSection(exportSection);

  return card.build();
}


// ============================================================================
// AI HANDLERS
// ============================================================================

function aiSummarizeThread(e) {
  var threadId = e.parameters.threadId;
  var result = apiCall_('/api/ai/summarize', 'POST', { thread_id: threadId });

  var card = CardService.newCardBuilder();
  card.setHeader(
    CardService.newCardHeader()
      .setTitle('AI SUMMARY')
      .setSubtitle(result.subject || '')
  );

  var section = CardService.newCardSection();

  if (result.status === 'success' && result.ai_summary) {
    section.addWidget(
      CardService.newDecoratedText()
        .setTopLabel('Messages Analyzed')
        .setText(String(result.message_count))
    );

    // Display AI summary with formatting
    var summary = result.ai_summary;
    section.addWidget(
      CardService.newTextParagraph().setText(summary)
    );
  } else {
    section.addWidget(
      CardService.newTextParagraph()
        .setText('Error: ' + (result.error || result.detail || 'AI unavailable'))
    );
  }

  card.addSection(section);

  // Export buttons
  var exportSection = CardService.newCardSection();
  exportSection.addWidget(
    CardService.newButtonSet()
      .addButton(CardService.newTextButton()
        .setText('To Evernote')
        .setOnClickAction(
          CardService.newAction()
            .setFunctionName('sendTextToEvernote')
            .setParameters({
              subject: 'AI Summary: ' + (result.subject || 'Thread'),
              body: result.ai_summary || 'No summary'
            })
        ))
      .addButton(CardService.newTextButton()
        .setText('To Drive')
        .setOnClickAction(
          CardService.newAction()
            .setFunctionName('sendTextToDrive')
            .setParameters({
              subject: 'AI Summary: ' + (result.subject || 'Thread'),
              body: result.ai_summary || 'No summary'
            })
        ))
  );

  exportSection.addWidget(
    CardService.newTextButton()
      .setText('Back to HUD')
      .setOnClickAction(CardService.newAction().setFunctionName('onHomepage'))
  );

  card.addSection(exportSection);
  return CardService.newNavigation().pushCard(card.build());
}


function aiDraftReply(e) {
  var messageId = e.parameters.messageId;
  var instructions = e.formInput ? (e.formInput.email_command || '') : '';
  var result = apiCall_('/api/ai/draft-reply', 'POST', {
    message_id: messageId,
    instructions: instructions || 'Reply professionally and helpfully in John\'s voice.'
  });

  var card = CardService.newCardBuilder();
  card.setHeader(
    CardService.newCardHeader()
      .setTitle('AI DRAFT REPLY')
      .setSubtitle('D2M Voice')
  );

  var section = CardService.newCardSection();

  if (result.status === 'success' && result.draft) {
    section.addWidget(
      CardService.newDecoratedText()
        .setTopLabel('To')
        .setText(result.reply_to || '')
        .setWrapText(true)
    );

    section.addWidget(
      CardService.newDecoratedText()
        .setTopLabel('Subject')
        .setText(result.subject || '')
        .setWrapText(true)
    );

    // Draft text
    section.addWidget(
      CardService.newTextParagraph().setText(result.draft)
    );

    // Create actual Gmail draft button
    section.addWidget(
      CardService.newTextButton()
        .setText('Create Gmail Draft')
        .setOnClickAction(
          CardService.newAction()
            .setFunctionName('createActualDraft')
            .setParameters({
              to: result.reply_to || '',
              subject: result.subject || '',
              body: result.draft || '',
              threadId: result.thread_id || ''
            })
        )
    );
  } else {
    section.addWidget(
      CardService.newTextParagraph()
        .setText('Error: ' + (result.error || result.detail || 'AI unavailable'))
    );
  }

  card.addSection(section);

  card.addSection(
    CardService.newCardSection().addWidget(
      CardService.newTextButton()
        .setText('Back')
        .setOnClickAction(CardService.newAction().setFunctionName('onHomepage'))
    )
  );

  return CardService.newNavigation().pushCard(card.build());
}


function createActualDraft(e) {
  var to = e.parameters.to;
  var subject = e.parameters.subject;
  var body = e.parameters.body;

  try {
    GmailApp.createDraft(to, subject, body);
    return CardService.newActionResponseBuilder()
      .setNotification(CardService.newNotification().setText('Draft created in Gmail!'))
      .build();
  } catch (err) {
    return CardService.newActionResponseBuilder()
      .setNotification(CardService.newNotification().setText('Error: ' + err.toString()))
      .build();
  }
}


// ============================================================================
// COMMAND CENTER
// ============================================================================

function executeCommand(e) {
  var query = e.formInput ? e.formInput.command_query : '';
  if (!query) {
    return CardService.newActionResponseBuilder()
      .setNotification(CardService.newNotification().setText('Enter a command first.'))
      .build();
  }

  var result = apiCall_('/api/ai/query', 'POST', { query: query });

  var card = CardService.newCardBuilder();
  card.setHeader(
    CardService.newCardHeader()
      .setTitle('EARA RESPONSE')
      .setSubtitle(query.substring(0, 40))
  );

  var section = CardService.newCardSection();

  if (result.status === 'success' && result.answer) {
    section.addWidget(
      CardService.newTextParagraph().setText(result.answer)
    );
  } else {
    section.addWidget(
      CardService.newTextParagraph()
        .setText('Error: ' + (result.error || result.detail || 'Unknown'))
    );
  }

  card.addSection(section);

  // Export + back
  var actionSection = CardService.newCardSection();
  actionSection.addWidget(
    CardService.newButtonSet()
      .addButton(CardService.newTextButton()
        .setText('To Evernote')
        .setOnClickAction(
          CardService.newAction()
            .setFunctionName('sendTextToEvernote')
            .setParameters({
              subject: 'EARA: ' + query.substring(0, 50),
              body: result.answer || ''
            })
        ))
      .addButton(CardService.newTextButton()
        .setText('To Drive')
        .setOnClickAction(
          CardService.newAction()
            .setFunctionName('sendTextToDrive')
            .setParameters({
              subject: 'EARA: ' + query.substring(0, 50),
              body: result.answer || ''
            })
        ))
  );

  // New query input
  actionSection.addWidget(
    CardService.newTextInput()
      .setFieldName('command_query')
      .setTitle('Follow-up command')
  );

  actionSection.addWidget(
    CardService.newButtonSet()
      .addButton(CardService.newTextButton()
        .setText('Execute')
        .setOnClickAction(CardService.newAction().setFunctionName('executeCommand')))
      .addButton(CardService.newTextButton()
        .setText('Back to HUD')
        .setOnClickAction(CardService.newAction().setFunctionName('onHomepage')))
  );

  card.addSection(actionSection);
  return CardService.newNavigation().pushCard(card.build());
}


function executeEmailCommand(e) {
  var query = e.formInput ? e.formInput.email_command : '';
  var messageId = e.parameters.messageId;

  if (!query) {
    return CardService.newActionResponseBuilder()
      .setNotification(CardService.newNotification().setText('Enter a command first.'))
      .build();
  }

  // Get email content for context
  var accessToken = e.gmail ? e.gmail.accessToken : null;
  var context = '';
  try {
    if (accessToken) {
      GmailApp.setCurrentMessageAccessToken(accessToken);
    }
    var message = GmailApp.getMessageById(messageId);
    context = 'FROM: ' + message.getFrom() + '\n' +
              'SUBJECT: ' + message.getSubject() + '\n' +
              'BODY:\n' + message.getPlainBody().substring(0, 3000);
  } catch (err) {
    context = 'Could not retrieve email content: ' + err.toString();
  }

  var result = apiCall_('/api/ai/query', 'POST', { query: query, context: context });

  var card = CardService.newCardBuilder();
  card.setHeader(
    CardService.newCardHeader()
      .setTitle('EARA RESPONSE')
      .setSubtitle(query.substring(0, 40))
  );

  var section = CardService.newCardSection();

  if (result.status === 'success' && result.answer) {
    section.addWidget(
      CardService.newTextParagraph().setText(result.answer)
    );
  } else {
    section.addWidget(
      CardService.newTextParagraph()
        .setText('Error: ' + (result.error || result.detail || 'Unknown'))
    );
  }

  card.addSection(section);

  var actionSection = CardService.newCardSection();
  actionSection.addWidget(
    CardService.newButtonSet()
      .addButton(CardService.newTextButton()
        .setText('To Evernote')
        .setOnClickAction(
          CardService.newAction()
            .setFunctionName('sendTextToEvernote')
            .setParameters({
              subject: 'EARA: ' + query.substring(0, 50),
              body: result.answer || ''
            })
        ))
      .addButton(CardService.newTextButton()
        .setText('To Drive')
        .setOnClickAction(
          CardService.newAction()
            .setFunctionName('sendTextToDrive')
            .setParameters({
              subject: 'EARA: ' + query.substring(0, 50),
              body: result.answer || ''
            })
        ))
  );

  actionSection.addWidget(
    CardService.newTextButton()
      .setText('Back')
      .setOnClickAction(CardService.newAction().setFunctionName('onHomepage'))
  );

  card.addSection(actionSection);
  return CardService.newNavigation().pushCard(card.build());
}


// ============================================================================
// EXPORT: EVERNOTE & DRIVE
// ============================================================================

function sendToEvernote(e) {
  var messageId = e.parameters.messageId;
  var subject = e.parameters.subject || 'Gmail Note';
  var from = e.parameters.from || '';

  try {
    var message = GmailApp.getMessageById(messageId);
    var body = 'FROM: ' + from + '\n' +
               'SUBJECT: ' + subject + '\n' +
               'DATE: ' + message.getDate().toLocaleString() + '\n\n' +
               message.getPlainBody();

    var result = apiCall_('/api/send-to-evernote', 'POST', {
      subject: subject,
      body: body
    });

    var msg = result.status === 'sent'
      ? 'Sent to Evernote (yodainva@gmail.com)'
      : 'Error: ' + (result.error || 'Unknown');

    return CardService.newActionResponseBuilder()
      .setNotification(CardService.newNotification().setText(msg))
      .build();
  } catch (err) {
    return CardService.newActionResponseBuilder()
      .setNotification(CardService.newNotification().setText('Error: ' + err.toString()))
      .build();
  }
}


function sendTextToEvernote(e) {
  var subject = e.parameters.subject || 'Thunderbird Note';
  var body = e.parameters.body || '';

  var result = apiCall_('/api/send-to-evernote', 'POST', {
    subject: subject,
    body: body
  });

  var msg = result.status === 'sent'
    ? 'Sent to Evernote'
    : 'Error: ' + (result.error || 'Unknown');

  return CardService.newActionResponseBuilder()
    .setNotification(CardService.newNotification().setText(msg))
    .build();
}


function saveToDrive(e) {
  var messageId = e.parameters.messageId;
  var subject = e.parameters.subject || 'Gmail Note';
  var from = e.parameters.from || '';

  try {
    var message = GmailApp.getMessageById(messageId);
    var body = 'FROM: ' + from + '\n' +
               'SUBJECT: ' + subject + '\n' +
               'DATE: ' + message.getDate().toLocaleString() + '\n\n' +
               message.getPlainBody();

    var filename = subject.replace(/[^a-zA-Z0-9 ]/g, '').substring(0, 50) + '.txt';
    var result = apiCall_('/api/save-to-drive', 'POST', {
      filename: filename,
      content: body
    });

    var msg = result.status === 'saved'
      ? 'Saved to Drive: ' + result.filename
      : 'Error: ' + (result.error || 'Unknown');

    return CardService.newActionResponseBuilder()
      .setNotification(CardService.newNotification().setText(msg))
      .build();
  } catch (err) {
    return CardService.newActionResponseBuilder()
      .setNotification(CardService.newNotification().setText('Error: ' + err.toString()))
      .build();
  }
}


function sendTextToDrive(e) {
  var subject = e.parameters.subject || 'Thunderbird Note';
  var body = e.parameters.body || '';

  var filename = subject.replace(/[^a-zA-Z0-9 ]/g, '').substring(0, 50) + '.txt';
  var result = apiCall_('/api/save-to-drive', 'POST', {
    filename: filename,
    content: body
  });

  var msg = result.status === 'saved'
    ? 'Saved to Drive: ' + result.filename
    : 'Error: ' + (result.error || 'Unknown');

  return CardService.newActionResponseBuilder()
    .setNotification(CardService.newNotification().setText(msg))
    .build();
}


// ============================================================================
// INTEL & FARE HANDLERS
// ============================================================================

function showBriefing(e) {
  var result = apiCall_('/api/briefing', 'GET');

  var card = CardService.newCardBuilder();
  card.setHeader(CardService.newCardHeader().setTitle('MORNING BRIEFING'));

  var section = CardService.newCardSection();

  if (result.status === 'success' && result.data) {
    section.addWidget(
      CardService.newDecoratedText()
        .setTopLabel('Source')
        .setText(result.file || 'cached')
    );

    var data = result.data;
    var display = typeof data.summary === 'string' ? data.summary
                  : JSON.stringify(data, null, 2).substring(0, 3000);
    section.addWidget(CardService.newTextParagraph().setText(display));
  } else {
    section.addWidget(
      CardService.newTextParagraph()
        .setText(result.message || 'No briefing data. Scheduler generates at 6:30 AM MT.')
    );
  }

  card.addSection(section);
  card.addSection(backButtonSection_());
  return CardService.newNavigation().pushCard(card.build());
}


function showFareWatches(e) {
  var result = apiCall_('/api/fare-watches', 'GET');

  var card = CardService.newCardBuilder();
  card.setHeader(
    CardService.newCardHeader()
      .setTitle('FARE WATCHES')
      .setSubtitle(result.count ? result.count + ' active' : '0 active')
  );

  var section = CardService.newCardSection();

  if (result.watches && result.watches.length > 0) {
    for (var i = 0; i < result.watches.length; i++) {
      var w = result.watches[i];
      section.addWidget(
        CardService.newDecoratedText()
          .setTopLabel(w.provider + ' | ' + w.type)
          .setText(w.label)
          .setBottomLabel(w.price_pp + '/pp | Total: ' + w.total + ' | ' + w.vs_baseline + ' vs baseline')
          .setWrapText(true)
      );
    }
  } else {
    section.addWidget(
      CardService.newTextParagraph()
        .setText('No active fare watches. Use Claude to add one with fare_watch_add.')
    );
  }

  card.addSection(section);
  card.addSection(backButtonSection_());
  return CardService.newNavigation().pushCard(card.build());
}


function searchSimilar(e) {
  var from = e.parameters.from || '';
  var query = 'from:' + from.replace(/.*</, '').replace(/>.*/, '');
  var result = apiCall_('/api/search-email', 'POST', { query: query, max_results: 5 });

  var card = CardService.newCardBuilder();
  card.setHeader(CardService.newCardHeader().setTitle('RELATED EMAILS').setSubtitle(query));

  var section = CardService.newCardSection();

  if (result.messages && result.messages.length > 0) {
    for (var i = 0; i < result.messages.length; i++) {
      var m = result.messages[i];
      section.addWidget(
        CardService.newDecoratedText()
          .setTopLabel(m.Date || '')
          .setText(m.Subject || '(no subject)')
          .setBottomLabel(m.snippet ? m.snippet.substring(0, 120) : '')
          .setWrapText(true)
      );
    }
  } else {
    section.addWidget(CardService.newTextParagraph().setText('No related emails found.'));
  }

  card.addSection(section);
  card.addSection(backButtonSection_());
  return CardService.newNavigation().pushCard(card.build());
}


function runShipIntel(e) { return runToolCard_('run_ship_intelligence_sweep', 'SHIP INTEL'); }
function runWorldIntel(e) { return runToolCard_('run_world_intelligence_sweep', 'WORLD INTEL'); }
function runTechMonitor(e) { return runToolCard_('run_daily_tech_monitor', 'TECH MONITOR'); }

function runToolCard_(toolName, title) {
  var card = CardService.newCardBuilder();
  card.setHeader(CardService.newCardHeader().setTitle(title).setSubtitle('Executing...'));

  var section = CardService.newCardSection();
  var result = apiCall_('/api/tool/' + toolName, 'POST', {});

  if (result.status === 'success') {
    var dataStr = JSON.stringify(result.data, null, 2);
    if (dataStr.length > 4000) {
      dataStr = dataStr.substring(0, 4000) + '\n\n... [truncated]';
    }
    section.addWidget(CardService.newTextParagraph().setText(dataStr));
  } else {
    section.addWidget(
      CardService.newTextParagraph()
        .setText('Error: ' + (result.error || result.detail || 'Unknown'))
    );
  }

  card.addSection(section);

  // Export buttons
  var exportSection = CardService.newCardSection();
  exportSection.addWidget(
    CardService.newButtonSet()
      .addButton(CardService.newTextButton()
        .setText('To Evernote')
        .setOnClickAction(
          CardService.newAction()
            .setFunctionName('sendTextToEvernote')
            .setParameters({
              subject: title + ' ' + new Date().toLocaleDateString(),
              body: result.data ? JSON.stringify(result.data, null, 2).substring(0, 5000) : 'No data'
            })
        ))
      .addButton(CardService.newTextButton()
        .setText('To Drive')
        .setOnClickAction(
          CardService.newAction()
            .setFunctionName('sendTextToDrive')
            .setParameters({
              subject: title + ' ' + new Date().toLocaleDateString(),
              body: result.data ? JSON.stringify(result.data, null, 2).substring(0, 5000) : 'No data'
            })
        ))
  );

  card.addSection(exportSection);
  card.addSection(backButtonSection_());
  return CardService.newNavigation().pushCard(card.build());
}


// ============================================================================
// HELPERS
// ============================================================================

function backButtonSection_() {
  return CardService.newCardSection().addWidget(
    CardService.newTextButton()
      .setText('Back to HUD')
      .setOnClickAction(CardService.newAction().setFunctionName('onHomepage'))
  );
}


// ============================================================================
// SETUP — Run once to configure API connection
// ============================================================================

/**
 * Update these values, then select setApiConfig > Run
 */
function setApiConfig() {
  var props = PropertiesService.getScriptProperties();

  // UPDATE THESE:
  props.setProperty('THUNDERBIRD_URL', 'https://YOUR-TUNNEL-URL.trycloudflare.com');
  props.setProperty('THUNDERBIRD_API_KEY', 'YOUR-API-KEY-HERE');

  Logger.log('Config saved. URL: ' + props.getProperty('THUNDERBIRD_URL'));
}
