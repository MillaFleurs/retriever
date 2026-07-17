# Retriever

Retriever is a local Codex plugin for company-site job intelligence. It helps a job seeker build a profile, monitor selected company career pages, detect new matching jobs early, and export reports without submitting applications.

The first implementation target is macOS. Retriever stores local user data in `~/.retriever` by default.

## Scope

Retriever is an intelligence and reconnaissance tool only.

- It reads and reviews company career sites.
- It records companies, jobs, targets, retrieval runs, and observations in SQLite.
- It warns about career-page prompt-injection patterns.
- It exports Markdown and CSV reports.
- It does not submit applications, send employer messages, rewrite resumes for listings, or click final application controls.

## Hackathon Track

This project targets "Apps for Your Life" for the OpenAI Devpost hackathon. The project should be judged as a Codex-assisted local productivity plugin for a real job-search workflow.

Reference: [OpenAI Devpost rules](https://openai.devpost.com/rules).

## Requirements

- macOS for the first release.
- Codex with the Chrome plugin installed and enabled for live career-site retrieval.
- Python 3 with the standard library.

References: [Codex Chrome extension docs](https://learn.chatgpt.com/docs/chrome-extension), [Codex automations docs](https://learn.chatgpt.com/docs/automations).

## Install Locally

From this repository:

```bash
codex plugin marketplace add /Users/daniel/code/20260717-retriever
codex plugin add retriever@retriever
```

Then install `retriever` from the repo-local marketplace in Codex.

The marketplace manifest is at `.agents/plugins/marketplace.json`; the plugin itself is at `plugins/retriever`.

After publishing this repository on GitHub, users can add the marketplace from
the GitHub repo instead of a local path:

```bash
codex plugin marketplace add MillaFleurs/retriever
codex plugin add retriever@retriever
```

## Runtime Commands

Initialize local state:

```bash
python3 plugins/retriever/scripts/retriever.py init
```

Use a temporary state directory for demos or tests:

```bash
python3 plugins/retriever/scripts/retriever.py --state-dir /private/tmp/retriever-demo profile write --json examples/demo/profile.json
```

Add a company:

```bash
python3 plugins/retriever/scripts/retriever.py company add "Example AI Labs" \
  --website-url "https://example.com/" \
  --careers-url "https://example.com/careers" \
  --research-url "https://example.com/careers" \
  --notes "User-specified dream company."
```

Record a job sighting:

```bash
python3 plugins/retriever/scripts/retriever.py job upsert \
  --company "Example AI Labs" \
  --title "Technical Program Manager" \
  --location "San Francisco, CA" \
  --source-url "https://example.com/careers" \
  --url "https://example.com/careers/technical-program-manager"
```

Export reports:

```bash
python3 plugins/retriever/scripts/retriever.py report --format markdown
python3 plugins/retriever/scripts/retriever.py report --format markdown --ranked --limit 6
python3 plugins/retriever/scripts/retriever.py report --format csv --output ~/.retriever/reports/jobs.csv
```

Archive items:

```bash
python3 plugins/retriever/scripts/retriever.py job archive 1
python3 plugins/retriever/scripts/retriever.py company archive "Example Company"
python3 plugins/retriever/scripts/retriever.py target preview role "Sales"
python3 plugins/retriever/scripts/retriever.py target archive --force role "Sales"
```

Start fresh with job findings while keeping the profile, companies, and targets:

```bash
python3 plugins/retriever/scripts/retriever.py reset jobs
python3 plugins/retriever/scripts/retriever.py reset jobs --confirm-delete
```

The first command previews the rows that would be deleted. The second command permanently deletes jobs, observations, and retrieval-run history.

## Skills

- `$retriever-onboard`: create or refresh `USER.md`, ask career-coach intake questions, seed companies.
- `$retriever-retrieve`: use Chrome to inspect company career sites and record matching jobs.
- `$retriever-manage`: update companies, targets, cadence, archive state, and explicit reset requests.
- `$retriever-report`: export Markdown or CSV reports.

## Storage

Default state is `~/.retriever`:

- `USER.md`: profile distilled from the user's conversation and resume.
- `retriever.sqlite3`: local SQLite database.
- `reports/`: exported reports.

The distributable plugin does not ship a real user's resume, email, profile, dream companies, or search preferences. Onboarding must collect those from the current user.

## License

Retriever is licensed as `AGPL-3.0-only`. AGPL is a copyleft free-software license with network-source obligations; it is not a noncommercial license. The official license text and identifier are published by GNU and SPDX.

References: [GNU AGPL v3](https://www.gnu.org/licenses/agpl-3.0.en.html), [SPDX AGPL-3.0-only](https://spdx.org/licenses/AGPL-3.0-only.html).
