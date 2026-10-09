// ============================================================
// Code.gs  –  Sprint Report Web App (Server Side)
// ============================================================
// SETUP:
//   1. Open any Google Sheet → Extensions → Apps Script
//   2. Rename default file to Code.gs, paste this content
//   3. Click + → HTML file → name it exactly: Index
//   4. Paste Index.html content there
//   5. Set SHARED_FOLDER_ID below to your team's shared folder ID
//      (get it from the folder URL: drive.google.com/drive/folders/FOLDER_ID)
//   6. Make sure the folder is shared with your team
//   7. Deploy → New Deployment → Web App
//      Execute as: Me | Who has access: Anyone (or your org)
//   8. Open the Web App URL in your browser
//
// JIRA SETUP (for the optional Backlog & Grooming section):
//   a. Create an API token: https://id.atlassian.com/manage-profile/security/api-tokens
//   b. Project Settings (gear icon) → Script Properties → add:
//        JIRA_EMAIL      = your Atlassian login email
//        JIRA_API_TOKEN  = the token from step (a)
//   c. Set JIRA_BASE_URL below
//   d. Fill in JIRA_TEAM_IDS below for every team
//   e. Run testJiraConnection() once from the editor to authorise
//      external requests and confirm the counts look right
//   f. Deploy → Manage deployments → ✏️ Edit → Version: New version
//      (editing the existing deployment keeps the same Web App URL)
// ============================================================

// ── Custom Menu ─────────────────────────────────────────────
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📊 Sprint Report')
    .addItem('Open Report Generator', 'openReportGenerator')
    .addToUi();
}

function openReportGenerator() {
  // NOTE: ScriptApp.getService().getUrl() was returning a stale/incorrect
  // deployment URL, so the working URL is hardcoded here instead.
  // If you create a NEW deployment in the future, update this URL to match.
  var url = "https://script.google.com/a/macros/docusign.com/s/AKfycbxPsg354D1BwVTAaV5eh8zbaVcy8_5GGnmAVFv70iT9dQcxMg4aRcKtndxCnB5Wv0pXkg/exec";
  var html = HtmlService.createHtmlOutput(
    '<div style="font-family:Arial,sans-serif;text-align:center;padding:24px 16px;">' +
    '<p style="margin-bottom:18px;font-size:14px;color:#333;">Click below to open the Sprint Report Generator in a new tab:</p>' +
    '<a href="' + url + '" target="_blank" rel="noopener" ' +
    'style="display:inline-block;background:#0b224e;color:#fff;padding:12px 24px;' +
    'border-radius:8px;text-decoration:none;font-weight:bold;font-size:14px;">' +
    '🌐 Open Report Generator</a>' +
    '<p style="margin-top:16px;font-size:11px;color:#888;">If nothing happens, right-click the button and choose "Open link in new tab".</p>' +
    '</div>'
  )
  .setTitle('Sprint Report Generator');
  SpreadsheetApp.getUi().showSidebar(html);
}

// ── CONFIGURATION ───────────────────────────────────────────
// Replace this with your shared Google Drive folder ID.
// Find it in the folder URL: drive.google.com/drive/folders/<FOLDER_ID>
var SHARED_FOLDER_ID = "1qBO9lohEpdlLsY5ovvcOJjmYmmmmYfgm";

var DONE_STATUSES = ["done", "closed", "resolved", "complete"];

// ── JIRA CONFIGURATION ──────────────────────────────────────
// Your Jira Cloud site, no trailing slash.
var JIRA_BASE_URL = "https://YOUR-SITE.atlassian.net";

// Map each "Team Name" (exactly as it appears in the sheet) to its Jira Team ID.
// To find an ID: in Jira, filter issues by the team, then switch to JQL view —
// the ID appears as  Team = <id>
// Matching is case-insensitive and ignores extra spaces.
var JIRA_TEAM_IDS = {
  "Lead to Opportunity": "faed835f-b19e-4cb2-9d25-9bda74232d11-354"
  // "Quote to Cash":     "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx-354",
  // "Case Management":   "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx-354",
};

// Backlog = open RTB work items not in an active sprint and not Done.
// This is your JQL with the duplicated clauses merged; {TEAM_ID} is filled per team.
var BACKLOG_JQL =
  'project = RTB' +
  ' AND issuetype not in (Sub-task, Test, Initiative, Epic)' +
  ' AND (labels not in (QA_Defect, UAT_Defect) OR labels is EMPTY)' +
  ' AND (Sprint not in openSprints() OR Sprint is EMPTY)' +
  ' AND status not in (Done)' +
  ' AND Team = "{TEAM_ID}"';

// Groomed = the backlog above, narrowed to status 10006.
var GROOMED_CLAUSE = 'status = 10006';

function doGet() {
  return HtmlService.createHtmlOutputFromFile("Index")
    .setTitle("Sprint Report Generator")
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function isDone(status) {
  return DONE_STATUSES.indexOf(String(status || "").trim().toLowerCase()) !== -1;
}

// ── Open spreadsheet by ID or fall back to active ───────────
function openSheet(spreadsheetId) {
  try {
    if (spreadsheetId && spreadsheetId.trim() !== "") {
      return SpreadsheetApp.openById(spreadsheetId.trim());
    }
    return SpreadsheetApp.getActiveSpreadsheet();
  } catch(e) {
    throw new Error("Could not open spreadsheet. Check the Sheet ID and make sure it is shared with your Google account. (" + e.message + ")");
  }
}

// ── Validate Sheet ID and return spreadsheet title ──────────
function validateSheetId(spreadsheetId) {
  try {
    var ss = openSheet(spreadsheetId);
    var sheets = ss.getSheets().map(function(s) { return s.getName(); });
    return { title: ss.getName(), sheets: sheets };
  } catch(e) {
    return { error: e.message };
  }
}

// ── Get sheet tab names ─────────────────────────────────────
function getSheetNames(spreadsheetId) {
  try {
    var ss = openSheet(spreadsheetId);
    return { sheets: ss.getSheets().map(function(s) { return s.getName(); }) };
  } catch(e) {
    return { error: e.message };
  }
}

// ── Get sprints, teams, assignees for a tab ─────────────────
function getSheetMeta(spreadsheetId, sheetName) {
  try {
    var ss    = openSheet(spreadsheetId);
    var sheet = ss.getSheetByName(sheetName);
    if (!sheet) return { error: 'Tab "' + sheetName + '" not found.' };

    var data = sheet.getDataRange().getValues();
    if (data.length < 2) return { error: "Sheet appears to be empty." };

    var col = buildColMap(data[0]);
    var missing = ["Team Name","Sprint Name","Assignee"].filter(function(h){ return col[h] === undefined; });
    if (missing.length) return { error: "Missing columns: " + missing.join(", ") };

    var sprints = [], teams = [], assignees = [];
    for (var i = 1; i < data.length; i++) {
      var sprint   = str(data[i][col["Sprint Name"]]);
      var team     = str(data[i][col["Team Name"]]);
      var assignee = str(data[i][col["Assignee"]]);
      if (sprint   && sprints.indexOf(sprint)     === -1) sprints.push(sprint);
      if (team     && teams.indexOf(team)         === -1) teams.push(team);
      if (assignee && assignees.indexOf(assignee) === -1) assignees.push(assignee);
    }
    return { sprints: sprints, teams: teams, assignees: assignees };
  } catch(e) {
    return { error: e.message };
  }
}

// ── Get assignees scoped to sprint + teams ──────────────────
function getAssigneesForSelection(spreadsheetId, sheetName, sprintName, selectedTeams) {
  try {
    var ss    = openSheet(spreadsheetId);
    var sheet = ss.getSheetByName(sheetName);
    if (!sheet) return { error: 'Tab not found.' };

    var data = sheet.getDataRange().getValues();
    var col  = buildColMap(data[0]);

    var assignees = [];
    for (var i = 1; i < data.length; i++) {
      var sprint   = str(data[i][col["Sprint Name"]]);
      var team     = str(data[i][col["Team Name"]]);
      var assignee = str(data[i][col["Assignee"]]);
      if (sprint !== sprintName) continue;
      if (selectedTeams.length && selectedTeams.indexOf(team) === -1) continue;
      if (assignee && assignees.indexOf(assignee) === -1) assignees.push(assignee);
    }
    return { assignees: assignees };
  } catch(e) {
    return { error: e.message };
  }
}

// ── Generate the full HTML report ──────────────────────────
function generateReport(params) {
  // params: { spreadsheetId, sheetName, sprintName, selectedTeams,
  //           rtbPlanned, rtbActual, selectedAssignees, includeBacklog }
  try {
    var ss    = openSheet(params.spreadsheetId);
    var sheet = ss.getSheetByName(params.sheetName);
    if (!sheet) return { error: 'Tab "' + params.sheetName + '" not found.' };

    var data = sheet.getDataRange().getValues();
    var col  = buildColMap(data[0]);

    var required = ["Issue key","Summary","Team Name","Status","Story Points",
                    "Sprint Name","Business Impact","No. Of Spillovers","Spillover Reason","Assignee"];
    var missing = required.filter(function(h){ return col[h] === undefined; });
    if (missing.length) return { error: "Missing columns: " + missing.join(", ") };

    var teamData = {}, teamOrder = [];

    for (var i = 1; i < data.length; i++) {
      var row      = data[i];
      var team     = str(row[col["Team Name"]]);
      var sprint   = str(row[col["Sprint Name"]]);
      var assignee = str(row[col["Assignee"]]);

      if (sprint !== params.sprintName) continue;
      if (params.selectedTeams.length && params.selectedTeams.indexOf(team) === -1) continue;
      if (params.selectedAssignees.length && params.selectedAssignees.indexOf(assignee) === -1) continue;

      if (!teamData[team]) { teamData[team] = []; teamOrder.push(team); }
      teamData[team].push({
        issueKey:        str(row[col["Issue key"]]),
        summary:         str(row[col["Summary"]]),
        status:          str(row[col["Status"]]),
        sp:              parseFloat(row[col["Story Points"]]) || 0,
        businessImpact:  str(row[col["Business Impact"]]),
        numSpillovers:   parseFloat(row[col["No. Of Spillovers"]]) || 0,
        spilloverReason: str(row[col["Spillover Reason"]]),
        assignee:        assignee
      });
    }

    if (!teamOrder.length) return { error: "No data found for the selected filters." };

    // ── Optional: fetch backlog / groomed counts from Jira (once per team) ──
    var backlogByTeam = {}, warnings = [];
    if (params.includeBacklog) {
      teamOrder.forEach(function(team) {
        var stats = getBacklogStats(team);
        backlogByTeam[team] = stats;
        if (stats.error) warnings.push(team + ": " + stats.error);
      });
    }

    // ── Build each team's block once; reuse for preview and saved files ──
    var blocks = {};
    teamOrder.forEach(function(team) {
      var rows         = teamData[team];
      var metrics      = calcMetrics(rows);
      var deliverables = rows.filter(function(r){ return  isDone(r.status); });
      var spillovers   = rows.filter(function(r){ return !isDone(r.status); });
      blocks[team] = teamBlock(team, params.sprintName, metrics, deliverables, spillovers,
                               params.rtbPlanned, params.rtbActual,
                               params.includeBacklog ? backlogByTeam[team] : null);
    });

    // Combined preview HTML (all selected teams) — used for in-browser preview only
    var parts = [htmlHeader()];
    teamOrder.forEach(function(team) { parts.push(blocks[team]); });
    parts.push(htmlFooter());
    var html = parts.join("\n");

    // ── Save files to shared team folder ──────────────────────
    var rootFolder;
    try {
      rootFolder = DriveApp.getFolderById(SHARED_FOLDER_ID);
    } catch(e) {
      return { error: "Could not access the shared folder. Make sure SHARED_FOLDER_ID is correct and the script owner has access to it. (" + e.message + ")" };
    }

    var docUrls  = [], htmlUrls = [];

    // Process each team — save into its own subfolder
    teamOrder.forEach(function(team) {
      // Find or create a subfolder named after the team
      var teamFolder;
      var existing = rootFolder.getFoldersByName(team);
      if (existing.hasNext()) {
        teamFolder = existing.next();
      } else {
        teamFolder = rootFolder.createFolder(team);
      }

      var teamHtml  = htmlHeader() + blocks[team] + htmlFooter();
      var teamLabel = team + " – " + params.sprintName + " – " + fmtDate(new Date());

      // Save styled HTML report into the team subfolder
      var htmlFile = teamFolder.createFile(teamLabel + ".html", teamHtml, MimeType.HTML);
      try {
        htmlFile.setSharing(DriveApp.Access.DOMAIN_WITH_LINK, DriveApp.Permission.VIEW);
      } catch(shareErr) {
        Logger.log("Sharing not applied (will use folder-level permissions instead): " + shareErr.message);
      }
      htmlUrls.push(htmlFile.getUrl());

      // Create Google Doc summary and move it into the team subfolder
      var doc  = DocumentApp.create(teamLabel);
      var body = doc.getBody();
      body.clear();
      body.appendParagraph("Sprint Retrospective – " + team + " – " + params.sprintName)
          .setHeading(DocumentApp.ParagraphHeading.HEADING1);
      body.appendParagraph("Generated: " + new Date().toLocaleString()).setItalic(true);
      body.appendParagraph("");
      body.appendParagraph(
        "The styled HTML report has been saved to the team folder. " +
        "Click the link below to open it — it will render correctly in your browser."
      );
      body.appendParagraph("");
      var para = body.appendParagraph("Open Styled HTML Report");
      para.setLinkUrl(htmlFile.getUrl());
      para.setBold(true);
      para.setForegroundColor("#1155CC");
      body.appendParagraph("");
      body.appendParagraph("Members included: " + params.selectedAssignees.join(", "));
      if (params.rtbPlanned) body.appendParagraph("RTB Capacity — Planned: " + params.rtbPlanned + " | Actual: " + (params.rtbActual || "—"));
      if (params.includeBacklog) {
        var b = backlogByTeam[team];
        body.appendParagraph(b && !b.error
          ? "Backlog: " + b.backlog + " tickets | Groomed: " + b.groomed + " tickets"
          : "Backlog: unavailable (" + (b ? b.error : "no data") + ")");
      }
      doc.saveAndClose();

      // Move the Google Doc from root Drive into the team subfolder
      var docFile = DriveApp.getFileById(doc.getId());
      teamFolder.addFile(docFile);
      DriveApp.getRootFolder().removeFile(docFile);
      docUrls.push(doc.getUrl());
    });

    var teamReports = teamOrder.map(function(team, idx) {
      return { team: team, htmlUrl: htmlUrls[idx], docUrl: docUrls[idx] };
    });

    return { html: html, teamReports: teamReports, warnings: warnings,
             docUrl: docUrls[0], htmlUrl: htmlUrls[0] }; // back-compat fields

  } catch(e) {
    return { error: e.message };
  }
}

// ── Jira helpers ────────────────────────────────────────────
function lookupTeamId(teamName) {
  var wanted = String(teamName || "").trim().replace(/\s+/g, " ").toLowerCase();
  for (var k in JIRA_TEAM_IDS) {
    if (k.trim().replace(/\s+/g, " ").toLowerCase() === wanted) return JIRA_TEAM_IDS[k];
  }
  return null;
}

function getBacklogStats(teamName) {
  var teamId = lookupTeamId(teamName);
  if (!teamId) return { error: 'No Jira Team ID configured for "' + teamName + '" (add it to JIRA_TEAM_IDS)' };
  try {
    var backlogJql = BACKLOG_JQL.replace("{TEAM_ID}", teamId);
    return {
      backlog: jiraCount(backlogJql),
      groomed: jiraCount(backlogJql + " AND " + GROOMED_CLAUSE)
    };
  } catch(e) {
    return { error: e.message };
  }
}

// Exact count of issues matching a JQL query (pages through the enhanced search API).
function jiraCount(jql) {
  var props = PropertiesService.getScriptProperties();
  var email = props.getProperty("JIRA_EMAIL");
  var token = props.getProperty("JIRA_API_TOKEN");
  if (!email || !token) throw new Error("Jira credentials missing — set JIRA_EMAIL and JIRA_API_TOKEN in Script Properties");

  var headers = {
    Authorization: "Basic " + Utilities.base64Encode(email + ":" + token),
    Accept: "application/json"
  };

  var total = 0, nextPageToken = null, pages = 0;
  do {
    var payload = { jql: jql, fields: ["id"], maxResults: 100 };
    if (nextPageToken) payload.nextPageToken = nextPageToken;

    var resp = UrlFetchApp.fetch(JIRA_BASE_URL + "/rest/api/3/search/jql", {
      method: "post",
      contentType: "application/json",
      headers: headers,
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    });

    var code = resp.getResponseCode();
    if (code === 401 || code === 403) throw new Error("Jira rejected the credentials (HTTP " + code + ")");
    if (code !== 200) throw new Error("Jira returned HTTP " + code + ": " + resp.getContentText().slice(0, 200));

    var data = JSON.parse(resp.getContentText());
    total += (data.issues || []).length;
    nextPageToken = data.nextPageToken || null;
    pages++;
  } while (nextPageToken && pages < 200);

  return total;
}

// Run this once from the Apps Script editor (select it → ▶ Run) to authorise
// external requests and check every configured team.
function testJiraConnection() {
  for (var team in JIRA_TEAM_IDS) {
    var s = getBacklogStats(team);
    Logger.log(team + " → " + (s.error ? "ERROR: " + s.error : "Backlog " + s.backlog + ", Groomed " + s.groomed));
  }
}

// ── Metric helpers ──────────────────────────────────────────
function calcMetrics(rows) {
  var total=0, spilledIn=0, delivered=0, spillOut=0;
  var totalT=0, spilledInT=0, deliveredT=0, spillOutT=0;
  rows.forEach(function(r){
    total += r.sp; totalT++;
    if (r.numSpillovers > 0) { spilledIn += r.sp; spilledInT++; }
    if (isDone(r.status))    { delivered += r.sp; deliveredT++; }
    else                     { spillOut  += r.sp; spillOutT++;  }
  });
  return { totalAtStart:total, spilledOver:spilledIn,
           netNewPlanned:total-spilledIn, delivered:delivered, spillToNext:spillOut,
           tickets: {
             totalAtStart:  totalT,
             spilledOver:   spilledInT,
             netNewPlanned: totalT - spilledInT,
             delivered:     deliveredT,
             spillToNext:   spillOutT
           } };
}

function buildColMap(headers) {
  var col = {};
  headers.forEach(function(h, i){ col[String(h).trim()] = i; });
  return col;
}

function str(v){ return String(v || "").trim(); }

// ── HTML output builders ────────────────────────────────────
function esc(s){
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;")
                  .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
function fmtDate(d){ return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate()); }
function pad(n){ return n<10?"0"+n:String(n); }
function htmlHeader(){
  return '<!DOCTYPE html><html><head><meta charset="UTF-8">'
       + '<style>body{margin:0;padding:20px;background:#f3f5f8;font-family:Helvetica,Arial,sans-serif;}</style>'
       + '</head><body>';
}
function htmlFooter(){ return '</body></html>'; }

// tickets (optional): when given, a ticket-count chip is shown under the sub-label
function metricCard(label, value, sub, border, valColor, tickets){
  var ticketChip = '';
  if (tickets !== undefined && tickets !== null) {
    ticketChip = '<div style="margin-top:10px;display:inline-block;background:#f3f5f8;color:#0b224e;'
               + 'border-radius:12px;padding:4px 12px;font-size:12px;font-weight:700;">'
               + '🎫 ' + tickets + ' ticket' + (tickets === 1 ? '' : 's') + '</div>';
  }
  return '<td width="33%" align="center" style="background:#fff;border:1px solid #e1e5eb;'
       + 'border-top:4px solid '+border+';border-radius:8px;padding:20px;">'
       + '<div style="font-size:11px;font-weight:bold;color:#6b7c93;text-transform:uppercase;">'+label+'</div>'
       + '<div style="font-size:36px;font-weight:800;color:'+valColor+';margin:10px 0 5px 0;">'+(value||0)+'</div>'
       + '<div style="font-size:12px;color:#8898aa;">'+sub+'</div>'
       + ticketChip + '</td>';
}

// Backlog & Grooming section (only rendered when the UI toggle is on)
function backlogSection(b){
  var h = '<div style="font-size:18px;font-weight:700;margin-bottom:20px;">🗂️ Backlog Health</div>';
  if (!b || b.error) {
    h += '<div style="background:#fff8e6;border:1px solid #f5d98b;border-radius:8px;padding:14px 18px;'
       + 'font-size:13px;color:#856404;margin-bottom:30px;">Backlog data unavailable'
       + (b && b.error ? ' — ' + esc(b.error) : '') + '</div>';
    return h;
  }
  var pct = b.backlog > 0 ? Math.round((b.groomed / b.backlog) * 100) : 0;
  h += '<table width="100%" cellpadding="10" cellspacing="10" style="margin-left:-10px;"><tr>'
     + metricCard("Backlog",   b.backlog,  "tickets not in an open sprint", "#8e44ad", "#0b224e")
     + metricCard("Groomed",   b.groomed,  "tickets ready for planning",    "#16a085", "#16a085")
     + metricCard("Groomed %", pct + "%",  "of backlog groomed",            "#3498db", "#0b224e")
     + '</tr></table><div style="height:30px;"></div>';
  return h;
}

function teamBlock(teamName, sprintName, m, deliverables, spillovers, rtbPlanned, rtbActual, backlog){
  var pct    = m.totalAtStart>0 ? Math.round((m.delivered/m.totalAtStart)*100) : 0;
  var badgeBg= pct>=80?"#27ae60":pct>=50?"#f1c40f":"#e74c3c";
  var badgeFg= (pct>=50&&pct<80)?"#0b224e":"#fff";
  var t      = m.tickets;
  var h='';

  h += '<table width="100%" cellpadding="0" cellspacing="0" style="max-width:900px;margin:0 auto 60px auto;background:#fff;box-shadow:0 4px 15px rgba(0,0,0,.1);">';

  // Header band
  h += '<tr><td style="background:#0b224e;padding:30px 40px;">'
     + '<div style="font-size:14px;font-weight:600;letter-spacing:1px;margin-bottom:20px;color:#fff;">'
     + '<span style="font-size:20px;font-weight:800;margin-right:15px;">Docusign</span>'
     + '<span style="color:#4f6b9c;margin-right:15px;">|</span>RTB Salesforce</div>'
     + '<table cellpadding="0" cellspacing="0"><tr>'
     + '<td style="font-size:30px;background:#1a3668;padding:15px;border-radius:50%;width:40px;text-align:center;">📊</td>'
     + '<td style="padding-left:20px;color:#fff;">'
     + '<div style="font-size:11px;text-transform:uppercase;letter-spacing:1.5px;color:#a0b2d0;margin-bottom:5px;">Sprint Retrospective</div>'
     + '<h1 style="font-size:26px;margin:0 0 5px 0;">'+esc(teamName)+'</h1>'
     + '<div style="font-size:13px;color:#a0b2d0;">'+esc(sprintName)+'</div>'
     + '</td></tr></table></td></tr>';

  // Velocity bar
  h += '<tr><td style="background:#0d3273;padding:15px 40px;color:#fff;">'
     + '<table width="100%" cellpadding="0" cellspacing="0"><tr>'
     + '<td style="font-size:14px;">Sprint Velocity</td><td align="right">'
     + '<span style="font-size:18px;font-weight:bold;color:#f1c40f;">'+m.delivered
     + ' <span style="font-size:14px;font-weight:normal;color:#a0b2d0;">/ '+m.totalAtStart+' story points</span></span>&nbsp;&nbsp;&nbsp;'
     + '<span style="background:'+badgeBg+';color:'+badgeFg+';padding:6px 12px;border-radius:15px;font-size:11px;font-weight:bold;">'+pct+'% Delivered</span>'
     + '</td></tr></table></td></tr>';

  // Body
  h += '<tr><td style="padding:30px 40px;">';

  // Sprint Summary cards (story points + ticket counts)
  h += '<div style="font-size:18px;font-weight:700;margin-bottom:20px;">📋 Sprint Summary</div>'
     + '<table width="100%" cellpadding="10" cellspacing="10" style="margin-bottom:0;margin-left:-10px;"><tr>'
     + metricCard("Total at Start",  m.totalAtStart,  "story points",      "#e1e5eb","#0b224e", t.totalAtStart)
     + metricCard("Spilled Over",    m.spilledOver,   "from prev. sprint", "#e1e5eb","#0b224e", t.spilledOver)
     + metricCard("Net New Planned", m.netNewPlanned, "story points",      "#e1e5eb","#0b224e", t.netNewPlanned)
     + '</tr><tr>'
     + metricCard("Delivered",     m.delivered,   "story points","#27ae60","#27ae60", t.delivered)
     + metricCard("Spill to Next", m.spillToNext, "story points","#e67e22","#e67e22", t.spillToNext);

  // RTB Capacity card
  var rtbContent;
  if (rtbPlanned || rtbActual) {
    rtbContent = '<div style="margin-top:8px;">'
      + '<div style="font-size:15px;font-weight:700;color:#27ae60;">Planned: ' + esc(rtbPlanned||'—') + '</div>'
      + '<div style="font-size:15px;font-weight:700;color:#e67e22;margin-top:4px;">Actual: '  + esc(rtbActual||'—')  + '</div>'
      + '</div>';
  } else {
    rtbContent = '<div style="font-size:28px;font-weight:800;color:#0b224e;margin:8px 0 4px 0;">N/A</div>'
               + '<div style="font-size:12px;color:#8898aa;">not provided</div>';
  }
  h += '<td width="33%" align="center" style="background:#fff;border:1px solid #e1e5eb;border-top:4px solid #3498db;border-radius:8px;padding:20px;">'
     + '<div style="font-size:11px;font-weight:bold;color:#6b7c93;text-transform:uppercase;">RTB Capacity</div>'
     + rtbContent + '</td>'
     + '</tr></table><div style="height:30px;"></div>';

  // Backlog Health (optional)
  if (backlog) h += backlogSection(backlog);

  // Deliverables table
  h += '<div style="font-size:18px;font-weight:700;margin-bottom:20px;">📦 Key Deliverables</div>'
     + '<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:40px;font-size:13px;">'
     + '<thead><tr style="background:#0b224e;color:#fff;">'
     + '<th width="14%" style="padding:12px 15px;font-size:12px;text-transform:uppercase;text-align:left;">Issue</th>'
     + '<th width="32%" style="padding:12px 15px;font-size:12px;text-transform:uppercase;text-align:left;">Summary</th>'
     + '<th width="44%" style="padding:12px 15px;font-size:12px;text-transform:uppercase;text-align:left;">Business Impact</th>'
     + '<th width="10%" style="padding:12px 15px;font-size:12px;text-transform:uppercase;text-align:center;">SP</th>'
     + '</tr></thead><tbody>';

  if (!deliverables.length) {
    h += '<tr><td colspan="4" style="padding:20px;text-align:center;color:#8898aa;font-style:italic;">No items completed this sprint.</td></tr>';
  } else {
    var spTotal = 0;
    deliverables.forEach(function(d){
      spTotal += d.sp;
      h += '<tr style="background:#fff;">'
         + '<td style="border-bottom:1px solid #f0f2f5;padding:12px 15px;vertical-align:top;">'
         + '<span style="background:#eef2f9;color:#0b224e;padding:6px 10px;border-radius:15px;font-weight:bold;font-size:12px;white-space:nowrap;">'+esc(d.issueKey)+'</span></td>'
         + '<td style="border-bottom:1px solid #f0f2f5;padding:12px 15px;vertical-align:top;">'+esc(d.summary)+'</td>'
         + '<td style="border-bottom:1px solid #f0f2f5;padding:12px 15px;vertical-align:top;">'+(d.businessImpact?esc(d.businessImpact):'<em style="color:#aaa;">—</em>')+'</td>'
         + '<td style="border-bottom:1px solid #f0f2f5;padding:12px 15px;vertical-align:top;text-align:center;">'
         + '<div style="background:#1761d1;color:#fff;width:30px;height:30px;border-radius:50%;font-weight:bold;font-size:13px;line-height:30px;text-align:center;margin:auto;">'+d.sp+'</div></td>'
         + '</tr>';
    });
    h += '<tr style="background:#f7fdf9;border-top:2px solid #27ae60;">'
       + '<td colspan="3" style="padding:15px;color:#27ae60;font-weight:bold;font-size:14px;">Total Story Points Delivered</td>'
       + '<td style="padding:15px;text-align:center;"><div style="background:#27ae60;color:#fff;width:30px;height:30px;border-radius:50%;font-weight:bold;font-size:13px;line-height:30px;text-align:center;margin:auto;">'+spTotal+'</div></td>'
       + '</tr>';
  }
  h += '</tbody></table>';

  // Spillover table
  h += '<div style="font-size:18px;font-weight:700;margin-bottom:20px;">⚠️ Spillover Items</div>'
     + '<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:13px;">'
     + '<thead><tr style="background:#8b4513;color:#fff;">'
     + '<th width="14%" style="padding:12px 15px;font-size:12px;text-transform:uppercase;text-align:left;">Issue</th>'
     + '<th width="40%" style="padding:12px 15px;font-size:12px;text-transform:uppercase;text-align:left;">Summary</th>'
     + '<th width="20%" style="padding:12px 15px;font-size:12px;text-transform:uppercase;text-align:left;">Status</th>'
     + '<th width="26%" style="padding:12px 15px;font-size:12px;text-transform:uppercase;text-align:left;">Spillover Reason</th>'
     + '</tr></thead><tbody>';

  if (!spillovers.length) {
    h += '<tr><td colspan="4" style="padding:20px;text-align:center;color:#8898aa;font-style:italic;">No spillover items — full sprint delivered! 🎉</td></tr>';
  } else {
    spillovers.forEach(function(s){
      h += '<tr style="background:#fff;">'
         + '<td style="border-bottom:1px solid #f0f2f5;padding:12px 15px;vertical-align:top;">'
         + '<span style="background:#fff0e6;color:#b35900;padding:6px 10px;border-radius:15px;font-weight:bold;font-size:12px;white-space:nowrap;">'+esc(s.issueKey)+'</span></td>'
         + '<td style="border-bottom:1px solid #f0f2f5;padding:12px 15px;vertical-align:top;">'+esc(s.summary)+'</td>'
         + '<td style="border-bottom:1px solid #f0f2f5;padding:12px 15px;vertical-align:top;">'
         + '<span style="background:#fff3cd;color:#856404;padding:4px 8px;border-radius:4px;font-size:12px;font-weight:bold;">'+esc(s.status)+'</span></td>'
         + '<td style="border-bottom:1px solid #f0f2f5;padding:12px 15px;vertical-align:top;">'
         + '<span style="color:#d35400;font-weight:bold;background:#fff5f0;padding:4px 8px;border-radius:4px;">'+(s.spilloverReason||"Not Provided")+'</span></td>'
         + '</tr>';
    });
  }
  h += '</tbody></table>';

  h += '</td></tr>';
  h += '<tr><td style="background:#f3f5f8;padding:20px;text-align:center;font-size:11px;color:#8898aa;border-top:1px solid #e1e5eb;">'
     + 'Jade Global &bull; RTB Managed Services &bull; Confidential &amp; Intended for Docusign Leadership Only'
     + '</td></tr></table>';
  return h;
}
