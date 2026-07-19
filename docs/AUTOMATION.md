# Automation

Retriever recurring runs should be configured through Codex **Scheduled** after the user chooses a cadence and explicitly authorizes retrieval. Installation and profile onboarding never create a background job by themselves. See [Using Retriever with Codex](CODEX.md#scheduled-retrieval) for the user-facing setup path.

## Schedule Prompt

Use this prompt body for a daily job-search automation:

```text
First run `python3 <plugin-root>/scripts/retriever.py setup-status` and treat its JSON as authoritative. If `ready_for_retrieval` is false or `database_integrity` is not `ok`, skip the scan without opening Chrome, creating or finishing a run, writing jobs, or writing reports. State that interactive onboarding is required and direct the user to start a Codex chat and select “Start my job search”. Otherwise, use $retriever-retrieve to check active companies in ~/.retriever for jobs matching the active USER.md profile. Then use $retriever-report to report jobs first seen since the previous scheduled run or since yesterday, whichever is available. Show counts, top ranked matches if there are many results, offer the full database/CSV, ask whether the user wants help identifying potential referrers for promising roles, ask whether preferences need updates, and do not submit applications or contact employers.
```

## Guardrails

- Confirm the cadence and timezone before creating an automation.
- For "every morning at 9:00", use a daily wall-clock schedule in the user's local timezone.
- If the automation tool rejects a schedule representation, retry with that tool's supported daily wall-clock format while preserving the requested cadence.
- Tell the user that local scheduled retrieval depends on Codex, Chrome, and the machine/session being available.
- Do not create a scheduled retrieval until `setup-status` reports `ready_for_retrieval: true` and the user explicitly agrees to retrieval.
- When removing Retriever, delete its own schedules through the `retriever-uninstall` flow before using the Plugins UI. Preserve unrelated Codex automations and local data unless the user explicitly chooses a reset.

Reference: [OpenAI Scheduled tasks documentation](https://learn.chatgpt.com/docs/automations).
