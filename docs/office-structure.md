# Office structure — real-file mapping (HFSE / HurleyFREY)

Captured from the real files she shared (read locally; the files themselves stay
in the git-ignored `samples/` and are never committed). This is the **schema**
we wire the app to — tab names, header rows, columns, dropdown options, and the
naming convention. No client rows or dollar amounts are stored here.

Firm letterhead constants (entered in Settings, not hard-coded): HurleyFREY,
3111 Sackett St. Suite 200, Houston, TX 77098 · billing email on invoices.
Principals who sign: **Chip**, **Brian** (Brian Frey, P.E.).

## Key realities that change the build
1. **Headers are not always on row 1.** Several sheets have a title/summary or
   date banner above the real header row. The Excel engine must take a
   per-sheet **header row** and **data-start row** (and auto-detect as a fallback).
2. **Multi-tab files.** Billing = 12 month tabs; Weekly = 3 tabs. Config targets
   a specific tab (and "current month" for billing).
3. **Held invoices live in the Billing sheet**, not the ledger — the status
   column reads e.g. `HOLD (CHIP)` (held + the P.M.'s nickname in parens).
4. **Job # is the primary key** everywhere, format `YYMMDD` + letter (e.g.
   `260114A`). Project folders are `Job # - Job Name`.

## Files

### 2026_Ledger.xlsx  → Invoice Ledger / Financials
- Tab: **`HFSE`**. Row 1 = title + running totals (`YTD Billed=`, `Collected=`).
  **Header row = 2**, blank row 3, **data starts row 4**.
- Columns: `Date, Client, Invoice #, Job #, Job Name, Billed, Paid, Payment Received, (blank), Notes`.
- Financials: `YTD Billed` and `Collected` are maintained on row 1; we can read
  them directly or recompute (Billed = year billed; Paid/Collected = received).

### 2026_Billing_Sheets.xlsx  → monthly billing collection + Held Invoices
- Tabs: **January … December** (12). Header row = 1.
- Columns: `Date, Job #, Job Name, Source, Fee, Prints, Invoice Amount, P.M, Notes, Invoice #, Status`.
- `Source` dropdown: `Verbal, Email, Time Sheet, Inspection Sheet, Invoice Sheet, Completed W.W.`
- `Status` (last col): `DONE` or `HOLD (nickname)` → **Held Invoices** reads this.
- Flow: engineers' work lands here monthly → reconciled → moved to Ledger → invoice generated.

### New_Weekly_Worksheet.xlsx  → live job tracker ("Project List"/Weekly)
- Tabs: **`Project Status`** (active), **`Completed`**, **`Hold`**.
- Project Status / Completed: row 1 = `DATE:` banner + group labels, **header row = 2**, **data row 3+**.
  Columns: `Project Name, Project #, Client, Due Date, Fee, Eng, Dr, Status, Priority, [Chip, Brian, Harry, Carl, Regina, Josh], to Client (Sent), Notes` (+ Completed adds `Billed, Inv #`).
- Hold tab: header row = 1, columns `Project Name, Project #, Client, Due Date, Fee, Eng, Dr, Status, Priority, Notes`.
- Dropdowns: `Eng` = `Ch, Br, Ch/Br`; `Dr` = `H, C, R, J, T, N/A`;
  `Status` = `Chip, Brian, Chip/Brian, Carl, Harry, Regina, Josh, Client, Completed`;
  `Priority` = `High, Medium, Low, CA/Obs`.

### 2026_Observations.xlsx  → Site Inspection / Observations
- Tab: **`HFSE`**, header row = 1.
- Columns: `Invoice #, Project #, Contact, Client, Project Name, Street Address, Permit,
  Inspection Type, Date(s), Fnd / Piers, C&G, Liftoff, Total Obs. Hours, Total Obs. Fee,
  Letter, Total Eng., Complete Total, [Letter status], [Inspector]`.
- Inspector seen: **Ian**. `Letter` = city-letter hours/flag; trailing cols hold
  letter "done" + inspector name.

### PI_Template.docx  → Project Information (the "enter once" master)
Rich intake form (9 tables). Sections:
- **Client info** table: Project Name, Address, Architect, Contact, Contract Signer,
  Bill To, Billing Address, Billing Email.
- **Status** (checkboxes): mktg / prelim / active / hold / work hold / billing hold.
- **Client type**, **Project type**, **Form of proposal**, **Expenses/Reimbursables** (checkbox grids).
- **Phases** SD / DD / CD / CA / BID / OTHER, each with **Scope of project** checkboxes.
- **Deliverables** (checkboxes), **Limits of Liability**, **Description**.
- **Fee Distribution** table: Description, % Distribution, Contract Amount, Hours
  (rows Total, SD, DD, CD, CA (Shop Drawings), OTHER/SITE VISITS).
- **Invoice schedule** table: Inv #, Date, DD, CD, CA, TC, Exp, Total, Notes.

### Invoice templates (CD … After First, per engineer)
- `Invoice_CD_Brian_AfterFirst.docx`, `Invoice_CD_Chip_AfterFirst.docx` (per-principal).
- Letterhead + `Dear <contact>, <date>`, phase fee breakdown (SD/DD/CD/CA = % of total),
  Previously Invoiced, This Invoice, Total due, payment options, signer block, header
  table `<client>  Invoice #<n> Project #<job>`.
- Matrix: **engineer (Brian/Chip) × phase × first / after-first** — more variants to come.

## App wiring plan (per panel)
- **Project List / Weekly** → read `New_Weekly_Worksheet.xlsx` `Project Status`
  (header row 2); New Project appends there; "Hold"/"Completed" tabs feed filters.
- **Financials** → `2026_Ledger.xlsx` (header row 2) for billed/paid/collected;
  per-engineer via P.M.
- **Held Invoices** → `2026_Billing_Sheets.xlsx` current-month tab, `Status` col.
- **Observations** → `2026_Observations.xlsx` columns above; inspector = Ian.
- **New Project / Documents** → PI template with `{{ }}` tags added per field.
- **Invoices** → pick engineer + phase template, fill fee math, save to job folder.

## Engine changes required
- `excel.read_rows` / `append_row`: accept `header_row` and `data_start_row`
  (auto-detect when unset); keep "next empty row" + "update by key" behavior.
- Config: per-file `{path, sheet, header_row}`; billing "current month tab".
- People & dropdowns seeded from the real values above (editable in Settings).
