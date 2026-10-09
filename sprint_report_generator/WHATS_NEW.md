# Sprint Report Generator: What's New

Oct 9, 2026 · @Akash Biswas

The Sprint Report Generator has two new features: ticket counts next to story points on every Sprint Summary card, and an optional Backlog Health section pulled live from Jira. Nothing else about generating a report has changed; the backlog section is off unless you switch it on.

## Ticket counts on Sprint Summary

Each Sprint Summary card now shows how many tickets sit behind its story points, as a small "🎫 N tickets" tag under the number. This makes it easy to spot sprints where a few large tickets or many small ones drive the total.

| Card | Story points | Ticket count |
| --- | --- | --- |
| Total at Start | All points in the sprint | All tickets in the sprint |
| Spilled Over | Points on tickets carried in from a previous sprint | Tickets with No. Of Spillovers above 0 |
| Net New Planned | Total at Start minus Spilled Over | Total tickets minus spilled-over tickets |
| Delivered | Points on tickets in a done status | Tickets in Done, Closed, Resolved or Complete |
| Spill to Next | Points on tickets not yet done | Tickets not yet done |

Counts follow the same filters as the points: the selected sprint, teams and members. No extra setup is needed.

## Backlog Health (optional)

When switched on, each team's report gets a Backlog Health section between Sprint Summary and Key Deliverables. The numbers come live from Jira at the moment you generate, so they reflect the backlog as it stands that day.

| Card | What it counts |
| --- | --- |
| Backlog | Open RTB tickets for the team in status 10006 that are not in an active sprint |
| Groomed | Backlog tickets that also carry the label RTB-Groomed |
| Groomed % | Groomed ÷ Backlog |

Backlog excludes Sub-tasks, Tests, Initiatives, Epics, Done tickets, and anything labelled QA\_Defect or UAT\_Defect. Each team is matched to its Jira Team by name, so a team that hasn't been mapped yet shows "Backlog data unavailable" instead of numbers.

The linked Google Doc for each team also gets a one-line backlog and groomed summary.

## How to use it

Open the generator from the sheet menu **📊 Sprint Report → Open Report Generator**, or from the web app link, then:

1. **Choose a spreadsheet.** Leave the ID blank to use the attached sheet, or paste another Sheet ID and click Load.
2. **Select the sheet tab** that holds the sprint data.
3. **Select the sprint.**
4. **Select one or more teams.**
5. **Enter RTB capacity** (optional), then click Confirm & Continue.
6. **Review team members.** Everyone is selected; deselect anyone whose tickets should be left out.
7. **Generate.**
   1. To add Backlog Health, switch on **Include Backlog & Grooming section**. A purple "Backlog section on" pill confirms it.
   2. Click **⚡ Generate Report**. With the toggle on, it takes a few seconds longer while it queries Jira.
   3. Open each team's **HTML Report** or **Google Doc**, or use **Preview combined report** to check them all at once.

Ticket counts appear automatically; the toggle only controls the Backlog Health section. Reports are saved to each team's subfolder in the shared Drive folder as before.

## Troubleshooting

If Jira can't be reached for a team, the report still generates. That team's Backlog Health shows "unavailable", and a yellow warning on the generator page lists which teams failed and why.

| What you see | What to do |
| --- | --- |
| No Jira Team ID configured for a team | Ask the tool owner to add that team's Jira Team ID |
| Jira rejected the credentials (HTTP 401 or 403) | The Jira API token has expired or was revoked; the tool owner renews it |
| Backlog or Groomed looks wrong | Run the backlog JQL in Jira for that team and compare; report the difference to the tool owner |
| Report takes longer than usual | Expected with the toggle on; switch it off if you don't need backlog numbers |

Questions or requests go to the tool owner, @Akash Biswas.
