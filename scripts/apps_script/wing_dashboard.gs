/**
 * wing_dashboard.gs — Google Apps Script for Thunderbird Wing Dashboard
 *
 * HOW TO DEPLOY:
 * 1. Open the Booking Master sheet in Google Sheets
 * 2. Extensions → Apps Script
 * 3. Paste this entire file into the editor (replace default code)
 * 4. Click Save, then Run → onOpen (grant permissions when prompted)
 * 5. To enable hourly auto-format: Run → createHourlyTrigger() once
 *
 * After deploy, you'll see a "🦅 Wing Ops" menu in the Sheets toolbar.
 * The Wing_Dashboard tab is written by Python (sheets_wing_sync.py).
 * This script adds formatting, navigation shortcuts, and auto-refresh color coding.
 *
 * Thunderbird Wing · Dreams2Memories Travel, LLC · 2026-06-19
 */

var DASHBOARD_TAB = "Wing_Dashboard";
var FARE_LOG_TAB = "Fare Log";
var ACTION_TRACKER_TAB = "Action_Tracker";
var BOOKING_MASTER_TAB = "Booking Master";

// ─────────────────────────────────────────── menu

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("🦅 Wing Ops")
    .addItem("📊 Go to Dashboard", "goToDashboard")
    .addItem("✈️ Go to Fare Log", "goToFareLog")
    .addItem("🎯 Go to Action Tracker", "goToActionTracker")
    .addSeparator()
    .addItem("🎨 Format Dashboard", "formatDashboard")
    .addItem("📌 Highlight P0 Missions", "highlightP0Missions")
    .addSeparator()
    .addItem("⏰ Enable Hourly Auto-Format", "createHourlyTrigger")
    .addItem("🗑️ Remove Auto-Format Trigger", "removeTriggers")
    .addSeparator()
    .addItem("ℹ️ About Wing Ops", "showAbout")
    .addToUi();
}

// ─────────────────────────────────────────── navigation

function goToDashboard() {
  _activateTab(DASHBOARD_TAB);
}

function goToFareLog() {
  _activateTab(FARE_LOG_TAB);
}

function goToActionTracker() {
  _activateTab(ACTION_TRACKER_TAB);
}

function _activateTab(name) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(name);
  if (sh) {
    ss.setActiveSheet(sh);
    sh.activate();
  } else {
    SpreadsheetApp.getUi().alert("Tab not found: " + name + "\nRun Python sheets_wing_sync.py first.");
  }
}

// ─────────────────────────────────────────── formatting

function formatDashboard() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(DASHBOARD_TAB);
  if (!sh) {
    SpreadsheetApp.getUi().alert("Wing_Dashboard tab not found. Run Python sync first.");
    return;
  }

  var data = sh.getDataRange().getValues();
  var numRows = data.length;

  // Reset all formatting first
  sh.getDataRange().setBackground(null).setFontColor(null).setFontWeight("normal");

  for (var i = 0; i < numRows; i++) {
    var row = data[i];
    var rowRange = sh.getRange(i + 1, 1, 1, sh.getLastColumn());
    var cell0 = String(row[0]);

    // Section headers (emoji-prefixed)
    if (cell0.match(/^[📊🤖🎯✈️🔧]/)) {
      rowRange.setBackground("#003087").setFontColor("#ffffff").setFontWeight("bold");
      continue;
    }

    // Main header row
    if (cell0 === "🦅 THUNDERBIRD WING DASHBOARD") {
      rowRange.setBackground("#f7f3ea").setFontColor("#003087").setFontWeight("bold")
               .setFontSize(13);
      continue;
    }

    // Bot health rows — color by status in column B
    var status = String(row[1]);
    if (status === "GREEN") {
      rowRange.setBackground("#d9ead3");
    } else if (status === "YELLOW") {
      rowRange.setBackground("#fff2cc");
    } else if (status === "RED") {
      rowRange.setBackground("#f4cccc");
    }

    // P0 missions
    if (String(row[1]) === "P0") {
      rowRange.setBackground("#f4cccc").setFontWeight("bold");
    }
    if (String(row[1]) === "P1") {
      rowRange.setBackground("#fff2cc");
    }
  }

  // Auto-resize columns A-H
  for (var col = 1; col <= 8; col++) {
    sh.autoResizeColumn(col);
  }

  // Freeze first 2 rows
  sh.setFrozenRows(2);

  SpreadsheetApp.getActiveSpreadsheet().toast("Dashboard formatted ✓", "🦅 Wing Ops", 3);
}

function highlightP0Missions() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(ACTION_TRACKER_TAB);
  if (!sh) return;

  var data = sh.getDataRange().getValues();
  for (var i = 1; i < data.length; i++) {
    var priority = String(data[i][3]);
    var range = sh.getRange(i + 1, 1, 1, sh.getLastColumn());
    if (priority === "P0") {
      range.setBackground("#f4cccc").setFontWeight("bold");
    } else if (priority === "P1") {
      range.setBackground("#fff2cc");
    }
  }
  SpreadsheetApp.getActiveSpreadsheet().toast("P0/P1 missions highlighted ✓", "🦅 Wing Ops", 3);
}

// ─────────────────────────────────────────── triggers

function createHourlyTrigger() {
  removeTriggers(); // clean slate
  ScriptApp.newTrigger("formatDashboard")
    .timeBased()
    .everyHours(1)
    .create();
  SpreadsheetApp.getUi().alert(
    "Hourly auto-format enabled.\n\n" +
    "Note: This formats the dashboard. Data refresh requires Python sheets_wing_sync.py " +
    "to run (via backup_bot or manually)."
  );
}

function removeTriggers() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    ScriptApp.deleteTrigger(triggers[i]);
  }
}

// ─────────────────────────────────────────── about

function showAbout() {
  var ui = SpreadsheetApp.getUi();
  ui.alert(
    "🦅 Thunderbird Wing Ops",
    "Dreams2Memories Travel, LLC\n" +
    "Commander: John 'Yoda' Loucks\n" +
    "COS: Victoria 'Victory' Hale, SES-6\n\n" +
    "Data sync: Python scripts/sheets_wing_sync.py\n" +
    "Sheet: Booking Master (1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU)\n\n" +
    "Dashboard tab written by Python every ~12h via backup_bot.\n" +
    "Apps Script adds formatting, menu, and hourly color refresh.\n\n" +
    "Wing Ops v1.0 · 2026-06-19",
    ui.ButtonSet.OK
  );
}

// ─────────────────────────────────────────── utilities (callable from Python via Sheets API)

/**
 * appendWingAlert — appends a row to the Commander_Log tab.
 * Not called directly from Apps Script; included so Sheets API callers can invoke it.
 */
function appendWingAlert(timestamp, category, message) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName("Commander_Log");
  if (!sh) return;
  sh.appendRow([timestamp, category, message]);
}
