# Automation

Retriever creates or updates one Codex **Scheduled** task after onboarding saves a ready profile and the user explicitly chooses a local-time cadence. That cadence authorizes the recurring task; installation alone never does. The first immediate retrieval still needs separate consent. See [Using Retriever with Codex](CODEX.md#scheduled-retrieval) for the user-facing setup path.

## Schedule Prompt

Use this prompt body for a daily, weekly, or monthly job-search automation:

```text
First invoke `$retriever-retrieve`. At execution time, let that loaded skill resolve its own installed plugin root and run Retriever’s authoritative `setup-status` configuration gate. Do not store, infer, or invoke a versioned `~/.codex/plugins/cache/...` runtime path in this scheduled task. If `ready_for_retrieval` is false, `requires_reinstall_cleanup` is true, or `database_integrity` is not `ok`, skip the scan without opening Chrome, creating or finishing a run, writing jobs, or writing reports. State that interactive onboarding is required and direct the user to start a Codex chat and select “Start a fresh private job search”. Otherwise, use `$retriever-retrieve` to check active companies in `~/.retriever` for jobs matching the active `USER.md` profile. Then use `$retriever-report` to report jobs first seen since the previous scheduled run or since yesterday, whichever is available, start or reuse the local interactive dashboard, and show its returned local URL prominently. Show counts, top ranked matches if there are many results, offer the full database/CSV, ask whether the user wants help identifying potential referrers for promising roles, ask whether preferences need updates, and do not submit applications or contact employers.
```

## Cadence Contract

Retriever accepts only a fully specified recurrence before it creates or updates a schedule:

```text
Daily at 8:00 AM local time
Weekly on Monday at 8:00 AM local time
Monthly on day 15 at 8:00 AM local time
```

Codex Scheduled's current task interface accepts an RRULE but does not expose a separate timezone field. Retriever therefore schedules only at an explicitly confirmed **machine-local** time. If a user names a timezone, Retriever asks them to confirm the corresponding local time instead of guessing. It converts the saved cadence through its local runtime:

```bash
python3 plugins/retriever/scripts/retriever.py schedule plan --cadence "<user-approved cadence>"
```

The command returns `valid`, `scheduler_timezone: local`, and the exact Codex wall-clock `rrule`. The automation creator must use that `rrule` unchanged. It must update an existing Retriever-owned task rather than create a duplicate when the user switches among daily, weekly, or monthly. The cadence itself authorizes the recurring task; it does not authorize an immediate first company-site scan.

## Repair a Missing-Runtime Error

An error that names a missing versioned Retriever cache directory does not by itself mean the job-search profile is stale. Use the currently loaded `$retriever-retrieve` skill to run `setup-status` and inspect the profile. When the profile is healthy, update the existing Retriever-owned automation with the prompt above, preserving its local-time cadence, project, model, and notification settings. Do not run a scan as part of that repair.

## Guardrails

- Confirm the cadence and machine-local time before creating an automation.
- Use the runtime's planned daily, weekly, or monthly wall-clock recurrence; never translate the user's cadence manually.
- If the automation tool rejects a schedule representation, retry with that tool's supported daily, weekly, or monthly wall-clock form while preserving the planned recurrence.
- Tell the user that local scheduled retrieval depends on Codex, Chrome, and the machine/session being available.
- Create or update the recurring task once `setup-status` reports `ready_for_retrieval: true` and the user explicitly approves the local-time cadence. Do not use that cadence as consent for the first immediate retrieval.
- Keep the task prompt version-agnostic. The loaded `$retriever-retrieve` skill resolves its runtime at execution time, so a plugin update or reinstall cannot invalidate a stored cache path. A changed or missing local runtime identity is a separate safety boundary: it blocks retrieval until interactive fresh onboarding.
- When removing Retriever, delete its own schedules through the `retriever-uninstall` flow before using the Plugins UI. Preserve unrelated Codex automations and local data unless the user explicitly chooses a reset.

Reference: [OpenAI Scheduled tasks documentation](https://learn.chatgpt.com/docs/automations).
