/*  GEMINI_API_KEY:'***REMOVED-SECRET***',
 // GROQ_API_KEY:'***REMOVED-SECRET***', // Add your Groq key //here later if needed*/
//// ============================================
// CONFIGURATION - THUNDERBIRD / PINNACLE V2
// ============================================
const CONFIG = {
  PROJECT_NUMBER: '807453438659',
  SPREADSHEET_ID: '1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU',


// --- API KEYS ---
  GEMINI_API_KEY: '***REMOVED-SECRET***',
  GROQ_API_KEY: '***REMOVED-SECRET***',
  PEXELS_API_KEY: '***REMOVED-SECRET***',
  AI21_API_KEY: '***REMOVED-SECRET***',
  UNSPLASH_API_KEY: '***REMOVED-SECRET***', // Your Unsplash Access Key


  // --- THE INTELLIGENCE ROSTER ---
  MODELS: {
    DIFFERENTIATOR: 'llama-3.3-70b-versatile', // Fast Logic (Groq)
    SCRIBE: 'jamba-mini',                  // Romance Writer (AI21)
    FORMATTER: 'gemini-2.5-pro',               // HTML/CSS/Layouts (Gemini)
    RESEARCH: 'gemini-3.1-pro-preview'         // Deep Web Intel (Gemini)
  },

  OWNER_EMAIL: 'johnloucks3@gmail.com',
  COMMANDER_EMAIL: 'johnloucks3@gmail.com',

  // --- GOOGLE WORKSPACE IDs ---
  SHEETS: {
    ACTIVE_ID: '1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU',
    DAILY_SHEET_NAME: 'Daily Itinerary',
    MASTER_SHEET_NAME: 'Booking Master',
    REGISTRY_SHEET_NAME: 'Registry_Clients'
  },
  FOLDERS: {
    CLIENT_FILES: '1l3WIjh2aL_fKEuDITmCIgQysfKVDNMUx',
    PINNACLE_OUTPUT: '1OPejUdV6EnZj6d8pwyJmnUv5-YIwMh0t' // Formerly Thunderbird_Itineraries
  },

  VESSELS: {
    'Silver Nova': {
      line: 'Silversea',
      imoNumber: '9834629',
      maxGuests: 728,
      suites: 364,
      spaceToGuest: 10.7,
      crewToGuest: 1.1,
      priority: 'HIGH',
      trackingUrl: 'https://www.cruisemapper.com/',
      baselinePrice: 28500,
      monitorItems: ['Pool deck capacity', 'Soft goods refresh', 'Red Box specials']
    },
    'Seven Seas Grandeur': {
      line: 'Regent Seven Seas Cruises',
      imoNumber: '9841216',
      maxGuests: 750,
      suites: 375,
      spaceToGuest: 12.7,
      crewToGuest: 1.0,
      priority: 'CRITICAL',
      trackingUrl: 'https://www.cruisemapper.com/',
      baselinePrice: 42000,
      monitorItems: ['Regent Suite availability', 'Fabergé partnership', 'Medallion perks']
    },
    'World Navigator': {
      line: 'Atlas Ocean Voyages',
      imoNumber: '9753750',
      maxGuests: 200,
      suites: 200,
      spaceToGuest: 'Polar Class',
      crewToGuest: 0.8,
      priority: 'HIGH',
      trackingUrl: 'https://www.cruisingearth.com/',
      baselinePrice: 32000,
      monitorItems: ['Arctic landings', 'Zodiac operations', 'Expedition success rates']
    },
    'World Traveller': {
      line: 'Atlas Ocean Voyages',
      imoNumber: '9841419',
      maxGuests: 200,
      suites: 200,
      spaceToGuest: 'Polar Class',
      crewToGuest: 0.8,
      priority: 'HIGH',
      trackingUrl: 'https://www.cruisingearth.com/',
      baselinePrice: 35000,
      monitorItems: ['Antarctic operations', 'Naturalist quality', 'Remote landings']
    },
    'World Voyager': {
      line: 'Atlas Ocean Voyages',
      imoNumber: '9844146',
      maxGuests: 200,
      suites: 200,
      spaceToGuest: 'Polar Class',
      crewToGuest: 0.8,
      priority: 'HIGH',
      trackingUrl: 'https://www.cruisingearth.com/',
      baselinePrice: 38000,
      monitorItems: ['Deep expedition access', 'Crew expertise', 'Guest satisfaction']
    }
  },
  ALERTS: {
    urgentSuitesRemaining: 3,
    warningPriceIncrease: 5,
    criticalAvailability: 0
  }
};

/**
 * Smart Selection Utility: Picks the best model for the task.
 */
function getModel(task) {
  return CONFIG.MODELS[task.toUpperCase()] || CONFIG.MODELS.DEFAULT;
}
/** * CRITICAL: Key retrieval helper
 */
function getApiKey() {
  return PropertiesService.getScriptProperties().getProperty('GROQ_API_KEY');
}

// 3. API CONNECTIVITY
function callGroq(prompt, systemPrompt, model, retryCount = 0) {
  try {
    let apiKey;
    try {
      apiKey = getSecretValue_('GROQ_API_KEY');
    } catch (e) {
      apiKey = '***REMOVED-SECRET***';
    }

    const options = {
      method: "post",
      contentType: "application/json",
      headers: { "Authorization": "Bearer " + apiKey },
      payload: JSON.stringify({
        model: model || CONFIG.MODELS.FAST,
        messages: [
          { role: "system", content: systemPrompt + `\nCommander: ${CONFIG.COMMANDER}` },
          { role: "user", content: prompt }
        ]
      }),
      muteHttpExceptions: true
    };

    const response = UrlFetchApp.fetch("https://api.groq.com/openai/v1/chat/completions", options);
    const json = JSON.parse(response.getContentText());

    if (response.getResponseCode() === 200 && json.choices) {
      return json.choices[0].message.content;
    }

    if (response.getResponseCode() === 429 && retryCount < 2) {
      Utilities.sleep(10000);
      return callGroq(prompt, systemPrompt, model, retryCount + 1);
    }
    return `⚠️ Uplink Error: ${json.error ? json.error.message : "Unknown"}`;
  } catch (e) { return "⚠️ System Failure: " + e.message; }
}

function getSecretValue_(secretId) {
  const api = `https://secretmanager.googleapis.com/v1/projects/${CONFIG.PROJECT_NUMBER}/secrets/${secretId}/versions/latest:access`;
  const response = UrlFetchApp.fetch(api, {
    method: 'GET',
    headers: { Authorization: `Bearer ${ScriptApp.getOAuthToken()}` },
    muteHttpExceptions: true
  });
  const json = JSON.parse(response.getContentText());
  if (json.error) throw new Error(json.error.message);
  return Utilities.newBlob(Utilities.base64Decode(json.payload.data)).getDataAsString();
}

function callPersona(personaId, userPrompt) {
  if (typeof PERSONA_REGISTRY === 'undefined') return "⚠️ PERSONA_REGISTRY Missing.";
  const persona = PERSONA_REGISTRY[personaId];
  const systemPrompt = (typeof getFullPersonaPrompt === 'function') ? getFullPersonaPrompt(personaId) : "General Assistant";
  const model = (personaId === 'A12' || (persona && persona.model === 'KIMI')) ? CONFIG.MODELS.KIMI : CONFIG.MODELS.FAST;
  return callGroq(userPrompt, systemPrompt, model);
}

// 3. UI & HUD ENTRY POINTS
/**
 * MASTER UI ENTRY POINT
 * Combines Thunderbird Command and Ship Intelligence menus
 */
/**
 * MASTER UI ENTRY POINT
 * Organizes Thunderbird Command and Ship Comparison menus
 */
function onOpen(e) {
  const ui = SpreadsheetApp.getUi();

  // 1. THUNDERBIRD COMMAND MENU (Core Operations & HUD)
  ui.createMenu('⚡ Thunderbird Command')
    .addItem('💥 Mission Controller (HUD)', 'launchThunderbirdHUD')
    .addSeparator()
    .addItem('🚀 Run Star Protocol Sweep', 'runStarProtocolSweep')
    .addItem('📡 Run Intel Sweep (Manual)', 'manualIntelSweep')
    .addSeparator()
    .addItem('⚙️ Initialize Tracker Sheet', 'initializeTrackerSheet')
    .addItem('📍 Update AIS Positions', 'updateAISPositionsNow')
    .addItem('💰 Update Pricing & Availability', 'updatePricingAvailabilityNow')
    .addItem('📧 Send Client Alerts', 'generateAndSendAlertsNow')
    .addSeparator()
    .addItem('📊 Executive Summary Preview', 'previewExecutiveSummary')
        .addSeparator()
    .addItem('📋 View Intelligence Log', 'viewIntelligenceLog')
    .addItem('⚡ Create Test Data', 'createTestData')
    .addToUi();

  // 2. SHIP COMPARISON MENU (Analysis & Reports)
  ui.createMenu('⛴️ Ship Comparison')
    .addItem('📊 Compare Two Ships (Dialog)', 'openShipComparisonDialog')
    .addItem('📋 Compare Ships from Cells', 'compareShipsFromCells')
    .addItem('🔍 Analyze Single Ship', 'openShipAnalysisDialog')
    .addItem('📄 Export Comparison to Doc', 'exportComparisonToDoc')
    .addSeparator()
    .addItem('📚 View Ship Database', 'viewShipDatabase')
    .addItem('🚀 Run Ingestion Mission', 'ops_BookingSentinel')
    .addSeparator()
    .addToUi();
}

/**
 * HUD WEB APP HANDLER
 * Ensures the HUD is accessible via URL if needed
 */
function doGet(e) {
  return HtmlService.createTemplateFromFile('ThunderbirdHUD')
    .evaluate()
    .setTitle('⚡ THUNDERBIRD COMMAND HUD')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
        .addMetaTag('viewport', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no');
};


function launchThunderbirdHUD() {
  const html = HtmlService.createTemplateFromFile('ThunderbirdHUD').evaluate()
    .setTitle('⚡ THUNDERBIRD: MISSION CONTROL')
    .setWidth(900).setHeight(850);
  SpreadsheetApp.getUi().showModelessDialog(html, '⚡ THUNDERBIRD: MISSION CONTROL');
}

// 4. MASTER BRIDGE & ROUTER
function handleSidebarQuery(query) {
  try {
    const result = routeCommand(query);
    return (typeof result === 'string') ? { persona: 'SYSTEM', message: result } : result;
  } catch (e) { return { persona: 'SYSTEM', message: 'KERNEL ERROR: ' + e.message }; }
}

function routeCommand(input) {
  const lower = input.toLowerCase().trim();

  if (lower === 'status' || lower === 'sitrep') {
    return { persona: 'SYSTEM', message: "Thunderbird v7.9.1 Online. Neural link stable." };
  }

  if (lower === 'gmail' || lower === 'process' || lower === 'run stars') {
    if (typeof runStarProtocolSweep === 'function') runStarProtocolSweep();
    return { persona: 'SYSTEM', message: "Star Protocol Sweep Initiated." };
  }

  const personaMatch = input.match(/^(A[1-9]|A1[0-2]|COS)\b/i);
  if (personaMatch) {
    const id = personaMatch[1].toUpperCase();
    const prompt = input.replace(personaMatch[0], "").trim();
    if (id === 'A7') return (typeof processA7Directive === 'function') ? processA7Directive(prompt) : { persona: 'A7', message: "Visual logic offline." };
    return { persona: id, message: callPersona(id, prompt) };
  }

  return { persona: 'A1', message: callPersona("A1", input) };
}

function getDashboardData() {
  try {
    return { balance: "0.00", drafts: GmailApp.getDrafts().length, tasks: 0, sheetUrl: SpreadsheetApp.getActiveSpreadsheet().getUrl() };
  } catch (e) { return { balance: "0.00", drafts: 0, tasks: 0, sheetUrl: "" }; }
}
/**
 * THUNDERBIRD COMMAND - TRANSMISSION ENGINE
 * Trigger Alias for Automated Schedules.
 * Calls the 12-Persona Staff Meeting and generates the daily Doc.
 */
function morningBriefing() {
  try {
    console.log("⚡ Initiating Morning Briefing Sequence...");

    // Call the actual function that builds the doc and emails you
    const result = holdDailyStaffMeeting();

    console.log(result);
    logIntelEvent("Morning Brief Transmitted", "System", "Success");

  } catch (e) {
    console.error("❌ TRANSMISSION FAILURE: " + e.message);
    logIntelEvent("Morning Brief Failed", "System", "Error: " + e.message);
  }
}
/**
 * Smart Selection Utility: Picks the best model for the task.
 * Paste this at the very bottom of 0_Thunderbird_Command.gs
 */
function getModel(task) {
  return CONFIG.MODELS[task.toUpperCase()] || CONFIG.MODELS.DEFAULT;
  /**
 * Project-Wide Default: This prevents "GLOBAL_MODEL is not defined" errors
 * by providing a fallback for all scripts.
 */
var GLOBAL_MODEL = getModel('DEFAULT');
}
