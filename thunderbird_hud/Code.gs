/**
 * THUNDERBIRD HUD v3 — Sheets/Docs Sidebar + Web App
 * Dreams2Memories Travel, LLC
 *
 * Single query window routed through Thunderbird REST API + Groq AI.
 * Works as: Sheets sidebar, Docs sidebar, standalone Web App (phone bookmark).
 *
 * Setup:
 *   1. Paste this into Apps Script editor
 *   2. Add ThunderbirdHUD.html as an HTML file
 *   3. Run setApiConfig() with your tunnel URL + API key
 *   4. Deploy > New deployment > Web App (access: Anyone with Google account)
 *   5. Bookmark the Web App URL on your phone
 */

// ============================================================================
// CONFIG
// ============================================================================

function getConfig_() {
  var props = PropertiesService.getScriptProperties();
  return {
    apiUrl: props.getProperty('THUNDERBIRD_URL') || 'http://localhost:8766',
    apiKey: props.getProperty('THUNDERBIRD_API_KEY') || ''
  };
}

function apiCall_(endpoint, method, payload) {
  var config = getConfig_();
  var url = config.apiUrl + endpoint;

  var options = {
    method: method || 'GET',
    headers: {
      'X-API-Key': config.apiKey,
      'Content-Type': 'application/json'
    },
    muteHttpExceptions: true
  };

  if (payload && method !== 'GET') {
    options.payload = JSON.stringify(payload);
  }

  try {
    var response = UrlFetchApp.fetch(url, options);
    var code = response.getResponseCode();
    if (code >= 200 && code < 300) {
      return JSON.parse(response.getContentText());
    }
    return { error: 'HTTP ' + code, detail: response.getContentText().substring(0, 500) };
  } catch (e) {
    return { error: 'Connection failed', detail: e.toString().substring(0, 300) };
  }
}


// ============================================================================
// ENTRY POINTS — MENU, SIDEBAR, WEB APP
// ============================================================================

/**
 * Adds Thunderbird Command menu to Sheets or Docs.
 */
function onOpen(e) {
  var ui;
  try {
    ui = SpreadsheetApp.getUi();
  } catch (_) {
    try {
      ui = DocumentApp.getUi();
    } catch (_) {
      return;
    }
  }

  ui.createMenu('Thunderbird Command')
    .addItem('Open HUD', 'showSidebar')
    .addItem('Open HUD (Dialog)', 'showDialog')
    .addToUi();
}

/**
 * Opens HUD as sidebar (300px, docked right).
 */
function showSidebar() {
  var html = HtmlService.createHtmlOutputFromFile('ThunderbirdHUD')
    .setTitle('THUNDERBIRD')
    .setWidth(300);

  try {
    SpreadsheetApp.getUi().showSidebar(html);
  } catch (_) {
    try {
      DocumentApp.getUi().showSidebar(html);
    } catch (_) {}
  }
}

/**
 * Opens HUD as floating dialog (larger).
 */
function showDialog() {
  var html = HtmlService.createHtmlOutputFromFile('ThunderbirdHUD')
    .setTitle('THUNDERBIRD: MISSION CONTROL')
    .setWidth(800)
    .setHeight(700);

  try {
    SpreadsheetApp.getUi().showModelessDialog(html, 'THUNDERBIRD: MISSION CONTROL');
  } catch (_) {
    try {
      DocumentApp.getUi().showModelessDialog(html, 'THUNDERBIRD: MISSION CONTROL');
    } catch (_) {}
  }
}

/**
 * Web App entry — serves HUD as standalone full-screen page.
 * Deploy > New deployment > Web App to get a bookmarkable URL.
 */
function doGet(e) {
  return HtmlService.createHtmlOutputFromFile('ThunderbirdHUD')
    .setTitle('THUNDERBIRD COMMAND')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no');
}


// ============================================================================
// QUERY HANDLER — Single brain, all queries route here
// ============================================================================

/**
 * Called by the HUD front end via google.script.run.handleQuery(query).
 * Routes everything through Thunderbird API /api/ai/query.
 */
function handleQuery(query) {
  if (!query || !query.trim()) {
    return { error: 'Empty query' };
  }

  var q = query.trim().toLowerCase();

  // ── HELP ──────────────────────────────────────────────────
  if (q === 'help' || q === '?') {
    return { answer: 'THUNDERBIRD HUD COMMANDS\n\n' +
      'status / sitrep     — API health check\n' +
      'tools / list tools  — Show available tools\n' +
      'briefing / brief    — Morning intel briefing\n' +
      'fares / watches     — Active fare watches\n' +
      'roster / personas   — D2M staff roster\n' +
      'ship intel / ships  — Run ship intelligence sweep\n' +
      'world intel / world — Run world intelligence sweep\n' +
      'tech / tech monitor — Tech news digest\n' +
      'staff <topic>       — Staff meeting (all personas)\n' +
      'meeting <topic>     — Same as staff\n' +
      'A1-A12 <query>      — Query individual persona\n' +
      'memory / recall     — Memory stats\n' +
      'history             — Recent conversation history\n' +
      'search <term>       — Search past conversations\n' +
      '\nEARA has memory — she remembers your recent conversations.' };
  }

  // ── MEMORY STATS ───────────────────────────────────────────
  if (q === 'memory' || q === 'recall' || q === 'memory stats') {
    var memStats = apiCall_('/api/memory/stats', 'GET');
    if (memStats.status === 'success') {
      var lines = [
        'EARA MEMORY',
        'Total conversations: ' + memStats.total_conversations,
        'Today: ' + memStats.today_conversations,
        'Facts stored: ' + memStats.total_facts,
      ];
      if (memStats.top_clients && memStats.top_clients.length > 0) {
        lines.push('\nMost discussed clients:');
        memStats.top_clients.forEach(function(c) {
          lines.push('  ' + c.client + ': ' + c.count + ' queries');
        });
      }
      if (memStats.top_tools && memStats.top_tools.length > 0) {
        lines.push('\nMost used tools:');
        memStats.top_tools.forEach(function(t) {
          lines.push('  ' + t.tool + ': ' + t.count + ' calls');
        });
      }
      return { answer: lines.join('\n') };
    }
    return { answer: 'Memory unavailable.' };
  }

  // ── CONVERSATION HISTORY ───────────────────────────────────
  if (q === 'history' || q === 'recent' || q === 'last conversations') {
    var hist = apiCall_('/api/memory/recent?limit=5', 'GET');
    if (hist.status === 'success' && hist.exchanges && hist.exchanges.length > 0) {
      var lines = ['RECENT CONVERSATIONS (' + hist.count + '):\n'];
      hist.exchanges.forEach(function(ex) {
        var ts = (ex.timestamp || '').substring(0, 16).replace('T', ' ');
        lines.push('[' + ts + ']');
        lines.push('You: ' + (ex.user_query || '').substring(0, 80));
        lines.push('EARA: ' + (ex.assistant_response || '').substring(0, 120));
        lines.push('');
      });
      return { answer: lines.join('\n') };
    }
    return { answer: 'No conversation history yet.' };
  }

  // ── SEARCH MEMORY ──────────────────────────────────────────
  if (/^search\s+/i.test(q)) {
    var searchTerm = query.trim().replace(/^search\s+/i, '');
    var searchResult = apiCall_('/api/memory/search', 'POST', { query: searchTerm, limit: 5 });
    if (searchResult.status === 'success' && searchResult.results && searchResult.results.length > 0) {
      var lines = ['MEMORY SEARCH: "' + searchTerm + '" (' + searchResult.count + ' results)\n'];
      searchResult.results.forEach(function(ex) {
        var ts = (ex.timestamp || '').substring(0, 16).replace('T', ' ');
        lines.push('[' + ts + ']');
        lines.push('You: ' + (ex.user_query || '').substring(0, 80));
        lines.push('EARA: ' + (ex.assistant_response || '').substring(0, 150));
        lines.push('');
      });
      return { answer: lines.join('\n') };
    }
    return { answer: 'No results for "' + searchTerm + '" in memory.' };
  }

  // ── STATUS ────────────────────────────────────────────────
  if (q === 'status' || q === 'sitrep') {
    var health = apiCall_('/api/health', 'GET');
    if (health.status === 'ok') {
      return { answer: 'Thunderbird API Online.\nTimestamp: ' + (health.timestamp || 'N/A') + '\nGroq AI: Active\nMCP Tools: Connected' };
    }
    return { answer: 'Thunderbird API OFFLINE.\n' + (health.error || '') + '\n' + (health.detail || '') };
  }

  // ── OFFLINE GUARD ─────────────────────────────────────────
  // Before any API-dependent command, verify the link is up.
  // This prevents hallucinated responses when the tunnel is dead.
  var ping = apiCall_('/api/health', 'GET');
  if (ping.status !== 'ok') {
    return { answer: 'LINK DOWN — Cannot process query.\n' +
      (ping.error || '') + '\n' + (ping.detail || '') +
      '\n\nUpdate THUNDERBIRD_URL in Script Properties\nwith the current tunnel URL, then retry.' };
  }

  // ── TOOLS LIST ────────────────────────────────────────────
  if (q === 'tools' || q === 'list tools') {
    var tools = apiCall_('/api/tools', 'GET');
    if (tools.tools) {
      return { answer: tools.count + ' tools online:\n\n' + tools.tools.join('\n') };
    }
    return { answer: 'Could not retrieve tool list.', error: tools.error };
  }

  // ── BRIEFING ──────────────────────────────────────────────
  if (/^(briefing|morning brief|brief)$/i.test(q)) {
    var brief = apiCall_('/api/briefing', 'GET');
    if (brief.status === 'success' && brief.data) {
      var display = typeof brief.data.summary === 'string'
        ? brief.data.summary
        : JSON.stringify(brief.data, null, 2).substring(0, 4000);
      return { answer: 'MORNING BRIEFING\nSource: ' + (brief.file || 'cached') + '\n\n' + display };
    }
    return { answer: brief.message || 'No briefing data cached. Scheduler generates at 6:30 AM MT.' };
  }

  // ── FARE WATCHES ──────────────────────────────────────────
  if (q === 'fares' || q === 'fare watches' || q === 'watches') {
    var fares = apiCall_('/api/fare-watches', 'GET');
    if (fares.watches && fares.watches.length > 0) {
      var lines = fares.watches.map(function(w) {
        return w.provider + ' | ' + w.label + '\n  ' + w.price_pp + '/pp | Total: ' + w.total + ' | ' + w.vs_baseline;
      });
      return { answer: 'FARE WATCHES (' + fares.count + ' active)\n\n' + lines.join('\n\n') };
    }
    return { answer: 'No active fare watches.' };
  }

  // ── PERSONA ROSTER ────────────────────────────────────────
  if (q === 'roster' || q === 'staff' || q === 'personas') {
    var personas = apiCall_('/api/personas', 'GET');
    if (personas.personas) {
      var lines = personas.personas.map(function(p) {
        return p.icon + ' ' + p.id + ' — ' + p.name + ': ' + p.role;
      });
      return { answer: 'D2M STAFF ROSTER (' + personas.count + ' personas)\n\n' + lines.join('\n') };
    }
    return { answer: 'Could not retrieve persona roster.' };
  }

  // ── STAFF MEETING ─────────────────────────────────────────
  if (/^(staff|meeting|war room)\s+/i.test(q)) {
    var meetingQuery = query.trim().replace(/^(staff|meeting|war room)\s+/i, '');
    var meeting = apiCall_('/api/ai/staff-meeting', 'POST', { query: meetingQuery });
    if (meeting.status === 'success') {
      return { answer: 'STAFF MEETING (' + meeting.persona_count + ' personas)\n' + meeting.consolidated_report };
    }
    return { error: 'Staff meeting failed: ' + (meeting.error || 'Unknown') };
  }

  // ── INDIVIDUAL PERSONA (A1-A12) ───────────────────────────
  var personaMatch = query.trim().match(/^(A[1-9]|A1[0-2])\b\s*(.*)/i);
  if (personaMatch) {
    var personaId = personaMatch[1].toUpperCase();
    var personaQuery = personaMatch[2] || 'Give me your tactical assessment of current operations.';
    var personaResult = apiCall_('/api/ai/persona', 'POST', { persona_id: personaId, query: personaQuery });
    if (personaResult.status === 'success' && personaResult.answer) {
      return { answer: personaResult.icon + ' ' + personaResult.persona + '-' + personaResult.name.toUpperCase() + ':\n\n' + personaResult.answer };
    }
    return { error: 'Persona ' + personaId + ' failed: ' + (personaResult.error || 'Unknown') };
  }

  // ── TOOL SHORTCUTS (prefix/keyword matching) ─────────────
  if (/^(ship\s*intel|ships)\b/i.test(q)) {
    var shipContext = query.trim().replace(/^(ship\s*intel|ships)\s*/i, '');
    return runToolWithContext_('run_ship_intelligence_sweep', 'SHIP INTEL', shipContext);
  }
  if (/^(world\s*intel|world)\b/i.test(q)) {
    var worldContext = query.trim().replace(/^(world\s*intel|world)\s*/i, '');
    return runToolWithContext_('run_world_intelligence_sweep', 'WORLD INTEL', worldContext);
  }
  if (/^(tech\s*monitor|tech)\b/i.test(q)) {
    return runTool_('run_daily_tech_monitor', 'TECH MONITOR');
  }
  if (/^(fares|fare\s*watch|watches)\b/i.test(q)) {
    var fares = apiCall_('/api/fare-watches', 'GET');
    if (fares.watches && fares.watches.length > 0) {
      var lines = fares.watches.map(function(w) {
        return w.provider + ' | ' + w.label + '\n  ' + w.price_pp + '/pp | Total: ' + w.total + ' | ' + w.vs_baseline;
      });
      return { answer: 'FARE WATCHES (' + fares.count + ' active)\n\n' + lines.join('\n\n') };
    }
    return { answer: 'No active fare watches.' };
  }

  // ── INTERCEPT: Queries about cruises/ships → suggest ship intel ──
  if (/^(cruise|cruises|ship|ships|voyage|sailing)\b/i.test(q)) {
    return { answer: 'For cruise intelligence, type:\n' +
      '• "ship intel" — Full ship intelligence sweep\n' +
      '• "ship intel Antarctica" — Focused sweep with context\n\n' +
      'For general cruise knowledge, rephrase as a question\nand I\'ll answer from travel expertise.' };
  }

  // ── INTERCEPT: Ship tracking (no real-time data) ─────────
  if (/ship\s*(locat|track|position|where|find|gps)/i.test(q)) {
    return { answer: 'Real-time ship tracking not available here.\n\n' +
      'Options:\n' +
      '• "ship intel" — Thunderbird ship intelligence sweep\n' +
      '• MarineTraffic.com — Live AIS vessel tracking\n' +
      '• VesselFinder.com — Free ship position lookup\n' +
      '• Cruise line app — Official tracking' };
  }

  // ── GENERAL AI QUERY (Groq — general knowledge only) ──────
  var result = apiCall_('/api/ai/query', 'POST', { query: query.trim() });

  if (result.status === 'success' && result.answer) {
    return { answer: result.answer };
  }

  return { error: result.error || 'Unknown error', detail: result.detail || '' };
}


/**
 * Execute an MCP tool by name and return formatted result.
 */
function runTool_(toolName, label) {
  var result = apiCall_('/api/tool/' + toolName, 'POST', {});
  if (result.status === 'success') {
    var text = JSON.stringify(result.data, null, 2);
    if (text.length > 5000) text = text.substring(0, 5000) + '\n\n... [truncated]';
    return { answer: label + '\n\n' + text };
  }
  return { error: label + ' failed: ' + (result.error || result.detail || 'Unknown') };
}


/**
 * Run a tool, then pass its output + original query to Groq for a contextual summary.
 * If extraContext is empty, behaves like runTool_ but with AI summarization.
 */
function runToolWithContext_(toolName, label, extraContext) {
  var result = apiCall_('/api/tool/' + toolName, 'POST', {});
  if (result.status !== 'success') {
    return { error: label + ' failed: ' + (result.error || result.detail || 'Unknown') };
  }

  var rawData = JSON.stringify(result.data, null, 2);
  if (rawData.length > 4000) rawData = rawData.substring(0, 4000) + '\n... [truncated]';

  // If no extra context, just return the raw data with label
  if (!extraContext || !extraContext.trim()) {
    return { answer: label + '\n\n' + rawData };
  }

  // Pass tool output + user context to AI for a focused summary
  var aiResult = apiCall_('/api/ai/query', 'POST', {
    query: extraContext,
    context: label + ' DATA:\n' + rawData
  });

  if (aiResult.status === 'success' && aiResult.answer) {
    return { answer: label + ' — ' + extraContext.trim() + '\n\n' + aiResult.answer };
  }

  // Fallback to raw data if AI fails
  return { answer: label + '\n\n' + rawData };
}


// ============================================================================
// HEALTH CHECK — Called by front end on load
// ============================================================================

function checkHealth() {
  return apiCall_('/api/health', 'GET');
}


// ============================================================================
// EVERNOTE EXPORT — Called by front end
// ============================================================================

/**
 * Send text content to Evernote via yodainva@gmail.com.
 */
function sendToEvernote(subject, body) {
  return apiCall_('/api/send-to-evernote', 'POST', {
    subject: subject || 'Thunderbird Note',
    body: body || ''
  });
}


// ============================================================================
// SETUP — Run once to configure API connection
// ============================================================================

/**
 * Update these values, then select setApiConfig > Run.
 */
function setApiConfig() {
  var props = PropertiesService.getScriptProperties();

  // UPDATE THESE:
  props.setProperty('THUNDERBIRD_URL', 'https://api.d2mluxury.quest');
  props.setProperty('THUNDERBIRD_API_KEY', '***REMOVED-SECRET***');

  Logger.log('Config saved. URL: ' + props.getProperty('THUNDERBIRD_URL'));
}
