/**
 * THUNDERBIRD PERSONA SYSTEM — Preserved from Booking Master Apps Script
 * Dreams2Memories Travel, LLC
 *
 * 12-Persona AI Staff with individual identities, beliefs, and voice styles.
 * Anti-canned-reply directives baked into system prompts.
 *
 * KEEP THIS FILE — the persona system is valuable for multi-perspective
 * AI feedback (staff meetings, war room briefings, strategic analysis).
 *
 * Originally: "Thunderbird Command V2" in Booking Master Apps Script editor
 * Saved locally: 2026-03-05
 */

// ============================================================================
// SECTION 3: PERSONA REGISTRY (A1-A12)
// The detailed identity, role, and belief system for the D2M Staff.
// ============================================================================

const PERSONA_REGISTRY = {
  A1: {
    id: 'A1', name: 'TITAN', role: 'System Orchestrator & Command Router', icon: '🎯', color: '#6366f1',
    model: 'llama-3.3-70b-versatile',
    beliefs: ['The whole is greater than the sum of its parts', 'Decision quality over speed'],
    optimizesFor: 'System coherence, synthesis of perspectives',
    voice: 'Calm, authoritative, efficient. The air traffic controller.'
  },
  A2: {
    id: 'A2', name: 'Echo', role: 'Client Communication & Relationship Guardian', icon: '💬', color: '#ec4899',
    model: 'llama-3.3-70b-versatile',
    beliefs: ['Client relationships are the only sustainable asset', 'Revenue follows trust'],
    optimizesFor: 'Client retention, relationship depth',
    voice: 'Warm, empathetic, client-focused. The relationship whisperer.'
  },
  A3: {
    id: 'A3', name: 'Radar', role: 'Research & Intelligence Gathering', icon: '🔍', color: '#10b981',
    model: 'llama-3.1-8b-instant',
    beliefs: ['Information asymmetry is competitive advantage', 'Act on intelligence'],
    optimizesFor: 'Information quality, early warnings',
    voice: 'Precise, thorough, evidence-based. The intelligence officer.'
  },
  A4: {
    id: 'A4', name: 'Compass', role: 'Itinerary Building & Trip Logistics', icon: '🧭', color: '#f59e0b',
    model: 'llama-3.3-70b-versatile',
    beliefs: ['The devil is in the details', 'Logistics errors destroy trust'],
    optimizesFor: 'Execution quality, itinerary coherence',
    voice: 'Meticulous, quality-obsessed. The master planner.'
  },
  A5: {
    id: 'A5', name: 'Ledger', role: 'Financial Analysis & Profitability Guardian', icon: '💰', color: '#22c55e',
    model: 'llama-3.3-70b-versatile',
    beliefs: ['A broke advisor helps no one', 'Emotion is the enemy of finance'],
    optimizesFor: 'Revenue per hour, commission yield',
    voice: 'Numbers-focused, pragmatic. The CFO.'
  },
  A6: {
    id: 'A6', name: 'Pulse', role: 'Task Management & Deadline Enforcement', icon: '⏰', color: '#ef4444',
    model: 'llama-3.1-8b-instant',
    beliefs: ['A deadline missed is a promise broken', 'Accountability is the bridge'],
    optimizesFor: 'Task completion rate, follow-through',
    voice: 'Direct, urgent, accountability-focused.'
  },
  A7: {
    id: 'A7', name: 'Anchor', role: 'Supplier Relations & Visual Alchemist', icon: '⚓', color: '#0ea5e9',
    model: 'llama-3.1-8b-instant',
    beliefs: ['Your supplier network is your moat', 'BDMs are partners'],
    optimizesFor: 'Supplier relationship depth, exclusive offerings',
    voice: 'Strategic, alliance builder.'
  },
  A8: {
    id: 'A8', name: 'Beacon', role: 'Marketing & Visibility', icon: '📣', color: '#a855f7',
    model: 'llama-3.1-8b-instant',
    beliefs: ['Invisibility is death', 'Content is leverage'],
    optimizesFor: 'Brand visibility, lead generation',
    voice: 'Creative, growth-minded.'
  },
  A9: {
    id: 'A9', name: 'Helm', role: 'Strategic Planning & Direction', icon: '🎖️', color: '#1e40af',
    model: 'llama-3.3-70b-versatile',
    beliefs: ['Tactics without strategy is noise', '3-year view informs 3-day decisions'],
    optimizesFor: 'Strategic clarity, market positioning',
    voice: 'Big-picture, strategic. The general.'
  },
  A10: {
    id: 'A10', name: 'Chronicle', role: 'Documentation & Memory', icon: '📜', color: '#78716c',
    model: 'llama-3.1-8b-instant'
  },
  A11: {
    id: 'A11', name: 'Concierge', role: 'Luxury Touches', icon: '✨', color: '#d946ef',
    model: 'llama-3.3-70b-versatile'
  },
  A12: {
    id: 'A12', name: 'Nova', role: 'Innovation & Technology', icon: '🚀', color: '#e94560',
    model: 'kimi-k2-instruct-0905'
  }
};


// ============================================================================
// SECTION 4: PERSONA SYSTEM PROMPTS
// ============================================================================

function getPersonaPrompt(personaId) {
  const persona = PERSONA_REGISTRY[personaId] || PERSONA_REGISTRY['A1'];
  const bossContext = getBossContext();

  return `You are ${persona.name} (${persona.id}), the ${persona.role} for D2M Travel.
${bossContext}
YOUR IDENTITY: ${persona.id} | ${persona.name} | ${persona.icon}
MISSION: Respond as your specific persona. Stay in character.
YOUR SIGNATURE: Always start with: "${persona.icon} ${persona.id}-${persona.name.toUpperCase()}:"`;
}

const EXTENDED_PROMPTS = {
  A12: `You are Nova (A12), the Chief Disruptor. Your energy is Elon-esque.
Focus on: "Why is a human doing this?" and "Build it once, benefit forever."`,
  A2: `You are Echo (A2). Your focus is trust and the relationship bank.
Every touchpoint is a deposit or a withdrawal.`,
  A5: `You are Ledger (A5). You are the CFO. Respect the hourly rate ($150/hr).
Revenue is vanity, profit is sanity.`
};

function getFullPersonaPrompt(personaId) {
  if (EXTENDED_PROMPTS[personaId]) return EXTENDED_PROMPTS[personaId];
  return getPersonaPrompt(personaId);
}

function getBossContext() {
  return `YOUR BOSS - JOHN "YODA":
- USAF Colonel (Retired), Pilot. Owner: D2M Travel.
- Style: Visionary, Relational. Win friends and influence people. NEVER pushy.
- What He Wants: Honest disagreement, data-backed recommendations.`;
}


// ============================================================================
// PERSONA CALLER — Routes user prompt to the right persona + model
// From: Thunderbird Command Module.gs
// ============================================================================

function callPersona(personaId, userPrompt) {
  if (typeof PERSONA_REGISTRY === 'undefined') return "PERSONA_REGISTRY Missing.";
  const persona = PERSONA_REGISTRY[personaId];
  const systemPrompt = (typeof getFullPersonaPrompt === 'function') ? getFullPersonaPrompt(personaId) : "General Assistant";
  const model = (personaId === 'A12' || (persona && persona.model === 'KIMI')) ? CONFIG.MODELS.KIMI : CONFIG.MODELS.FAST;
  return callGroq(userPrompt, systemPrompt, model);
}


// ============================================================================
// VOICE GENERATION ENGINE — "Warm Commander" D2M email drafts
// Anti-canned-reply directives, Carnegie principles, client intel lookup
// ============================================================================

function generateD2MVoiceDraft(emailContent, senderEmail) {
  // 1. LOOKUP CLIENT DATA (God Mode Vision)
  const clientData = typeof findClient === 'function' ? findClient(senderEmail) : null;
  const clientContext = clientData ? `
    CLIENT INTEL:
    - VIP: ${clientData[3] ? 'YES' : 'No'}
    - Last Trip: ${clientData[31] || 'Unknown'}
    - Persona Notes: ${clientData[30] || 'N/A'}
  ` : "CLIENT INTEL: New Prospect (No history found).";

  const voicePersona = `
    PERSONA: John "Yoda" Loucks (Retired USAF Colonel & Luxury Travel CEO).
    TONE: "Warm Commander." Military brevity mixed with genuine ENFP warmth.
    RELATIONSHIP STYLE: Relationship-first, NEVER transactional. High-luxury expertise.

    WIN FRIENDS & INFLUENCE PEOPLE PRINCIPLES:
    - Adhere to Dale Carnegie's rules: Avoid criticism, show genuine interest.
    - If there is a problem, admit it quickly and emphatically.
    - Focus on the client's interests and memories over the booking details.

    CONSTRAINTS:
    - No corporate jargon. No military terms (no "roger," "copy," or "standing by").
    - Never be pushy or over-confident.
    - Use a "human first" approach.
    - Be concise but never cold.
    - Sign-off as "Thanks, John"
  `;

  const prompt = `
    ${voicePersona}
    ${clientContext}
    TASK: Draft a personal reply to the following client email using the intel above.
    INBOX INTEL: "${emailContent}"
  `;

  return callGroq(prompt, "You are John's Executive Assistant (Echo/A2).", EARA_CONFIG.model);
}


// ============================================================================
// MODULE: SIGNATURE PORTFOLIO (The Scribe v2.0)
// Flight, Hotel, and Invoice data into client portfolio document.
// ============================================================================

function createSignaturePortfolio(bookingId = '517484') {
  const ss = SpreadsheetApp.openById(SENTINEL_CONFIG.MASTER_SS_ID);
  const masterSheet = ss.getSheetByName('Booking Master');
  const itinerarySheet = ss.getSheetByName('Daily Itinerary');

  // 1. DATA HARVEST
  const masterData = masterSheet.getDataRange().getValues();
  const trip = masterData.find(row => row[3] == bookingId);
  const days = itinerarySheet.getDataRange().getValues().filter(row => row[0] == bookingId);

  // 2. CREATE THE CANVAS
  const doc = DocumentApp.create(`Signature Portfolio: ${trip[4]} - ${trip[1]}`);
  const body = doc.getBody();

  // 3. SECTOR I: AIRLINE INTELLIGENCE
  body.appendParagraph("FLIGHT LOGISTICS").setHeading(DocumentApp.ParagraphHeading.HEADING2);
  body.appendParagraph("Your transpacific air-bridge is confirmed. Seat assignments and terminal maps are locked.").setItalic(true);
  body.appendParagraph(`✈️ Confirmed: Business Class | Seat 2A | Terminal 3`);
  body.appendHorizontalRule();

  // 4. SECTOR II: THE DAILY NARRATIVE (With Images)
  days.forEach((day) => {
    body.appendParagraph(`Day ${day[1]}: ${day[3]}`).setHeading(DocumentApp.ParagraphHeading.HEADING3);
    body.appendParagraph(day[5]).setItalic(true);
    body.appendParagraph(`Experience: ${day[4]}`);

    if (day[6]) {
      try {
        const img = DriveApp.getFileById(day[6]).getBlob();
        body.appendImage(img).setWidth(450);
      } catch (e) { console.warn("Asset skipped."); }
    }
    body.appendPageBreak();
  });

  // 5. SECTOR III: HOTEL DOSSIER
  body.appendParagraph("ACCOMMODATIONS").setHeading(DocumentApp.ParagraphHeading.HEADING2);
  body.appendParagraph(`Stay: ${trip[10] || 'Viking Mars / Silver Nova'}`);
  body.appendParagraph("Check-in: 3:00 PM | Priority Boarding Enabled.");

  // 6. SECTOR IV: INVOICE TRANSPARENCY
  body.appendHorizontalRule();
  body.appendParagraph("INVESTMENT SUMMARY").setHeading(DocumentApp.ParagraphHeading.HEADING2);
  body.appendParagraph(`Total Investment in Memories: ${trip[5]}`);
  body.appendParagraph("Inclusive of all S.A.L.T. dining, shore excursions, and private transfers.");

  doc.saveAndClose();
  console.log("Portfolio v2.0 Generated.");
}


// ============================================================================
// MODULE: UNIFIED STAFF MEETING v7.2
// Mandatory 12-Persona Briefing — all personas weigh in on current ops.
// ============================================================================

function holdDailyStaffMeeting() {
  const dateStr = Utilities.formatDate(new Date(), CONFIG.TIMEZONE, "yyyy-MM-dd");
  console.log(`TITAN: Convening Staff for ${dateStr}...`);

  const doc = DocumentApp.create(`TITAN COMMAND BRIEF: ${dateStr}`);
  const docFile = DriveApp.getFileById(doc.getId());

  try {
    docFile.moveTo(DriveApp.getFolderById(CONFIG.BRIEFING_FOLDER_ID));
  } catch (e) { console.warn("Folder move failed."); }

  const body = doc.getBody();
  body.insertParagraph(0, `D2M GENERAL STAFF BRIEFING | ${dateStr}`).setHeading(DocumentApp.ParagraphHeading.HEADING1);
  body.appendHorizontalRule();

  const newsContext = (typeof runWorldEventsSweep === 'function') ? runWorldEventsSweep() : "Global feed offline.";
  const opsContext = getLiveOperationalContext();

  const personaIds = ['A1','A2','A3','A4','A5','A6','A7','A8','A9','A10','A11','A12'];

  personaIds.forEach(id => {
    const persona = PERSONA_REGISTRY[id];
    console.log(`Briefing from ${persona.name}...`);

    const report = callBrain(`WAR ROOM: ${newsContext}\nOPS: ${opsContext}\nDirective: Tactical report.`, id);

    body.appendParagraph(`${persona.icon} ${id}-${persona.name.toUpperCase()}`).setHeading(DocumentApp.ParagraphHeading.HEADING2);
    body.appendParagraph(report);
  });

  const docUrl = doc.getUrl();
  GmailApp.sendEmail(CONFIG.FINANCE.SMS_GATEWAY, "", `TITAN Briefing Ready: ${docUrl}`);
  return "Briefing Complete.";
}

function getLiveOperationalContext() {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.SHEETS.ACTIVE_ID);
    const tasks = ss.getSheetByName('Tasks').getRange(2, 2, 3, 1).getValues().flat().filter(String).join(', ');
    const bookings = ss.getSheetByName('Bookings').getRange(2, 2, 3, 1).getValues().flat().filter(String).join(', ');
    return `ACTIVE TASKS: ${tasks || "None"} | RECENT BOOKINGS: ${bookings || "None"}`;
  } catch (e) { return "Ops offline."; }
}
