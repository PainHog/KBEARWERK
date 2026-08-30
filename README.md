# KBEARWERK — Office Assistant

A friendly, all-in-one **Windows desktop app** that handles the day-to-day work of
an office administrator at a structural engineering firm — so the job is faster,
calmer, and nothing slips.

It's a real app with a window and tabs, **not** a script. Enter information once,
and it files it everywhere it needs to go.

---

## What it does (at a glance)

- **Home** — a big "find any job" search (by address, client, contractor, number),
  plus a *"look what you got done today"* summary and recent activity.
- **Open a Job** — pull up one job and act on it: open its folder, scan for missing
  data, generate a letter into its Correspondence folder.
- **New Project** — accept a proposal and, from one form (or a dropped proposal
  file), create the folder, update the Proposal List / Weekly Worksheet / Project
  List, and generate the Project Information Sheet.
- **Documents** — fill any blank template in-app and save copies everywhere at once.
- **Redlines** — file a scanned redline, email the right drafter, update the two
  lists, and mark it done.
- **Boss's Inbox** — watch the supervisor's mailbox for urgent / client / RFP mail.
- **Observations / Inspections** — a site inspection sheet that pulls client info
  from the job; when approved for a city letter, draft → review → **Seal & Save**
  with the engineer's signature and seal.
- **Needed** — scan a job's folder for missing documents/info and print an
  outstanding-items sheet for the weekly meeting.
- **Billing** — track each contract vs. what's billed vs. what's remaining.
- **Meeting Checklist**, **Schedule**, and **Settings**.

## Principles it's built on

- **Enter once, carry over.** Everything typed for a job is remembered and pre-fills
  future sheets.
- **Never lose work.** If a cloud file/folder is disconnected, the app saves locally
  and syncs when it's back.
- **Never overwrite.** Spreadsheet entries always go to the next empty row.
- **Stays local & private.** Sensitive data never leaves the PC; logins use Windows
  Credential Manager.
- **Preserves complex Excel.** Inspection workbooks are edited through Excel itself,
  so dropdowns, checkboxes, tabs and macros survive.

---

## For the user: how to get the app

You don't build anything. Every time the app is updated, GitHub automatically
compiles a fresh **`KBEARWERK.exe`**:

1. Open the **Actions** tab of this repository.
2. Click the most recent **"Build Windows app"** run.
3. Download the **`KBEARWERK-windows`** artifact and unzip it.
4. Double-click **`KBEARWERK.exe`**. (Windows SmartScreen may warn about an unknown
   publisher the first time — choose *More info → Run anyway*.)

First launch: open **Settings** and point the app at the work folder and the real
spreadsheets, and add people/contacts. Then everything else lights up.

---

## For developers

```bash
python -m venv .venv
. .venv/Scripts/activate      # Windows
pip install -r requirements.txt
python main.py                # run the app
python -m pytest -q tests     # run the engine tests
```

- The **service layer** (`kbearwerk/services/`) has no GUI dependency and is unit
  tested; it runs on any OS.
- The **GUI** (`kbearwerk/panels/`, `kbearwerk/app.py`) uses CustomTkinter and runs
  on Windows (Outlook + Excel-COM features are Windows-only and degrade gracefully
  elsewhere for development).

See **[ROADMAP.md](ROADMAP.md)** for the full requirements checklist and what still
needs her real files to finish.
