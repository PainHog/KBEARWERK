# KBEARWERK — Requirements & Roadmap

A beginner-friendly, multi-panel **Windows desktop app** to reduce the workload and
stress of an office administrator at a structural engineering firm. One place to
run every part of the job, find anything instantly, and keep track of what's
missing, outstanding and done. Installed app (a real `.exe`), **not** a script.

Status legend: ✅ built (scaffold; will be tailored to her real files) · 🟡 partial · ⬜ to do.

## Guiding principles
- **Enter data once**, and it files itself everywhere.
- **Find anything fast** — search her lists *and* every folder/file on the drive.
- **Reduce stress** — see what's done; never panic-search; never lose work.
- **Sensitive data stays local**; logins in Windows Credential Manager.
- **Never overwrite** — spreadsheet writes go to the next empty row.
- **Never lose work** — cloud desync saves locally and syncs when it's back.

## Features
| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 1 | App shell: multi-panel window, sidebar, theme | ✅ | 13 tabs, looks like a real app |
| 2 | Config/settings engine (local, secure) | ✅ | `%APPDATA%\KBEARWERK\config.json` |
| 3 | **Global search** — jobs from lists **+ every folder/file on disk** | ✅ | "type Callahan, open the folder/file" |
| 4 | **New Project** — enter once, fan out everywhere | ✅ | folder + 3 Excel lists + info sheet + open Monograph/OCE |
| 5 | **Documents** generator (fill blank templates) | ✅ | auto-detects `{{fields}}`; saves to many places |
| 6 | **Job workspace** — open a job & act on it | ✅ | scan missing, generate letter → Correspondence, missing-fields report |
| 7 | Project List searchable table | ✅ | open selected job's folder |
| 8 | Redlines — file, email drafter, update 2 lists, mark done | ✅ | Outlook send/draft + activity log |
| 9 | Boss's Inbox monitor (Outlook, local) | ✅ | flags urgent / client / RFP |
| 10 | **Site Inspection Sheet** (client info auto-fills) | ✅ | mileage/hours/actual date + approved-for-city-letter |
| 11 | Needed / missing-docs tracker + printable sheet | ✅ | auto-scans folder; prints "Outstanding Items" |
| 12 | Billing ledger (contract vs billed vs remaining) | ✅ (local) | wire to her real billing sheets next |
| 13 | Weekly meeting checklist | ✅ | |
| 14 | Office schedule / calendar | 🟡 | reminders + Outlook shortcut; tailor to her real calendar |
| 15 | Settings (paths, people, seals, email, URLs, sync) | ✅ | |
| 16 | Excel: next-empty-row append, update-by-# | ✅ | never overwrites old data |
| 17 | Cloud-desync resilience (local outbox + auto-sync) | ✅ | pending indicator + Sync now |
| 18 | Complex inspection Excel (dropdowns/checkboxes/tabs/macros) | ✅ | edits through Excel itself (COM) |
| 19 | Secure credential storage | ✅ | keyring / Credential Manager |
| 20 | OCE **localhost** print-tracking | 🟡 | open + paste now; auto-post to local endpoint later |
| 21 | Packaging: one-click `.exe` + GitHub Actions build | ✅ | Actions builds `KBEARWERK.exe` per push |
| 22 | Validate, document, commit & push | ✅ | engine unit-tested (14 tests) |
| 23 | Missing-fields report (per document, red MISSING) | ✅ | non-blocking |
| 24 | Drag-and-drop document import + auto-extract | ✅ | drop a proposal → fields fill (heuristic; tune to her format) |
| 25 | Accomplishments view (today/this week) | ✅ | jobs created, emails sent, redlines, docs… |
| 26 | City letters: draft → review → **Seal & Save** | ✅ | applies engineer signature + seal images |
| 27 | Contacts by **nickname** (email hidden) | ✅ | pick "Carl"/"Ian", not the address |
| 28 | Per-job **pull-list** (carry-over data) | ✅ | everything typed is remembered & pre-fills |
| 29 | Activity log (proof a task was done) | ✅ | powers Home's recent activity + counts |
| 30 | Search-as-launcher (find & Generate a document) | ✅ | type "CD Sheet" → Generate, no workflow |
| 31 | Financials dashboard + invoicing + move-to-ledger | ✅ | held fund, month (per engineer), year; draft invoices |
| 32 | Sync-status visibility (✓ / ☁ / ⏳) | ✅ | reads cloud file attributes; shown on Home |
| 33 | Convert document → PDF | ✅ | Word/LibreOffice; "Also save a PDF" + standalone |
| 34 | Dark mode by default + theme-aware tables | ✅ | no white glare; light/system available |
| 35 | Collapsible sections (declutter primitive) | 🟡 | built; apply per-panel with her input |
| 36 | Color menu (text hex) + draw-on-screen mode | ✅ | pencil/marker, click clears & exits, input blocked |
| 37 | Headless GUI audit (every panel, under Xvfb) | ✅ | 23 GUI checks + 15 engine tests green |

## What we still need from her (to make it precise)
- The real **folder template** (exact sub-folder names under a job).
- Copies (blank/redacted OK) of: **Proposal List**, **Project List**, **Weekly
  Worksheet**, the **two redline lists**, the **inspection workbook**, and any
  **billing sheet** — so columns/tabs match exactly.
- Her blank **document/letter templates** (city letters, transmittals, the site
  inspection sheet, the Project Information Sheet) to load into the library and to
  add `{{ field }}`, `{{ signature }}`, `{{ seal }}`, `{{ draft_notice }}` tags.
- A sample **proposal** so the drag-and-drop extractor can be tuned to their layout.
- The **engineer signature + seal** images.
- The **OCE localhost** address (e.g. `http://localhost:8080/...`).
- The exact **project folder naming** convention.
- How she keeps the **office schedule/calendar**.
- The **boss's mailbox** name as it appears in her Outlook.

## Delivery
- Python + CustomTkinter GUI; runs on her Windows PC.
- GitHub Actions compiles a downloadable **`KBEARWERK.exe`** on every push (Actions
  tab → latest run → Artifacts). No scripts, no setup.
