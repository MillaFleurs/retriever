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
- It exports Markdown, CSV, static HTML reports, and a managed loopback-only interactive dashboard for local job review and archiving.
- It does not submit applications, send employer messages, rewrite resumes for listings, or click final application controls.
- If a user explicitly targets the Boston Red Sox or New England Patriots as an employer, Retriever gives one playful “Bark. Grrr.” while still providing the same complete help and results.

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
- The ChatGPT desktop app with Codex available. Retriever plugins can run in Codex or Work mode; they are not available in Chat mode, the IDE extension, or mobile.
- The separate Chrome plugin installed and enabled for live career-site retrieval. It is not needed for onboarding, local reports, or archive management.
- Python 3 with the standard library.

References: [OpenAI Plugins documentation](https://learn.chatgpt.com/docs/plugins), [Codex Chrome extension documentation](https://learn.chatgpt.com/docs/chrome-extension).

## Install in Codex

Full Codex installation, update, scheduling, and uninstall guidance is in [Using Retriever with Codex](docs/CODEX.md).

### GitHub Marketplace

Install Retriever from its public GitHub marketplace:

```bash
codex plugin marketplace add MillaFleurs/retriever
codex plugin add retriever@retriever
```

### Local Clone

For development, run these commands from the repository root:

```bash
codex plugin marketplace add .
codex plugin add retriever@retriever
```

The marketplace manifest is `.agents/plugins/marketplace.json`; its Retriever entry resolves to `plugins/retriever`. For a local source, restart the ChatGPT desktop app after changing plugin files.
Reference: [Build plugins: marketplace setup](https://learn.chatgpt.com/docs/build-plugins#build-your-own-curated-plugin-list).

## Use in the Codex App

Retriever is intended to run through the Codex app after installation. A normal user does not need to run the Python runtime commands directly.

1. Open a **new** Codex chat in the ChatGPT desktop app. Plugin skills become available in new chats after installation.
2. If Codex shows **Try it now**, select it. Otherwise send **Start my job search**.
3. Retriever checks local setup without creating data; when no saved profile is present, it starts a concise career-coach intake immediately.
4. After it verifies the saved profile, Retriever asks whether to run the first company search. It calculates the estimate from the current active-company count at about three minutes per company, and it waits for an explicit yes before opening Chrome or searching a career site.
5. Ask Retriever for the workflow you want, for example:

```text
Start my job search
Check my target companies for new jobs.
Show my full Retriever job report.
Open my Retriever job dashboard.
Export my Retriever jobs as an HTML dashboard.
```

Codex invokes Retriever's bundled skills and local runtime under the hood. When a user asks about found jobs, Retriever starts or reuses its local interactive dashboard and shares the URL automatically. Installation itself cannot collect a resume or preferences in the background: that information is collected only in the first interactive chat. Live career-site retrieval still requires the Chrome plugin to be installed and enabled. Retriever uses the normal Chrome browser identity; it does not alter or append its name to the User-Agent string.

References: [OpenAI Plugins documentation](https://learn.chatgpt.com/docs/plugins), [Codex Chrome extension documentation](https://learn.chatgpt.com/docs/chrome-extension), [Using Retriever with Codex](docs/CODEX.md).

## Documentation

- [Using Retriever with Codex](docs/CODEX.md): GitHub and local marketplace installation, new-chat startup, Chrome, updates, Scheduled, and uninstall.
- [Architecture](docs/ARCHITECTURE.md): components, data model, retrieval, archive, reset, reporting, and scheduling boundaries.
- [Automation](docs/AUTOMATION.md): the guarded Codex Scheduled prompt and schedule lifecycle.
- [Security and Safety](docs/SECURITY.md): external-site safety, prompt-injection handling, local data, and loopback dashboard controls.
- [Demo Script](docs/DEMO.md): live and deterministic Devpost demo flow.
- [Devpost Checklist](docs/DEVPOST.md): submission evidence and release verification.

## Runtime Commands for Development

These commands are for developers, deterministic demos, and local verification. A normal Retriever user works through the Codex app and does not need to run them.

Initialize local state:

```bash
python3 plugins/retriever/scripts/retriever.py init
```

Check whether local state is intact and ready without creating files, directories, database rows, or a retrieval run:

```bash
python3 plugins/retriever/scripts/retriever.py setup-status
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

Start or reuse a local-only interactive dashboard with confirmation-gated archive buttons, total/shown/archived job counts, and archived-job CSV download:

```bash
python3 plugins/retriever/scripts/retriever.py dashboard start --ranked
```

The command prints `http://127.0.0.1:<port>/` immediately and keeps the local service running for review. Stop it when finished:

```bash
python3 plugins/retriever/scripts/retriever.py dashboard stop
```

Static HTML exports remain read-only.

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

## Verification

Run the full local test suite:

```bash
python3 -B -m unittest discover -s tests -v
```

Plugin and skill validation are part of the release workflow:

Use Codex's `plugin-creator` validation for `plugins/retriever` and `skill-creator` validation for any changed skill directory. Those helpers are provided by the local Codex installation rather than this repository's runtime.

## Uninstall and Scheduled Searches

Before uninstalling Retriever, tell it `Uninstall Retriever and delete its schedules`. Retriever will identify only its own Codex automations, show them for confirmation, and remove them before you use the Plugins UI. By default it preserves `~/.retriever`; choose a separate explicit reset or full-data deletion if you do not want to retain local data.

Plugin skills become available in a new chat after installation. Retriever therefore uses the first interactive **Try it now** or **Start my job search** conversation for onboarding and an explicit uninstall cleanup flow for scheduled automations; it does not claim a background install lifecycle event.

References: [OpenAI Plugins documentation](https://learn.chatgpt.com/docs/plugins), [Build plugins](https://learn.chatgpt.com/docs/build-plugins), [Using Retriever with Codex](docs/CODEX.md).

## Skills

- `$retriever-onboard`: create or refresh `USER.md`, ask career-coach intake questions, seed companies.
- `$retriever-welcome`: handle the **Start my job search** prompt, safely inspect local state, and start or resume onboarding.
- `$retriever-retrieve`: use Chrome to inspect company career sites and record matching jobs.
- `$retriever-manage`: update companies, targets, cadence, archive state, and explicit reset requests.
- `$retriever-report`: export Markdown, CSV, or HTML reports.
- `$retriever-uninstall`: remove Retriever-owned schedules after confirmation and guide local-data cleanup.

## Storage

Default state is `~/.retriever`:

- `USER.md`: profile distilled from the user's conversation and resume.
- `retriever.sqlite3`: local SQLite database.
- `reports/`: exported reports.

The distributable plugin does not ship a real user's resume, email, profile, dream companies, or search preferences. Onboarding must collect those from the current user.

## License

Retriever is licensed as `AGPL-3.0-only`. AGPL is a copyleft free-software license with network-source obligations; it is not a noncommercial license. The official license text and identifier are published by GNU and SPDX.

References: [GNU AGPL v3](https://www.gnu.org/licenses/agpl-3.0.en.html), [SPDX AGPL-3.0-only](https://spdx.org/licenses/AGPL-3.0-only.html).
