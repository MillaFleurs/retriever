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

An explicit job archive is a durable local CRM decision. Later scans update the matching job's `last_seen_at` value and add an observation, but they never unarchive it. Only an explicit future restore feature may change that decision.

## Reset Semantics

Archive is for hiding jobs, companies, or categories from reports while preserving history. Reset is for explicit fresh-start workflows such as reinstall testing.

`python3 plugins/retriever/scripts/retriever.py reset jobs` previews a job-findings reset. `python3 plugins/retriever/scripts/retriever.py reset jobs --confirm-delete` permanently deletes rows from `jobs`, `observations`, and `retrieval_runs` while preserving `USER.md`, `companies`, and `targets`.

`python3 plugins/retriever/scripts/retriever.py reset state` previews a full fresh-onboarding cleanup. With `--confirm-delete`, it deletes only known Retriever artifacts—`USER.md`, SQLite database files, reports, dashboard service metadata, and retained `prior-installs` backups—while preserving unknown entries in the state directory. It stops the managed dashboard before deletion and never deletes Codex schedules itself. The interactive `retriever-uninstall` clean-test flow deletes confirmed Retriever-owned schedules first, then invokes this local cleanup, so manual `~/.retriever` deletion is unnecessary.

The post-install fresh starter uses `python3 plugins/retriever/scripts/retriever.py reinstall prepare --confirm-fresh-start`. Rather than delete data, it moves only known active Retriever artifacts to `~/.retriever/prior-installs/<timestamp>/`; new onboarding never reads that backup. `runtime.json` records the bundle identity that saved an active profile. A changed or missing identity marks retained state as requiring fresh onboarding and blocks reports, dashboard startup, and retrieval until the active state is replaced.

A full profile or database wipe is intentionally not inferred from "start fresh with jobs"; Retriever must ask for exact scope before deleting profile data, companies, targets, or local artifacts.

## Reporting

The default report returns the full visible database. Ranked reports can be limited for readability, but they must disclose how many visible jobs are not shown inline and offer the full report or CSV export.

Report formats are Markdown for chat-readable summaries, CSV for spreadsheet import, and static HTML for a local dashboard that can be opened without a server. Whenever Retriever presents found jobs—after an interactive request or a successful scheduled run—the report skill starts or reuses a managed loopback-only interactive dashboard and presents its URL. It binds only to `127.0.0.1`, displays total job records, shown jobs, and directly archived jobs, offers an archived-job CSV download, requires a per-process confirmation token for archiving, and writes only the selected job's local archive flag after the user confirms. An unqualified request for “the web page” means this local dashboard, not an employer careers page. `dashboard stop` sends an authenticated loopback shutdown request and removes its local service metadata.

## Scheduling

Recurring retrieval is a two-layer contract. The local runtime validates a single active cadence target and deterministically maps daily, weekly, or monthly **machine-local** user input to a Codex wall-clock RRULE. The skills then use Codex Scheduled to create or update one Retriever-owned automation with that plan. A cadence-only update uses `profile set-cadence`, which replaces only the active cadence target and the cadence section of `USER.md`; it never clears the local CRM history. The current task interface accepts the RRULE without a separate timezone field, so a named timezone requires local-time confirmation rather than silent conversion. A valid user-selected cadence authorizes the recurring task; immediate retrieval remains separately consent-gated. At execution time, the scheduled prompt invokes the currently loaded `$retriever-retrieve` skill, which resolves its own installed runtime and repeats the setup preflight before it opens Chrome or creates a run. A successful scheduled run starts or reuses the managed local dashboard and places its loopback URL in the result, so the user can review the same SQLite-backed job list and archive controls used in an interactive report. Scheduled prompts must never persist a versioned `~/.codex/plugins/cache/...` runtime path because plugin updates and reinstalls can replace cache directories.

Before uninstalling Retriever, its explicit uninstall workflow identifies and removes only Retriever-owned schedules after user confirmation. Codex exposes no GUI-uninstall callback, so the Plugins UI itself preserves local data and tasks. On the next install, the fresh starter quarantines active state; a retained schedule then fails the local configuration gate and skips retrieval until onboarding updates it. Reference: [OpenAI Hooks documentation](https://learn.chatgpt.com/docs/hooks).

Reference: [OpenAI Scheduled tasks documentation](https://learn.chatgpt.com/docs/automations), [Using Retriever with Codex](CODEX.md).
