# Retriever

<p align="center">
  <img src="plugins/retriever/assets/icon-256.png" alt="Retriever logo" width="128">
</p>

Retriever is a local Codex plugin for company-site job intelligence. It helps a job seeker build a profile, monitor selected company career pages, detect new matching jobs early, and export reports without submitting applications.

The first implementation target is macOS. Retriever stores local user data in `~/.retriever` by default.

## Scope

Retriever is an intelligence and reconnaissance tool only.

- It reads and reviews company career sites.
- It records companies, jobs, targets, retrieval runs, and observations in SQLite.
- It warns about career-page prompt-injection patterns.
- It exports Markdown, CSV, and static HTML dashboard reports.
- It does not submit applications, send employer messages, rewrite resumes for listings, or click final application controls.

## Why Retriever Helps

Retriever is built around the practical advantage of seeing real company-site postings early. Harvard Business Review's July 15, 2026 article "Are You Biased Toward Job Candidates Who Reply Quickly?" by Eric M. VanEpps and Einav Hart describes research showing that hiring evaluations can be influenced by how quickly candidates respond, not only by credentials or fit.

Retriever helps a job seeker find fresh postings directly on company career pages, evaluate fit quickly, and decide whether to seek a legitimate referral while the role is still new. It does not automate outreach or applications.

Reference: [Harvard Business Review: Are You Biased Toward Job Candidates Who Reply Quickly?](https://hbr.org/2026/07/are-you-biased-toward-job-candidates-who-reply-quickly).

## Hackathon Track

This project targets "Apps for Your Life" for the OpenAI Devpost hackathon. The project should be judged as a Codex-assisted local productivity plugin for a real job-search workflow.

Reference: [OpenAI Devpost rules](https://openai.devpost.com/rules).

## How Codex and GPT-5.6 Were Used

Retriever was built as a human-directed, Codex-implemented project.

- Dan Anderson wrote the product specifications, chose the job-search workflow, set the safety boundary that Retriever must never submit applications, and performed bug testing and QA.
- Codex generated the repository implementation: plugin metadata, Retriever skills, SQLite runtime, report exporters, dashboard output, tests, documentation, and release-support assets.
- GPT-5.6 reasoning in Codex was used to translate the human product direction into implementation decisions, repair bugs found during QA, and keep the plugin scoped to local job-search intelligence rather than application submission.

Reference: [OpenAI Devpost rules](https://openai.devpost.com/rules). The repository history records the implementation changes as commits in this project.

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

## Use in the Codex App

Retriever is intended to run through the Codex app after installation. A normal user does not need to run the Python runtime commands directly.

1. Open Codex in the ChatGPT desktop app.
2. Open **Plugins**, install **Retriever**, and start a new Codex chat.
3. Ask Retriever for the workflow you want, for example:

```text
Set up my Retriever job-search profile.
Check my target companies for new jobs.
Show my full Retriever job report.
Export my Retriever jobs as an HTML dashboard.
```

Codex will invoke Retriever's bundled skills and use the local runtime under the hood. Live career-site retrieval still requires the Chrome plugin to be installed and enabled.

References: [Codex plugins docs](https://learn.chatgpt.com/docs/plugins), [Codex skills and plugins docs](https://learn.chatgpt.com/docs/skills-and-plugins).

## Runtime Commands for Development

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
python3 plugins/retriever/scripts/retriever.py report --format html --ranked --output ~/.retriever/reports/jobs.html
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
- `$retriever-report`: export Markdown, CSV, or HTML reports.

## Storage

Default state is `~/.retriever`:

- `USER.md`: profile distilled from the user's conversation and resume.
- `retriever.sqlite3`: local SQLite database.
- `reports/`: exported reports.

The distributable plugin does not ship a real user's resume, email, profile, dream companies, or search preferences. Onboarding must collect those from the current user.

## License

Retriever is licensed as `AGPL-3.0-only`. AGPL is a copyleft free-software license with network-source obligations; it is not a noncommercial license. The official license text and identifier are published by GNU and SPDX.

References: [GNU AGPL v3](https://www.gnu.org/licenses/agpl-3.0.en.html), [SPDX AGPL-3.0-only](https://spdx.org/licenses/AGPL-3.0-only.html).
