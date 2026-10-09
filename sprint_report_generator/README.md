# Sprint Report Generator

A Google Apps Script web app that turns sprint data in a Google Sheet into a
styled, per-team sprint retrospective report. Each team's report is saved to a
shared Google Drive folder as an HTML file, with a companion Google Doc that
links to it.

## Files

- `Code.gs` — server side: reads the sheet, calculates metrics, queries Jira
  for backlog counts, builds the HTML and saves files to Drive.
- `Index.html` — the 7-step wizard UI (spreadsheet → tab → sprint → teams →
  RTB capacity → members → generate).

## What the report shows

- **Sprint Summary** — Total at Start, Spilled Over, Net New Planned,
  Delivered and Spill to Next, each as story points **and** ticket count,
  plus RTB Capacity (planned / actual).
- **Backlog Health** *(optional, toggle in Step 7)* — Backlog tickets,
  Groomed tickets and Groomed %, pulled live from Jira per team.
- **Key Deliverables** — completed items with business impact and points.
- **Spillover Items** — unfinished items with status and spillover reason.

## Required sheet columns

`Issue key`, `Summary`, `Team Name`, `Status`, `Story Points`, `Sprint Name`,
`Business Impact`, `No. Of Spillovers`, `Spillover Reason`, `Assignee`

## Setup

1. Open a Google Sheet → **Extensions → Apps Script**.
2. Paste `Code.gs` into the default script file.
3. Add an HTML file named exactly `Index` and paste `Index.html` into it.
4. Set `SHARED_FOLDER_ID` in `Code.gs` to your shared Drive folder ID.
5. **Deploy → New deployment → Web app** (Execute as: Me).
6. Update the hardcoded URL in `openReportGenerator()` to your deployment URL.

### Jira (for the Backlog Health section)

1. Create an Atlassian API token.
2. **Project Settings → Script Properties**: add `JIRA_EMAIL` and
   `JIRA_API_TOKEN`. Never put the token in the code.
3. Set `JIRA_BASE_URL` and fill in `JIRA_TEAM_IDS` (sheet team name → Jira
   Team ID) in `Code.gs`.
4. Run `testJiraConnection()` once from the editor to authorise external
   requests and check the counts.
5. **Deploy → Manage deployments → Edit → New version** to keep the same URL.

**Backlog** = open RTB items in `status = 10006` (excluding Sub-task, Test,
Initiative, Epic and QA/UAT defects) not in an active sprint.
**Groomed** = the same set with `labels = "RTB-Groomed"`. Adjust `BACKLOG_JQL` /
`GROOMED_CLAUSE` in `Code.gs` if your workflow differs.
