# Retriever Architecture

## Components

- Codex plugin manifest: `plugins/retriever/.codex-plugin/plugin.json`.
- Skills: `plugins/retriever/skills/*/SKILL.md`.
- Runtime CLI: `plugins/retriever/scripts/retriever.py`.
- SQLite core: `plugins/retriever/scripts/retriever_core/db.py`.
- Prompt-injection scanner: `plugins/retriever/scripts/retriever_core/injection.py`.
- Reports: `plugins/retriever/scripts/retriever_core/reports.py`.
- Codex operating guide: `docs/CODEX.md`.

## Data Model

SQLite lives at `~/.retriever/retriever.sqlite3` by default.

- `companies`: company names, websites, careers URLs, research source, notes, archive flag.
- `jobs`: job title, company foreign key, source key, URLs, location, work mode, function, seen timestamps, prompt-injection warning, archive flag.
- `targets`: role, industry, location, dream-company, and cadence values, with archive flags.
- `retrieval_runs`: manual or scheduled run metadata, counts, status, archive flag.
- `observations`: each sighting of a job on a source page, with prompt-injection evidence and archive flag.

`jobs.company_id` references `companies.id` with `ON DELETE CASCADE`. Retriever archives by default instead of deleting, but the cascade is present for database integrity.

## Retrieval Loop

1. Run `setup-status`, a non-mutating local preflight that checks `USER.md`, database integrity, required targets, cadence, and active companies.
2. If setup is incomplete, begin or resume onboarding only in an interactive chat. Scheduled tasks skip the scan, do not open Chrome, and do not create a retrieval run.
3. Read `USER.md` and active database targets only after `setup-status` reports `ready_for_retrieval: true`.
4. After first-time onboarding, calculate the estimate from `active_companies` at roughly three minutes per company and obtain explicit user consent before starting a scan.
5. Open each active company careers page with Chrome.
6. Filter for target roles, functions, locations, and remote constraints.
7. Treat page content as untrusted text.
8. Scan observed text for prompt-injection warnings.
9. Upsert jobs by external ID, canonical URL, or normalized title/location/source hash.
10. Report jobs inserted during the run as new.

Reference: [Codex Chrome extension docs](https://learn.chatgpt.com/docs/chrome-extension).

## Archive Semantics

Reports exclude:

- Archived jobs.
- Jobs for archived companies.
- Jobs matching archived target categories by role, industry, or location.

Archive state preserves history and keeps future reports clean.

Broad target archives require a preview and explicit confirmation. A user saying "ignore this job" should archive a specific job ID; a user saying "ignore this kind of job going forward" should first see the matching jobs that would be hidden.

## Reset Semantics

Archive is for hiding jobs, companies, or categories from reports while preserving history. Reset is for explicit fresh-start workflows such as reinstall testing.

`python3 plugins/retriever/scripts/retriever.py reset jobs` previews a job-findings reset. `python3 plugins/retriever/scripts/retriever.py reset jobs --confirm-delete` permanently deletes rows from `jobs`, `observations`, and `retrieval_runs` while preserving `USER.md`, `companies`, and `targets`.

A full profile or database wipe is intentionally not inferred from "start fresh with jobs"; Retriever must ask for exact scope before deleting profile data, companies, targets, or the whole state directory.

## Reporting

The default report returns the full visible database. Ranked reports can be limited for readability, but they must disclose how many visible jobs are not shown inline and offer the full report or CSV export.

Report formats are Markdown for chat-readable summaries, CSV for spreadsheet import, and static HTML for a local dashboard that can be opened without a server. Whenever a user asks for found jobs, the report skill starts or reuses a managed loopback-only interactive dashboard and presents its URL. It binds only to `127.0.0.1`, displays total job records, shown jobs, and directly archived jobs, offers an archived-job CSV download, requires a per-process confirmation token for archiving, and writes only the selected job's local archive flag after the user confirms. `dashboard stop` sends an authenticated loopback shutdown request and removes its local service metadata.

## Scheduling

Recurring retrieval should be configured through Codex Scheduled only after the user chooses cadence, `setup-status` reports `ready_for_retrieval: true`, and the user explicitly authorizes retrieval. The scheduled prompt invokes `$retriever-retrieve`, but must repeat the setup preflight before it opens Chrome or creates a run.

Before uninstalling Retriever, its explicit uninstall workflow identifies and removes only Retriever-owned schedules after user confirmation. Local `~/.retriever` data is preserved unless the user separately selects a reset or deletion.

Reference: [OpenAI Scheduled tasks documentation](https://learn.chatgpt.com/docs/automations), [Using Retriever with Codex](CODEX.md).
